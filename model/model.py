import math
import torch
from torch import nn, einsum
import torch.nn.functional as F
from functools import partial
from einops.layers.torch import Rearrange
from einops import rearrange, reduce
from einops._torch_specific import allow_ops_in_compiled_graph

from utils.utils import default, identity, exists

allow_ops_in_compiled_graph()

USE_CIRCULAR_PADDING = False

if USE_CIRCULAR_PADDING:
    conv2d = lambda *args, **kwargs: nn.Conv2d(*args, **kwargs, padding_mode='circular')
else:
    conv2d = lambda *args, **kwargs: nn.Conv2d(*args, **kwargs)

class TileableConv2d(nn.Conv2d):
    '''
    Custom Conv2d module that uses circular padding (for tileable image generation)
    '''
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
    
    def forward(self, x):
        x = F.pad(x, (self.padding[0], self.padding[0], self.padding[1], self.padding[1]), mode='circular')
        return F.conv2d(x, self.weight, self.bias, self.stride, 0, self.dilation, self.groups)

def replace_conv2d_with_tileable(model):
    '''
    Recursively replace all Conv2d layers in a model with TileableConv2d layers, copy weights over
    '''
    for name, module in model.named_children():
        if isinstance(module, nn.Conv2d):
            new_conv = TileableConv2d(module.in_channels, module.out_channels, module.kernel_size, module.stride, module.padding, module.dilation, module.groups, module.bias is not None)
            new_conv.weight = module.weight
            new_conv.bias = module.bias
            setattr(model, name, new_conv)
        else:
            replace_conv2d_with_tileable(module)

def replace_tileable_with_conv2d(model):
    '''
    Recursively replace all TileableConv2d layers in a model with Conv2d layers, copy weights over
    '''
    for name, module in model.named_children():
        if isinstance(module, TileableConv2d):
            new_conv = nn.Conv2d(module.in_channels, module.out_channels, module.kernel_size, module.stride, module.padding, module.dilation, module.groups, module.bias is not None)
            new_conv.weight = module.weight
            new_conv.bias = module.bias
            setattr(model, name, new_conv)
        else:
            replace_tileable_with_conv2d(module)

class Block(nn.Module):
    '''
    SPADE-conditioned conv block:
    x -> conv -> group norm -> gamma_1(t) * x + beta_1(t) -> gamma_2(F) * x + beta_2(F) -> SiLU
    gamma_1/beta_1 are for diffusion time conditioning (globally uniform),
    gamma_2/beta_2 are for feature map conditioning (spatially varying)
    '''
    def __init__(self, dim, dim_out, groups = 8):
        super().__init__()
        self.proj = WeightStandardizedConv2d(dim, dim_out, 3, padding = 1)
        self.norm = nn.GroupNorm(groups, dim_out)
        self.act = nn.SiLU()

    def forward(self, x, t_gamma_beta = None, spade_gamma_beta = None):
        x = self.norm(self.proj(x))

        if exists(t_gamma_beta):
            x = x * (t_gamma_beta[0] + 1) + t_gamma_beta[1]

        if exists(spade_gamma_beta):
            x = x * (spade_gamma_beta[0] + 1.) + spade_gamma_beta[1]

        return self.act(x)

class ResnetBlock(nn.Module):
    '''
    ResNet block with SPADE conditioning
    '''
    def __init__(self, dim, dim_out, *, time_emb_dim = None, groups = 8, z_emb_dim = None):
        super().__init__()
        self.mlp_t = nn.Sequential(
            nn.SiLU(),
            nn.Linear(time_emb_dim, dim_out * 2)
        ) if exists(time_emb_dim) else None

        self.spade_conv = None
        if exists(z_emb_dim):
            self.spade_conv = nn.Sequential(
                nn.SiLU(),
                conv2d(z_emb_dim, dim_out, 3, padding = 1),
                nn.SiLU()
            )
            self.spade_gamma = conv2d(dim_out, dim_out, 3, padding = 1)
            self.spade_beta = conv2d(dim_out, dim_out, 3, padding = 1)

        self.block1 = Block(dim, dim_out, groups = groups)
        self.block2 = Block(dim_out, dim_out, groups = groups)
        self.res_conv = conv2d(dim, dim_out, 1) if dim != dim_out else nn.Identity()

    def forward(self, x, time_emb = None, z_emb = None):
        t_gamma_beta = None
        spade_gamma_beta = None

        if exists(self.mlp_t) and exists(time_emb):
            time_emb = self.mlp_t(time_emb).unsqueeze(-1).unsqueeze(-1)
            t_gamma_beta = time_emb.chunk(2, dim = 1)
        
        if exists(self.spade_conv) and exists(z_emb):
            if z_emb.ndim == 2:
                # z_emb is (B, C), tile it to be (B, C, H, W):
                z_emb = z_emb.unsqueeze(-1).unsqueeze(-1)
                z_emb = z_emb.expand(-1, -1, x.shape[-2], x.shape[-1]) # (B, C, H, W)
            if x.shape[-1] != z_emb.shape[-1]: # spatial dim mismatch
                z_emb = F.interpolate(z_emb, size = x.shape[-2:], mode = 'nearest')

            z_emb = self.spade_conv(z_emb)
            spade_gamma_beta = [self.spade_gamma(z_emb), self.spade_beta(z_emb)] # (2, B, C, H, W)

        h = self.block1(x, t_gamma_beta=t_gamma_beta, spade_gamma_beta=spade_gamma_beta)
        h = self.block2(h)

        return h + self.res_conv(x)

class Residual(nn.Module):
    def __init__(self, fn):
        super().__init__()
        self.fn = fn

    def forward(self, x, *args, **kwargs):
        return self.fn(x, *args, **kwargs) + x

def Upsample(dim, dim_out = None):
    return nn.Sequential(
        nn.Upsample(scale_factor = 2, mode = 'nearest'),
        conv2d(dim, default(dim_out, dim), 3, padding = 1)
    )

def Downsample(dim, dim_out = None):
    return nn.Sequential(
        Rearrange('b c (h p1) (w p2) -> b (c p1 p2) h w', p1 = 2, p2 = 2),
        conv2d(dim * 4, default(dim_out, dim), 1)
    )

def variance_unbiased_false(tensor):
    return torch.var(tensor, unbiased=False)

class WeightStandardizedConv2d(nn.Conv2d):
    """
    https://arxiv.org/abs/1903.10520
    weight standardization purportedly works synergistically with group normalization
    """
    def forward(self, x):
        eps = 1e-5 if x.dtype == torch.float32 else 1e-3

        weight = self.weight
        mean = reduce(weight, 'o ... -> o 1 1 1', 'mean')
        var = torch.var(weight, dim=(1,2,3), unbiased=False, keepdim=True)
        
        normalized_weight = (weight - mean) * (var + eps).rsqrt()
        
        if USE_CIRCULAR_PADDING:
            x = F.pad(x, (self.padding[0], self.padding[0], self.padding[1], self.padding[1]), mode='circular')
            return F.conv2d(x, normalized_weight, self.bias, self.stride, 0, self.dilation, self.groups)
        else:
            return F.conv2d(x, normalized_weight, self.bias, self.stride, self.padding, self.dilation, self.groups)

class LayerNorm(nn.Module):
    def __init__(self, dim):
        super().__init__()
        self.g = nn.Parameter(torch.ones(1, dim, 1, 1))

    def forward(self, x):
        eps = 1e-5 if x.dtype == torch.float32 else 1e-3
        var = torch.var(x, dim = 1, unbiased = False, keepdim = True)
        mean = torch.mean(x, dim = 1, keepdim = True)
        return (x - mean) * (var + eps).rsqrt() * self.g

class PreNorm(nn.Module):
    def __init__(self, dim, fn):
        super().__init__()
        self.fn = fn
        self.norm = LayerNorm(dim)

    def forward(self, x):
        x = self.norm(x)
        return self.fn(x)

class SinusoidalPosEmb(nn.Module):
    def __init__(self, dim):
        super().__init__()
        self.dim = dim

    def forward(self, x):
        device = x.device
        half_dim = self.dim // 2
        emb = math.log(10000) / (half_dim - 1)
        emb = torch.exp(torch.arange(half_dim, device=device) * -emb)

        if x.ndim == 1:
            emb = x[:, None] * emb[None, :]
        else: # (B, C, 1) * (1, 1, D) 
            emb = x[:, :, None] * emb[None, None, :]
            
        emb = torch.cat((emb.sin(), emb.cos()), dim=-1)
        return emb

class RandomOrLearnedSinusoidalPosEmb(nn.Module):
    """ following @crowsonkb 's lead with random (learned optional) sinusoidal pos emb """
    """ https://github.com/crowsonkb/v-diffusion-jax/blob/master/diffusion/models/danbooru_128.py#L8 """

    def __init__(self, dim, is_random = False):
        super().__init__()
        assert (dim % 2) == 0
        half_dim = dim // 2
        self.weights = nn.Parameter(torch.randn(half_dim), requires_grad = not is_random)

    def forward(self, x):
        x = rearrange(x, 'b -> b 1')
        freqs = x * rearrange(self.weights, 'd -> 1 d') * 2 * math.pi
        fouriered = torch.cat((freqs.sin(), freqs.cos()), dim = -1)
        fouriered = torch.cat((x, fouriered), dim = -1)
        return fouriered

class LinearAttention(nn.Module):
    def __init__(self, dim, heads = 4, dim_head = 32):
        super().__init__()
        self.scale = dim_head ** -0.5
        self.heads = heads
        hidden_dim = dim_head * heads
        self.to_qkv = nn.Conv2d(dim, hidden_dim * 3, 1, bias = False)

        self.to_out = nn.Sequential(
            nn.Conv2d(hidden_dim, dim, 1),
            LayerNorm(dim)
        )

    def forward(self, x):
        b, c, h, w = x.shape
        qkv = self.to_qkv(x).chunk(3, dim = 1)
        q, k, v = map(lambda t: rearrange(t, 'b (h c) x y -> b h c (x y)', h = self.heads), qkv)

        q = q.softmax(dim = -2)
        k = k.softmax(dim = -1)

        q = q * self.scale
        v = v / (h * w)

        context = torch.einsum('b h d n, b h e n -> b h d e', k, v)

        out = torch.einsum('b h d e, b h d n -> b h e n', context, q)
        out = rearrange(out, 'b h c (x y) -> b (h c) x y', h = self.heads, x = h, y = w)
        return self.to_out(out)

class Attention(nn.Module):
    def __init__(self, dim, heads = 4, dim_head = 32):
        super().__init__()
        self.scale = dim_head ** -0.5
        self.heads = heads
        hidden_dim = dim_head * heads

        self.to_qkv = nn.Conv2d(dim, hidden_dim * 3, 1, bias = False)
        self.to_out = nn.Conv2d(hidden_dim, dim, 1)

    def forward(self, x):
        b, c, h, w = x.shape
        qkv = self.to_qkv(x).chunk(3, dim = 1)
        q, k, v = map(lambda t: rearrange(t, 'b (h c) x y -> b h c (x y)', h = self.heads), qkv)

        q = q * self.scale

        sim = einsum('b h d i, b h d j -> b h i j', q, k)
        attn = sim.softmax(dim = -1)
        out = einsum('b h i j, b h d j -> b h i d', attn, v)

        out = rearrange(out, 'b h (x y) d -> b (h d) x y', x = h, y = w)
        return self.to_out(out)

class NeRFPosEnc(nn.Module):
    # NeRF style positional encoding from mip-nerf
    # https://github.com/google/mipnerf/blob/main/internal/mip.py
    def __init__(self, min_deg, max_deg):
        super().__init__()
        self.min_deg = min_deg
        self.max_deg = max_deg

    def forward(self, x, chn_last=False):
        if x.ndim == 4:
            x = x.permute(0, 2, 3, 1).contiguous() # (B, H, W, C)

        scales = torch.tensor([2.0**i for i in range(self.min_deg, self.max_deg)]).to(x.device)
        xb = (x[..., None, :] * scales[:, None]).view(*x.shape[:-1], -1)
        four_feat = torch.sin(torch.cat([xb, xb + 0.5 * torch.pi], dim=-1))
        four_feat = torch.cat([x, four_feat], dim=-1)

        if x.ndim == 4 and not chn_last:
            four_feat = four_feat.permute(0, 3, 1, 2).contiguous() # (B, C, H, W)

        return four_feat
    
class Unet(nn.Module):
    def __init__(
        self,
        dim,
        init_dim = None,
        out_dim = None,
        dim_mults=(1, 2, 4, 8),
        channels = 3,
        self_condition = False,
        resnet_block_groups = 8,
        learned_variance = False,
        cond_dim = 128,
        nclasses = 1,
        nparams = 18,
        attention = True,
        pos_enc_deg = 0, # default 0 = no pos enc
        cond_layers = (), # which layers to condition, default () = all
    ):
        super().__init__()

        self.nclasses = nclasses
        self.cond_dim = cond_dim

        self.channels = channels
        self.self_condition = self_condition
        input_channels = channels * (2 if self_condition else 1)

        init_dim = default(init_dim, dim)
        self.init_conv = conv2d(input_channels, init_dim, 7, padding=3)

        dims = [init_dim, *map(lambda m: dim * m, dim_mults)]
        in_out = list(zip(dims[:-1], dims[1:]))

        block_klass = partial(ResnetBlock, groups = resnet_block_groups)

        self.cls_dim = dim if nclasses > 1 else 0
        self.classes_emb = nn.Embedding(nclasses, self.cls_dim)

        self.cond_pos_enc = NeRFPosEnc(0, pos_enc_deg) if pos_enc_deg > 0 else nn.Identity()
        cond_enc_dim = (2 * nparams * pos_enc_deg) + nparams # final dim for positonally encoded substance param cond

        self.cond_mlp = nn.Sequential(
            nn.Linear(cond_enc_dim + self.cls_dim, cond_dim),
            nn.GELU(),
            nn.Linear(cond_dim, cond_dim)
        )

        sinu_pos_emb = SinusoidalPosEmb(dim)
        fourier_dim = dim

        time_dim = dim * 4
        self.time_mlp = nn.Sequential(
            sinu_pos_emb,
            nn.Linear(fourier_dim, time_dim),
            nn.GELU(),
            nn.Linear(time_dim, time_dim)
        )

        self.downs = nn.ModuleList([])
        self.ups = nn.ModuleList([])
        num_resolutions = len(in_out)
        if len(cond_layers) == 0:
            cond_layers = list(range(num_resolutions + 2)) # condition on all layers, plus bottleneck and final conv blocks

        if attention:
            atten_block = lambda dim, linear: Residual(PreNorm(dim, LinearAttention(dim))) if linear else Residual(PreNorm(dim, Attention(dim)))
        else:
            atten_block = lambda dim, linear: nn.Identity()

        model_str = 'UNET: '
        for ind, (dim_in, dim_out) in enumerate(in_out):
            is_last = ind >= (num_resolutions - 1)
            maybe_cond = cond_dim if ind in cond_layers else None # condition only on certain layers

            self.downs.append(nn.ModuleList([
                block_klass(dim_in, dim_in, time_emb_dim = time_dim, z_emb_dim=maybe_cond),
                block_klass(dim_in, dim_in, time_emb_dim = time_dim, z_emb_dim=maybe_cond),
                atten_block(dim_in, linear=True),
                Downsample(dim_in, dim_out) if not is_last else conv2d(dim_in, dim_out, 3, padding = 1)
            ]))
            model_str += f'down_cond{maybe_cond}_{ind}({dim_in} -> {dim_out}) '

        maybe_cond = cond_dim if num_resolutions in cond_layers else None
        mid_dim = dims[-1]
        self.mid_block1 = block_klass(mid_dim, mid_dim, time_emb_dim = time_dim, z_emb_dim=maybe_cond)
        self.mid_attn = atten_block(mid_dim, linear=False)
        self.mid_block2 = block_klass(mid_dim, mid_dim, time_emb_dim = time_dim, z_emb_dim=maybe_cond)
        model_str += f'mid_cond{maybe_cond}_({mid_dim} -> {mid_dim}) '

        for ind, (dim_in, dim_out) in enumerate(reversed(in_out)):
            is_last = ind == (len(in_out) - 1)
            maybe_cond = cond_dim if (num_resolutions - ind - 1) in cond_layers else None

            self.ups.append(nn.ModuleList([
                block_klass(dim_out + dim_in, dim_out, time_emb_dim = time_dim, z_emb_dim=maybe_cond),
                block_klass(dim_out + dim_in, dim_out, time_emb_dim = time_dim, z_emb_dim=maybe_cond),
                atten_block(dim_out, linear=True),
                Upsample(dim_out, dim_in) if not is_last else  conv2d(dim_out, dim_in, 3, padding = 1)
            ]))
            model_str += f'up_cond{maybe_cond}_{ind}({dim_out} -> {dim_in}) '

        default_out_dim = channels * (1 if not learned_variance else 2)
        self.out_dim = default(out_dim, default_out_dim)

        maybe_cond = cond_dim if num_resolutions + 1 in cond_layers else None
        self.final_res_block = block_klass(dim * 2, dim, time_emb_dim = time_dim, z_emb_dim=maybe_cond)
        self.final_conv = conv2d(dim, self.out_dim, 1)
        model_str += f'final_cond{maybe_cond}_({dim} -> {self.out_dim})'

        print(model_str)

    def preproc_conditioning(self, time, params, classes, class_emb=None):
        '''
        Preprocesses the diffusion time and conditioning features.

        time:  (B,) tensor of diffusion time values
        params: (B, nparams, H, W) tensor of noise parameters
        classes: (B, C, H, W) tensor of one hot class labels
        class_emb (optional): (B, C, H, W) tensor of class embeddings, if provided `classes` is ignored

        Returns:
        time: (B, time_dim) tensor of processed time embeddings
        c: (B, cond_dim, H, W) tensor of processed conditioning features
        '''

        if exists(class_emb):
            cls_embs = class_emb
        else:
            cls_embs = einsum('b c h w, c d -> b d h w', classes, self.classes_emb.weight)
        c = torch.cat((params, cls_embs), dim = 1) # (B, C' + cls_emb, H, W)
        c = torch.permute(c, (0, 2, 3, 1)) # (B, H, W, C' + cls_emb)
        c = self.cond_mlp(c)
        c = c.permute(0, 3, 1, 2) # back to (B, C, H, W)
        c = c.contiguous()

        time = self.time_mlp(time)
        
        return time, c

    # @torch.compile()
    def forward(
        self,
        x,       # current image (B, 1, H, W)
        t,       # diffusion time (B,)
        c,       # conditioning feature grid (B, C, H, W)
    ):
        x = self.init_conv(x)
        r = x.clone()

        h = []

        for block1, block2, attn, downsample in self.downs:
            x = block1(x, t, c)
            h.append(x)
            x = block2(x, t, c)
            x = attn(x)
            h.append(x)
            x = downsample(x)

        x = self.mid_block1(x, t, c)
        x = self.mid_attn(x)
        x = self.mid_block2(x, t, c)

        for block1, block2, attn, upsample in self.ups:
            x = torch.cat((x, h.pop()), dim = 1)
            x = block1(x, t, c)

            x = torch.cat((x, h.pop()), dim = 1)
            x = block2(x, t, c)
            x = attn(x)
            x = upsample(x)

        x = torch.cat((x, r), dim = 1)
        x = self.final_res_block(x, t, c)
        x = self.final_conv(x)

        return x
