import os
import json
import torch
import gradio as gr
import numpy as np
from PIL import Image
from types import SimpleNamespace
from torchvision.utils import save_image, make_grid

from inference.inference import Inference, dict2cond
from config.noise_config import noise_types, noise_aliases, ntype_to_params_map

# Load config from .json
json_path = os.path.join('./pretrained/tiny_spherical/config.json')
with open(json_path, 'r') as f:
    config = json.load(f)
    config = SimpleNamespace(**config)

config.out_dir = 'pretrained'
config.exp_name = 'tiny_spherical'
config.sample_timesteps = 40  # Reduce for faster generation

device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
inf = Inference(config, device=device)

# Get common noise types and masks for a simpler interface
common_noise_types = [
    "damas", "galvanic", "cells1", "cells4", "perlin", 
    "gaussian", "voro", "liquid", "fibers", "micro", "rust"
]
available_masks = [os.path.splitext(f)[0] for f in os.listdir('inference/masks') if f.endswith('.png')]

def tensor_to_image(tensor):
    """Convert a PyTorch tensor to a PIL Image"""
    if len(tensor.shape) == 4:
        tensor = tensor[0]  # Take the first image if it's a batch
    
    # Convert to numpy and scale to 0-255
    img_np = tensor.cpu().numpy().transpose(1, 2, 0) * 255
    img_np = img_np.clip(0, 255).astype(np.uint8)
    
    # If it's a grayscale image, remove the channel dimension
    if img_np.shape[2] == 1:
        img_np = img_np[:, :, 0]
    
    return Image.fromarray(img_np)

def generate_noise(pattern1, pattern2, mask_type, blend_factor, invert_mask):
    """Generate a noise pattern based on the selected options"""
    try:
        # Set up parameters for first noise pattern
        c1 = {
            'cls': pattern1,
            'sbsparams': {
                p: 0.5 for p in ntype_to_params_map.get(noise_aliases.get(pattern1, pattern1), [])
            }
        }
        
        # Set up parameters for second noise pattern
        c2 = {
            'cls': pattern2,
            'sbsparams': {
                p: 0.5 for p in ntype_to_params_map.get(noise_aliases.get(pattern2, pattern2), [])
            }
        }
        
        # Image dimensions
        H, W = 256, 256
        
        # Load the mask
        mask_path = f"inference/masks/{mask_type}.png"
        
        # Handle mask inversion before passing to slerp_mask if needed
        if invert_mask:
            # Load mask, invert it, and save to a temporary path
            mask_img = Image.open(mask_path)
            mask_array = 255 - np.array(mask_img)
            inverted_mask = Image.fromarray(mask_array)
            temp_mask_path = f"inference/masks/temp_inverted.png"
            inverted_mask.save(temp_mask_path)
            mask_path = temp_mask_path
        
        # Generate the noise with mask blending
        with torch.no_grad():
            img = inf.slerp_mask(
                mask=mask_path,
                dict1=c1,
                dict2=c2,
                H=H,
                W=W,
                blending_factor=blend_factor
            )
        
        # Get mask preview
        mask_img = Image.open(mask_path)
        if invert_mask:
            # We already have an inverted mask for preview
            pass
        
        # Return both the generated noise and mask preview
        return tensor_to_image(img), mask_img
        
    except Exception as e:
        print(f"Error generating noise: {e}")
        import traceback
        traceback.print_exc()
        return None, None

def generate_single_noise(pattern, H=256, W=256):
    """Generate a single noise pattern"""
    try:
        # Set up parameters for noise pattern
        c = {
            'cls': pattern,
            'sbsparams': {
                p: 0.5 for p in ntype_to_params_map.get(noise_aliases.get(pattern, pattern), [])
            }
        }
        
        # Generate the noise - use the standalone dict2cond function
        with torch.no_grad():
            sbsparams, classes = dict2cond(c, H=H, W=W)
            sbsparams = sbsparams.cuda()
            classes = classes.cuda()
            img = inf.generate(sbsparams=sbsparams, classes=classes)
        
        return tensor_to_image(img)
        
    except Exception as e:
        print(f"Error generating noise: {e}")
        import traceback
        traceback.print_exc()
        return None

# Create the Gradio interface
with gr.Blocks(title="Noisy Handy Gardio Demo") as demo:
    gr.Markdown("#iNoisy Handy")
    
    gr.Markdown("Based on the Paper: [One Noise to Rule Them All](https://arxiv.org/abs/2406.08413)")
    gr.Markdown("Generate procedural noise patterns by blending two noise types with a mask shape")
    
    with gr.Row():
        with gr.Column(scale=1):
            # Left panel - controls
            with gr.Group():
                pattern1 = gr.Dropdown(
                    choices=common_noise_types,
                    value="damas",
                    label="Pattern 1"
                )
                
                pattern2 = gr.Dropdown(
                    choices=common_noise_types,
                    value="galvanic",
                    label="Pattern 2"
                )
                
                mask_type = gr.Dropdown(
                    choices=available_masks, 
                    value="star",
                    label="Mask Shape"
                )
                
                invert_mask = gr.Checkbox(label="Invert mask", value=False)
                
                blend_factor = gr.Slider(
                    minimum=0.0, 
                    maximum=1.0, 
                    value=0.5, 
                    step=0.01, 
                    label="Blend factor"
                )
                
                generate_btn = gr.Button("Generate", variant="primary")
        
        with gr.Column(scale=2):
            # Right panel - output
            # Add previews for pattern1 and pattern2
            with gr.Row():
                pattern1_preview = gr.Image(label="Pattern 1 Preview", interactive=False)
                pattern2_preview = gr.Image(label="Pattern 2 Preview", interactive=False)
            
            with gr.Row():
                mask_image = gr.Image(label="Blend map", interactive=False)
                output_image = gr.Image(label="Output", interactive=False)
    
    # Update pattern 1 preview when changed
    def update_pattern1_preview(pattern):
        return generate_single_noise(pattern)
    
    pattern1.change(
        fn=update_pattern1_preview,
        inputs=[pattern1],
        outputs=pattern1_preview
    )
    
    # Update pattern 2 preview when changed
    def update_pattern2_preview(pattern):
        return generate_single_noise(pattern)
    
    pattern2.change(
        fn=update_pattern2_preview,
        inputs=[pattern2],
        outputs=pattern2_preview
    )
    
    # Update mask preview when mask or invert changes
    def update_mask_preview(mask_type, invert_mask):
        mask_path = f"inference/masks/{mask_type}.png"
        img = Image.open(mask_path)
        if invert_mask:
            img = Image.fromarray(255 - np.array(img))
        return img
    
    mask_type.change(
        fn=update_mask_preview, 
        inputs=[mask_type, invert_mask], 
        outputs=mask_image
    )
    
    invert_mask.change(
        fn=update_mask_preview, 
        inputs=[mask_type, invert_mask], 
        outputs=mask_image
    )
    
    # Generate button click event - updated to also refresh pattern previews
    def generate_with_previews(pattern1, pattern2, mask_type, blend_factor, invert_mask):
        # Generate individual pattern previews
        pattern1_img = generate_single_noise(pattern1)
        pattern2_img = generate_single_noise(pattern2)
        
        # Generate blended output
        output, mask = generate_noise(pattern1, pattern2, mask_type, blend_factor, invert_mask)
        
        return pattern1_img, pattern2_img, output, mask
    
    generate_btn.click(
        fn=generate_with_previews, 
        inputs=[pattern1, pattern2, mask_type, blend_factor, invert_mask], 
        outputs=[pattern1_preview, pattern2_preview, output_image, mask_image]
    )
    
    # Initialize the previews
    demo.load(
        fn=lambda: [
            generate_single_noise("damas"),
            generate_single_noise("galvanic"),
            update_mask_preview("star", False)
        ],
        inputs=None,
        outputs=[pattern1_preview, pattern2_preview, mask_image]
    )

if __name__ == "__main__":
    demo.launch() 