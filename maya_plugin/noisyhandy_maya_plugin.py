##################################################################################################################################
######## Set Up Sections to make sure all paths and dependencies are well set up before running the core program #################
##################################################################################################################################
##################################################################################################################################
# Importing utilities 
import os
import sys
import json
import ctypes
import site
from types import SimpleNamespace

# Setting up Maya Internal command interfaces package:
import maya.cmds as cmds
import maya.OpenMaya as OpenMaya
import maya.OpenMayaMPx as OpenMayaMPx 

# Import Other information

import noisyhandy_maya_ui
# Plugin Information
PLUGIN_NAME = "NoisyHandyPlugin"
PLUGIN_VERSION = "1.0.1"

# Node Definitions
NOISY_HANDY_NODE_TYPE = "noisyHandyNode"
NOISY_HANDY_NODE_ID = OpenMaya.MTypeId(0x00134567)  # Unique type ID for our node

# Centralized path management
def setup_paths():
    """
    Centralized function to manage all paths needed by the NoisyHandy plugin.
    Sets up required paths and returns a dictionary with all path configurations.
    """
    paths = {}
    
    # Get the plugin path - use __file__ if available, otherwise use Maya's API
    if '__file__' in globals():
        plugin_path = __file__
    else:
        plugin_path = cmds.pluginInfo("noisyhandy_maya_plugin.py", query=True, path=True)
        
    plugin_dir = os.path.dirname(plugin_path)
    root_dir = os.path.dirname(plugin_dir)
    
    # Set up the important paths
    paths['plugin_dir'] = plugin_dir
    paths['root_dir'] = root_dir
    paths['mask_dir'] = os.path.join(root_dir, "inference", "masks")
    paths['temp_output_dir'] = os.path.join(root_dir, "inference", "temp_output")
    paths['checkpoints_dir'] = os.path.join(root_dir, "checkpoints")
    paths['config_dir'] = os.path.join(root_dir, "config")
    
    # Ensure temp_output directory exists
    if not os.path.exists(paths['temp_output_dir']):
        os.makedirs(paths['temp_output_dir'], exist_ok=True)
    
    # Add paths to sys.path if needed
    if root_dir not in sys.path:
        sys.path.append(root_dir)
        print(f"Added {root_dir} to sys.path")
    
    # Add Maya's site-packages path
    mayapy_dir = os.path.join(os.path.dirname(sys.executable), 'lib', 'site-packages')
    if os.path.exists(mayapy_dir) and mayapy_dir not in sys.path:
        sys.path.append(mayapy_dir)
        print(f"Added Maya's site-packages: {mayapy_dir}")
    
    return paths

# Initialize paths
PATHS = setup_paths()

# Initialize Dependencies
def setup_dependencies() -> bool:
    """
    Ensure that required Python packages (numpy, PIL) are installed,
    and that the CUDA runtime DLLs are visible before importing torch.
    Returns True if torch imports OK, False otherwise.
    """
    print(">>>>>>>>>>>>>>>>>>>>>>>>>>")
    print("INITIATING DEPENDENCY CHECK")
    print("==========================")
    print("SETTING UP DEPENDENCY INFO")
    # 1) Check NumPy
    try:
        import numpy  # 
        print("[✓] NumPy is available")
    except ImportError as e:
        print(f"[!] NumPy not found: {e}")

    # 2) Check Pillow
    try:
        from PIL import Image
        print("[✓] PIL is available")
    except ImportError as e:
        print(f"[!] PIL not found: {e}")

    # 3) Finally, import torch
    try:
        import torch  
        
        print(f"[✓] Successfully imported torch, version {torch.__version__}")
        print(f"[✓]CUDA is Available: {torch.cuda.is_available()}")
        print("END SETTING UP DEPENDENCY")
        print("==========================")
        return True
    except Exception as e:
        print(f"[!] Failed to import torch: {e}")
        print("    • Make sure you have the MSVC runtime installed")
        print("    • If you're using a CUDA build, double-check that the "
              "CUDA runtime DLLs are on PATH or added via `os.add_dll_directory`")
        print("END SETTING UP DEPENDENCY")
        print("==========================")
        print("<<<<<<<<<<<<<<<<<<<<<<<<<<")
        return False

HAS_DEPENDENCIES = setup_dependencies()

##################################################################################################################################
##################################################################################################################################
##################################################################################################################################
##################################################################################################################################
############################################## END OF SETUP ######################################################################

def get_root_path():
    """
    Return the Path to the root 
    @return a string value representing the parent directory of the plugin
    """
    return PATHS['root_dir']

# Maya command for running inference
class NoisyHandyInferenceCmd(OpenMayaMPx.MPxCommand):
    """
    Maya command to run inference with the NoisyHandy model
    """
    root_path = None
    command_name = "noisyHandyInference"
    inf = None
    
    def __init__(self):
        OpenMayaMPx.MPxCommand.__init__(self)
        
        if NoisyHandyInferenceCmd.inf is None:
            try:
                # Fixing the issue that the Torch doesn't see the correct dll
                os.add_dll_directory(r"C:\\Program Files\\NVIDIA GPU Computing Toolkit\\CUDA\\v12.4\\bin")
                import torch
                
                # Handle PIL import more gracefully
                try:
                    from PIL import Image
                    print("PIL loaded successfully in command")
                except ImportError:
                    print("PIL not available. Attempting to use alternate image handling...")
                    # We'll define a minimal Image class as a fallback if needed
                    # This is just a placeholder, the actual implementation should be more robust
                    class Image:
                        @staticmethod
                        def fromarray(arr):
                            return ImageFallback(arr)
                        
                    class ImageFallback:
                        def __init__(self, arr):
                            self.data = arr
                        
                        def resize(self, size, _):
                            return self
                        
                        def save(self, path):
                            # Just save using numpy if possible
                            try:
                                np.save(path + ".npy", self.data)
                                print(f"Saved image data as numpy array to {path}.npy")
                                return True
                            except Exception as e:
                                print(f"Failed to save image: {str(e)}")
                                return False
                
                from inference.inference import Inference, dict2cond
                
                # Get paths using centralized path management
                root_path = PATHS['root_dir']
                config_path = PATHS['config_dir']

                # Load config from .json using relative path
                json_path = os.path.join(config_path, 'model_config.json')
                with open(json_path, 'r') as f:
                    config = json.load(f)
                    config = SimpleNamespace(**config)

                config.out_dir = PATHS['checkpoints_dir']
                config.exp_name = 'v1'
                config.sample_timesteps = 30  # Reduce for faster generation

                device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
                print(f"device: {device}")

                NoisyHandyInferenceCmd.inf = Inference(config, device=device)
                print("Successful Inference Setup")
            except Exception as e:
                print(f"Error initializing model for inference: {str(e)}")
                raise
             
        else:
            print("Inference already setup")
    
    def doIt(self, args):
        """
        Execute the command
        """
        try:
            
            print()
            print(">=========================>")
            print("INFERENCE COMMAND EXECUTED")
            # Parse arguments
            argData = OpenMaya.MArgParser(self.syntax(), args)
            
            # Get paths using centralized path management
            root_path = PATHS['root_dir']
            temp_output_dir = PATHS['temp_output_dir']
            
            # Get parameters from UI using the old API methods
            pattern1 = ""
            if argData.isFlagSet('pattern1'):
                pattern1 = argData.flagArgumentString('pattern1', 0)
            
            pattern2 = ""
            if argData.isFlagSet('pattern2'):
                pattern2 = argData.flagArgumentString('pattern2', 0)
            
            mask_path = ""
            if argData.isFlagSet('maskPath'):
                mask_path = argData.flagArgumentString('maskPath', 0)
            
            blend_factor = 0.5
            if argData.isFlagSet('blendFactor'):
                blend_factor = argData.flagArgumentDouble('blendFactor', 0)

            pattern1param = {}
            if argData.isFlagSet('pattern1Params'):
                pattern1_params_str = argData.flagArgumentString('pattern1Params', 0)
                pattern1param = json.loads(pattern1_params_str)

            pattern2param = {}
            if argData.isFlagSet('pattern2Params'):
                pattern2_params_str = argData.flagArgumentString('pattern2Params', 0)
                pattern2param = json.loads(pattern2_params_str)
            
            print(pattern1)
            print(pattern1param)
            print(pattern2)
            print(pattern2param)
            print(mask_path)
            print(blend_factor)

            res = None
            H, W = 256, 256
            
            # Import here to ensure paths are set up
            import numpy as np
            import torch
            from PIL import Image
            from inference.inference import Inference, dict2cond
            
            if pattern2:
                print("into blending")
                # Set up parameters for first noise pattern
                c1 = {
                    'cls': pattern1,
                    'sbsparams': pattern1param
                }
                
                # Set up parameters for second noise pattern
                c2 = {
                    'cls': pattern2,
                    'sbsparams': pattern2param
                }

                with torch.no_grad():
                    res = NoisyHandyInferenceCmd.inf.slerp_mask(
                        mask=mask_path,
                        dict1=c1,
                        dict2=c2,
                        H=H,
                        W=W,
                        blending_factor=blend_factor
                    )
                # Use path from centralized configuration
                output_path = os.path.join(temp_output_dir, 'tmp_output.png')
                print("finish blending")
            else:
                print("into single")
                # Set up parameters for noise pattern
                c = {
                    'cls': pattern1,
                    'sbsparams': pattern1param
                }
                
                # Generate the noise - use the standalone dict2cond function
                with torch.no_grad():
                    sbsparams, classes = dict2cond(c, H=H, W=W)
                    sbsparams = sbsparams.cuda()
                    classes = classes.cuda()
                    res = NoisyHandyInferenceCmd.inf.generate(sbsparams=sbsparams, classes=classes)
                # Use path from centralized configuration
                output_path = os.path.join(temp_output_dir, f'tmp_{pattern1}.png')
                print("finish single")
            
            if res is not None:
                print("converting to image")
                if len(res.shape) == 4:
                    res = res[0]  # Take the first image if it's a batch
        
                # Convert to numpy and scale to 0-255
                img_np = res.cpu().numpy().transpose(1, 2, 0) * 255
                img_np = img_np.clip(0, 255).astype(np.uint8)
                
                # If it's a grayscale image, remove the channel dimension
                if img_np.shape[2] == 1:
                    img_np = img_np[:, :, 0]
                img = Image.fromarray(img_np)

                # Make sure output directory exists
                os.makedirs(os.path.dirname(output_path), exist_ok=True)
                
                img = img.resize((350, 350), Image.Resampling.LANCZOS)
                img.save(output_path)
                print(f"Generated image save to {output_path}")

                self.setResult(output_path)
            else:
                OpenMaya.MGlobal.displayError("Failed to generate image")
            
        except Exception as e:
            OpenMaya.MGlobal.displayError(f"Error running NoisyHandy inference: {str(e)}")
            raise
    
    @staticmethod
    def cmdCreator():
        """Create an instance of the command"""
        return OpenMayaMPx.asMPxPtr(NoisyHandyInferenceCmd())
    
    @staticmethod
    def syntaxCreator():
        """Create the command syntax object"""
        syntax = OpenMaya.MSyntax()
        
        # Add flags for the command
        syntax.addFlag('-p1', '-pattern1', OpenMaya.MSyntax.kString)
        syntax.addFlag('-p2', '-pattern2', OpenMaya.MSyntax.kString)
        syntax.addFlag('-ms', '-maskPath', OpenMaya.MSyntax.kString)
        syntax.addFlag('-bf', '-blendFactor', OpenMaya.MSyntax.kDouble)

        # Add flags for parameter dictionaries
        # Using string flags to pass JSON-encoded parameter dictionaries
        syntax.addFlag('-p1p', '-pattern1Params', OpenMaya.MSyntax.kString)
        syntax.addFlag('-p2p', '-pattern2Params', OpenMaya.MSyntax.kString)

        return syntax

# NoisyHandy Node Implementation
class NoisyHandyNode(OpenMayaMPx.MPxNode):
    """
    Maya node that represents a NoisyHandy generated noise texture
    This node can be connected to other Maya nodes like a standard noise node
    """
    # Class attributes for the node
    id = NOISY_HANDY_NODE_ID
    typeName = NOISY_HANDY_NODE_TYPE
    
    # Attribute handles (will be populated in initialize)
    outColorAttr = OpenMaya.MObject()
    outAlphaAttr = OpenMaya.MObject()
    patternAttr = OpenMaya.MObject()
    pattern2Attr = OpenMaya.MObject()
    blendFactorAttr = OpenMaya.MObject()
    scaleAttr = OpenMaya.MObject()
    offsetAttr = OpenMaya.MObject()
    timeAttr = OpenMaya.MObject()
    parameterMapAttr = OpenMaya.MObject()
    texturePathAttr = OpenMaya.MObject()
    
    # UV Input
    uvCoordAttr = OpenMaya.MObject()
    
    # Animation related
    animateNoiseAttr = OpenMaya.MObject()
    animationSpeedAttr = OpenMaya.MObject()
    
    # Texture resolution
    resolutionAttr = OpenMaya.MObject()
    
    # Noise parameters - directly on the node
    noiseFrequencyAttr = OpenMaya.MObject()
    noiseOctavesAttr = OpenMaya.MObject()
    noisePersistenceAttr = OpenMaya.MObject()
    
    # Texture file path
    texturePath = ""
    pattern1Value = ""
    pattern2Value = ""
    pattern1Params = {}
    pattern2Params = {}
    
    def __init__(self):
        OpenMayaMPx.MPxNode.__init__(self)
        # Cache for generated texture data
        self.textureData = None
        self.lastParams = {}
    
    def loadTexture(self, path):
        """Load texture from file and cache it"""
        if not path or not os.path.exists(path):
            return None
        
        try:
            from PIL import Image
            img = Image.open(path)
            img_array = np.array(img)
            return img_array
        except Exception as e:
            print(f"Error loading texture: {str(e)}")
            return None
    
    def sampleTexture(self, textureData, u, v):
        """
        Sample texture at given UV coordinates
        Returns RGB tuple normalized to 0-1
        """
        if textureData is None:
            return (0.5, 0.5, 0.5)  # Default gray
            
        try:
            # Get texture dimensions
            height, width = textureData.shape[:2]
            
            # Convert UV (0-1) to pixel coordinates
            x = int((u % 1.0) * (width - 1))
            y = int((1.0 - (v % 1.0)) * (height - 1))  # Flip Y for proper UV orientation
            
            # Sample the texture
            pixel = textureData[y, x]
            
            # Normalize to 0-1 range
            if len(pixel) >= 3:
                return (pixel[0] / 255.0, pixel[1] / 255.0, pixel[2] / 255.0)
            else:
                # Grayscale image
                gray = pixel / 255.0
                return (gray, gray, gray)
        except Exception as e:
            print(f"Error sampling texture: {str(e)}")
            return (0.5, 0.5, 0.5)
    
    def compute(self, plug, dataBlock):
        """
        Compute the output values based on the input values
        This is called by Maya when it needs to evaluate the node
        """
        if plug == NoisyHandyNode.outColorAttr or plug == NoisyHandyNode.outAlphaAttr:
            
            # Get values from input attributes
            timeHandle = dataBlock.inputValue(NoisyHandyNode.timeAttr)
            time = timeHandle.asTime().asUnits(OpenMaya.MTime.kSeconds)
            
            scaleHandle = dataBlock.inputValue(NoisyHandyNode.scaleAttr)
            scale = scaleHandle.asFloat3()
            
            offsetHandle = dataBlock.inputValue(NoisyHandyNode.offsetAttr)
            offset = offsetHandle.asFloat3()
            
            blendFactorHandle = dataBlock.inputValue(NoisyHandyNode.blendFactorAttr)
            blendFactor = blendFactorHandle.asFloat()
            
            patternHandle = dataBlock.inputValue(NoisyHandyNode.patternAttr)
            pattern = patternHandle.asString()
            
            pattern2Handle = dataBlock.inputValue(NoisyHandyNode.pattern2Attr)
            pattern2 = pattern2Handle.asString()
            
            texturePathHandle = dataBlock.inputValue(NoisyHandyNode.texturePathAttr)
            texturePath = texturePathHandle.asString()
            
            # Get animation options
            animateNoiseHandle = dataBlock.inputValue(NoisyHandyNode.animateNoiseAttr)
            animateNoise = animateNoiseHandle.asBool()
            
            animationSpeedHandle = dataBlock.inputValue(NoisyHandyNode.animationSpeedAttr)
            animationSpeed = animationSpeedHandle.asFloat()
            
            # Get noise parameters
            noiseFrequencyHandle = dataBlock.inputValue(NoisyHandyNode.noiseFrequencyAttr)
            noiseFrequency = noiseFrequencyHandle.asFloat()
            
            noiseOctavesHandle = dataBlock.inputValue(NoisyHandyNode.noiseOctavesAttr)
            noiseOctaves = noiseOctavesHandle.asInt()
            
            noisePersistenceHandle = dataBlock.inputValue(NoisyHandyNode.noisePersistenceAttr)
            noisePersistence = noisePersistenceHandle.asFloat()
            
            # Get UV coordinates from input or from local position
            uvCoordHandle = dataBlock.inputValue(NoisyHandyNode.uvCoordAttr)
            uv = uvCoordHandle.asFloat2()
            
            # Apply scaling and offset to UV
            u = (uv[0] * scale[0]) + offset[0]
            v = (uv[1] * scale[1]) + offset[1]
            
            # Apply time offset for animation if enabled
            if animateNoise:
                offset_time = time * animationSpeed
                # Modify UV based on time for animation
                u += offset_time * 0.1
                v += offset_time * 0.05
            
            # Access output handles
            outColorHandle = dataBlock.outputValue(NoisyHandyNode.outColorAttr)
            outAlphaHandle = dataBlock.outputValue(NoisyHandyNode.outAlphaAttr)
            
            # If we have a texture path, use that as our output color
            if texturePath and os.path.exists(texturePath):
                # Load texture if not cached or parameters changed
                paramHash = f"{texturePath}_{u}_{v}_{scale[0]}_{scale[1]}_{offset[0]}_{offset[1]}_{time}"
                if self.textureData is None or self.lastParams.get('hash') != paramHash:
                    self.textureData = self.loadTexture(texturePath)
                    self.lastParams['hash'] = paramHash
                
                if self.textureData is not None:
                    # Sample texture at UV coordinates
                    r, g, b = self.sampleTexture(self.textureData, u, v)
                    
                    # Set output color
                    outColor = OpenMaya.MFloatVector(r, g, b)
                    outColorHandle.setMFloatVector(outColor)
                    
                    # Calculate luminance for alpha
                    alpha = (r * 0.299 + g * 0.587 + b * 0.114)
                    outAlphaHandle.setFloat(alpha)
                else:
                    # Default if texture can't be loaded
                    outColorHandle.setMFloatVector(OpenMaya.MFloatVector(0.5, 0.5, 0.5))
                    outAlphaHandle.setFloat(1.0)
            else:
                # No texture, generate procedural noise based on attributes
                # This is a simple noise implementation that could be improved
                import math
                
                # Simple Perlin-like noise function (simplified for example)
                noise_val = math.sin(u * noiseFrequency * 10) * math.cos(v * noiseFrequency * 10) * 0.5 + 0.5
                
                # Use noise parameters to adjust the output
                noise_val = math.pow(noise_val, noisePersistence)
                
                # Set output color based on noise value
                outColor = OpenMaya.MFloatVector(noise_val, noise_val, noise_val)
                outColorHandle.setMFloatVector(outColor)
                outAlphaHandle.setFloat(noise_val)
                
            # Mark the outputs as clean
            outColorHandle.setClean()
            outAlphaHandle.setClean()
            
            return OpenMayaMPx.MPxStatus.kSuccess
            
        return OpenMayaMPx.MPxStatus.kUnknownParameter
    
    @staticmethod
    def nodeCreator():
        """Create an instance of the node"""
        return OpenMayaMPx.asMPxPtr(NoisyHandyNode())
    
    @staticmethod
    def nodeInitializer():
        """Initialize the node attributes"""
        # Create function sets for attribute creation
        nAttr = OpenMaya.MFnNumericAttribute()
        tAttr = OpenMaya.MFnTypedAttribute()
        uAttr = OpenMaya.MFnUnitAttribute()
        
        # Create output color attribute (RGB)
        NoisyHandyNode.outColorAttr = nAttr.createColor("outColor", "oc")
        nAttr.setWritable(False)
        nAttr.setStorable(False)
        nAttr.setKeyable(False)
        
        # Create output alpha attribute (float)
        NoisyHandyNode.outAlphaAttr = nAttr.create("outAlpha", "oa", OpenMaya.MFnNumericData.kFloat, 1.0)
        nAttr.setWritable(False)
        nAttr.setStorable(False)
        nAttr.setKeyable(False)
        
        # Create pattern attribute (string)
        NoisyHandyNode.patternAttr = tAttr.create("pattern", "pat", OpenMaya.MFnData.kString)
        tAttr.setKeyable(True)
        tAttr.setStorable(True)
        
        # Create pattern2 attribute (string)
        NoisyHandyNode.pattern2Attr = tAttr.create("pattern2", "pat2", OpenMaya.MFnData.kString)
        tAttr.setKeyable(True)
        tAttr.setStorable(True)
        
        # Create blend factor attribute (float)
        NoisyHandyNode.blendFactorAttr = nAttr.create("blendFactor", "bf", OpenMaya.MFnNumericData.kFloat, 0.5)
        nAttr.setKeyable(True)
        nAttr.setStorable(True)
        nAttr.setMin(0.0)
        nAttr.setMax(1.0)
        
        # Create scale attribute (vector)
        NoisyHandyNode.scaleAttr = nAttr.create("scale", "sc", OpenMaya.MFnNumericData.k3Float)
        nAttr.setDefault(1.0, 1.0, 1.0)
        nAttr.setKeyable(True)
        nAttr.setStorable(True)
        
        # Create offset attribute (vector)
        NoisyHandyNode.offsetAttr = nAttr.create("offset", "of", OpenMaya.MFnNumericData.k3Float)
        nAttr.setDefault(0.0, 0.0, 0.0)
        nAttr.setKeyable(True)
        nAttr.setStorable(True)
        
        # Create time attribute
        NoisyHandyNode.timeAttr = uAttr.create("time", "tm", OpenMaya.MFnUnitAttribute.kTime, 0.0)
        uAttr.setKeyable(True)
        uAttr.setStorable(True)
        
        # Create texture path attribute (string)
        NoisyHandyNode.texturePathAttr = tAttr.create("texturePath", "tp", OpenMaya.MFnData.kString)
        tAttr.setKeyable(False)
        tAttr.setStorable(True)
        tAttr.setHidden(False)  # Make visible in UI
        
        # Create UV coordinate attribute (float2)
        NoisyHandyNode.uvCoordAttr = nAttr.create("uvCoord", "uv", OpenMaya.MFnNumericData.k2Float)
        nAttr.setDefault(0.0, 0.0)
        nAttr.setKeyable(True)
        nAttr.setStorable(True)
        
        # Create animation controls
        NoisyHandyNode.animateNoiseAttr = nAttr.create("animateNoise", "an", OpenMaya.MFnNumericData.kBoolean, False)
        nAttr.setKeyable(True)
        nAttr.setStorable(True)
        
        NoisyHandyNode.animationSpeedAttr = nAttr.create("animationSpeed", "as", OpenMaya.MFnNumericData.kFloat, 1.0)
        nAttr.setKeyable(True)
        nAttr.setStorable(True)
        nAttr.setMin(0.0)
        
        # Create noise parameter attributes
        NoisyHandyNode.noiseFrequencyAttr = nAttr.create("noiseFrequency", "nf", OpenMaya.MFnNumericData.kFloat, 1.0)
        nAttr.setKeyable(True)
        nAttr.setStorable(True)
        nAttr.setMin(0.01)
        nAttr.setMax(10.0)
        
        NoisyHandyNode.noiseOctavesAttr = nAttr.create("noiseOctaves", "no", OpenMaya.MFnNumericData.kInt, 4)
        nAttr.setKeyable(True)
        nAttr.setStorable(True)
        nAttr.setMin(1)
        nAttr.setMax(10)
        
        NoisyHandyNode.noisePersistenceAttr = nAttr.create("noisePersistence", "np", OpenMaya.MFnNumericData.kFloat, 0.5)
        nAttr.setKeyable(True)
        nAttr.setStorable(True)
        nAttr.setMin(0.0)
        nAttr.setMax(1.0)
        
        # Create resolution attribute for the noise texture
        NoisyHandyNode.resolutionAttr = nAttr.create("resolution", "res", OpenMaya.MFnNumericData.kInt, 256)
        nAttr.setKeyable(True)
        nAttr.setStorable(True)
        nAttr.setMin(64)
        nAttr.setMax(1024)
        
        # Add attributes to the node
        NoisyHandyNode.addAttribute(NoisyHandyNode.outColorAttr)
        NoisyHandyNode.addAttribute(NoisyHandyNode.outAlphaAttr)
        NoisyHandyNode.addAttribute(NoisyHandyNode.patternAttr)
        NoisyHandyNode.addAttribute(NoisyHandyNode.pattern2Attr)
        NoisyHandyNode.addAttribute(NoisyHandyNode.blendFactorAttr)
        NoisyHandyNode.addAttribute(NoisyHandyNode.scaleAttr)
        NoisyHandyNode.addAttribute(NoisyHandyNode.offsetAttr)
        NoisyHandyNode.addAttribute(NoisyHandyNode.timeAttr)
        NoisyHandyNode.addAttribute(NoisyHandyNode.texturePathAttr)
        NoisyHandyNode.addAttribute(NoisyHandyNode.uvCoordAttr)
        NoisyHandyNode.addAttribute(NoisyHandyNode.animateNoiseAttr)
        NoisyHandyNode.addAttribute(NoisyHandyNode.animationSpeedAttr)
        NoisyHandyNode.addAttribute(NoisyHandyNode.noiseFrequencyAttr)
        NoisyHandyNode.addAttribute(NoisyHandyNode.noiseOctavesAttr)
        NoisyHandyNode.addAttribute(NoisyHandyNode.noisePersistenceAttr)
        NoisyHandyNode.addAttribute(NoisyHandyNode.resolutionAttr)
        
        # Set up attribute dependencies for compute
        NoisyHandyNode.attributeAffects(NoisyHandyNode.patternAttr, NoisyHandyNode.outColorAttr)
        NoisyHandyNode.attributeAffects(NoisyHandyNode.patternAttr, NoisyHandyNode.outAlphaAttr)
        NoisyHandyNode.attributeAffects(NoisyHandyNode.pattern2Attr, NoisyHandyNode.outColorAttr)
        NoisyHandyNode.attributeAffects(NoisyHandyNode.pattern2Attr, NoisyHandyNode.outAlphaAttr)
        NoisyHandyNode.attributeAffects(NoisyHandyNode.blendFactorAttr, NoisyHandyNode.outColorAttr)
        NoisyHandyNode.attributeAffects(NoisyHandyNode.blendFactorAttr, NoisyHandyNode.outAlphaAttr)
        NoisyHandyNode.attributeAffects(NoisyHandyNode.scaleAttr, NoisyHandyNode.outColorAttr)
        NoisyHandyNode.attributeAffects(NoisyHandyNode.scaleAttr, NoisyHandyNode.outAlphaAttr)
        NoisyHandyNode.attributeAffects(NoisyHandyNode.offsetAttr, NoisyHandyNode.outColorAttr)
        NoisyHandyNode.attributeAffects(NoisyHandyNode.offsetAttr, NoisyHandyNode.outAlphaAttr)
        NoisyHandyNode.attributeAffects(NoisyHandyNode.timeAttr, NoisyHandyNode.outColorAttr)
        NoisyHandyNode.attributeAffects(NoisyHandyNode.timeAttr, NoisyHandyNode.outAlphaAttr)
        NoisyHandyNode.attributeAffects(NoisyHandyNode.texturePathAttr, NoisyHandyNode.outColorAttr)
        NoisyHandyNode.attributeAffects(NoisyHandyNode.texturePathAttr, NoisyHandyNode.outAlphaAttr)
        NoisyHandyNode.attributeAffects(NoisyHandyNode.uvCoordAttr, NoisyHandyNode.outColorAttr)
        NoisyHandyNode.attributeAffects(NoisyHandyNode.uvCoordAttr, NoisyHandyNode.outAlphaAttr)
        NoisyHandyNode.attributeAffects(NoisyHandyNode.animateNoiseAttr, NoisyHandyNode.outColorAttr)
        NoisyHandyNode.attributeAffects(NoisyHandyNode.animateNoiseAttr, NoisyHandyNode.outAlphaAttr)
        NoisyHandyNode.attributeAffects(NoisyHandyNode.animationSpeedAttr, NoisyHandyNode.outColorAttr)
        NoisyHandyNode.attributeAffects(NoisyHandyNode.animationSpeedAttr, NoisyHandyNode.outAlphaAttr)
        NoisyHandyNode.attributeAffects(NoisyHandyNode.noiseFrequencyAttr, NoisyHandyNode.outColorAttr)
        NoisyHandyNode.attributeAffects(NoisyHandyNode.noiseFrequencyAttr, NoisyHandyNode.outAlphaAttr)
        NoisyHandyNode.attributeAffects(NoisyHandyNode.noiseOctavesAttr, NoisyHandyNode.outColorAttr)
        NoisyHandyNode.attributeAffects(NoisyHandyNode.noiseOctavesAttr, NoisyHandyNode.outAlphaAttr)
        NoisyHandyNode.attributeAffects(NoisyHandyNode.noisePersistenceAttr, NoisyHandyNode.outColorAttr)
        NoisyHandyNode.attributeAffects(NoisyHandyNode.noisePersistenceAttr, NoisyHandyNode.outAlphaAttr)
        NoisyHandyNode.attributeAffects(NoisyHandyNode.resolutionAttr, NoisyHandyNode.outColorAttr)
        NoisyHandyNode.attributeAffects(NoisyHandyNode.resolutionAttr, NoisyHandyNode.outAlphaAttr)

# Create Node Command Implementation
class CreateNoisyHandyNodeCmd(OpenMayaMPx.MPxCommand):
    """
    Command to create a NoisyHandy node with texture and parameters from the UI
    """
    command_name = "createNoisyHandyNode"
    
    def __init__(self):
        OpenMayaMPx.MPxCommand.__init__(self)
        self.node_name = ""
    
    def doIt(self, args):
        """Execute the command"""
        try:
            # Parse arguments
            argData = OpenMaya.MArgParser(self.syntax(), args)
            
            # Get parameters
            texture_path = ""
            if argData.isFlagSet('texturePath'):
                texture_path = argData.flagArgumentString('texturePath', 0)
            
            pattern = "damas"
            if argData.isFlagSet('pattern'):
                pattern = argData.flagArgumentString('pattern', 0)
            
            pattern2 = ""
            if argData.isFlagSet('pattern2'):
                pattern2 = argData.flagArgumentString('pattern2', 0)
            
            blend_factor = 0.5
            if argData.isFlagSet('blendFactor'):
                blend_factor = argData.flagArgumentDouble('blendFactor', 0)
            
            # Create the node
            node_name = cmds.createNode(NOISY_HANDY_NODE_TYPE, name="noisyHandyNode#")
            
            # Set values on the node
            cmds.setAttr(node_name + ".pattern", pattern, type="string")
            if pattern2:
                cmds.setAttr(node_name + ".pattern2", pattern2, type="string")
            cmds.setAttr(node_name + ".blendFactor", blend_factor)
            
            if texture_path and os.path.exists(texture_path):
                cmds.setAttr(node_name + ".texturePath", texture_path, type="string")
            
            # Store the node name for undoIt/redoIt
            self.node_name = node_name
            
            # Set the result to the node name
            self.setResult(node_name)
            
            OpenMaya.MGlobal.displayInfo(f"Created NoisyHandy node: {node_name}")
            
        except Exception as e:
            OpenMaya.MGlobal.displayError(f"Error creating NoisyHandy node: {str(e)}")
            raise
    
    def undoIt(self):
        """Undo the command"""
        if self.node_name:
            try:
                cmds.delete(self.node_name)
            except:
                pass
    
    def redoIt(self):
        """Redo the command"""
        # Implementation would recreate the node with the same parameters
        pass
    
    def isUndoable(self):
        """Indicate that this command is undoable"""
        return True
    
    @staticmethod
    def cmdCreator():
        """Create an instance of the command"""
        return OpenMayaMPx.asMPxPtr(CreateNoisyHandyNodeCmd())
    
    @staticmethod
    def syntaxCreator():
        """Create the command syntax object"""
        syntax = OpenMaya.MSyntax()
        
        # Add flags for the command
        syntax.addFlag('-tp', '-texturePath', OpenMaya.MSyntax.kString)
        syntax.addFlag('-p', '-pattern', OpenMaya.MSyntax.kString)
        syntax.addFlag('-p2', '-pattern2', OpenMaya.MSyntax.kString)
        syntax.addFlag('-bf', '-blendFactor', OpenMaya.MSyntax.kDouble)
        
        return syntax

# Plugin initialization and cleanup
def initializePlugin(mobject):
    """
    Initialize the plugin when Maya loads it
    """
    # SET THE PLUGIN INFORMATION
    mplugin = OpenMayaMPx.MFnPlugin(mobject, "cg@penn", PLUGIN_VERSION, "2025")
    
    try:
        mplugin.registerCommand(
            NoisyHandyInferenceCmd.command_name,
            NoisyHandyInferenceCmd.cmdCreator,
            NoisyHandyInferenceCmd.syntaxCreator
        )
        
        mplugin.registerNode(
            NoisyHandyNode.typeName,
            NoisyHandyNode.id,
            NoisyHandyNode.nodeCreator,
            NoisyHandyNode.nodeInitializer,
            OpenMayaMPx.MPxNode.kDependNode
        )
        
        mplugin.registerCommand(
            CreateNoisyHandyNodeCmd.command_name,
            CreateNoisyHandyNodeCmd.cmdCreator,
            CreateNoisyHandyNodeCmd.syntaxCreator
        )
        
        # Create the UI when plugin is loaded
        try:
            import noisyhandy_maya_ui
            noisyhandy_maya_ui.create_menu()  # Create menu instead of showing UI directly
            print("NoisyHandy menu created successfully")
        except Exception as e:
            OpenMaya.MGlobal.displayWarning(f"Error creating UI menu: {str(e)}")
            
        print(f"{PLUGIN_NAME} v{PLUGIN_VERSION} loaded successfully")
    except:
        sys.stderr.write(f"Failed to register command: {NoisyHandyInferenceCmd.command_name}\n")
        raise

def uninitializePlugin(mobject):
    """
    Clean up when the plugin is unloaded
    """
    mplugin = OpenMayaMPx.MFnPlugin(mobject)
    
    try:
        # First find and clean up any existing noise nodes
        try:
            # Find all NoisyHandy nodes
            noisy_nodes = cmds.ls(type=NOISY_HANDY_NODE_TYPE)
            
            if noisy_nodes and len(noisy_nodes) > 0:
                print(f"Found {len(noisy_nodes)} NoisyHandy nodes to clean up.")
                
                # Get connected place2d nodes
                place2d_nodes = []
                for node in noisy_nodes:
                    # Find any connected place2dTexture nodes
                    connected_nodes = cmds.listConnections(node, type="place2dTexture")
                    if connected_nodes:
                        place2d_nodes.extend(connected_nodes)
                
                # Get all the connected shading networks to clean up later
                connected_shaders = []
                connected_sg_sets = []
                
                for node in noisy_nodes:
                    connections = cmds.listConnections(f"{node}.outColor") or []
                    for conn in connections:
                        conn_type = cmds.nodeType(conn)
                        if conn_type in ["lambert", "blinn", "phong", "standardSurface", "displacementShader", "bump3d"]:
                            connected_shaders.append(conn)
                        elif conn_type == "shadingEngine":
                            connected_sg_sets.append(conn)
                
                # Delete the NoisyHandy nodes - this disconnects them from the network
                cmds.delete(noisy_nodes)
                print(f"Deleted {len(noisy_nodes)} NoisyHandy nodes.")
                
                # Clean up place2d nodes that were connected to our nodes
                if place2d_nodes:
                    # Remove duplicates
                    place2d_nodes = list(set(place2d_nodes))
                    # Check if each node still exists (might be deleted as part of node deletion)
                    existing_place2d = [node for node in place2d_nodes if cmds.objExists(node)]
                    if existing_place2d:
                        cmds.delete(existing_place2d)
                        print(f"Deleted {len(existing_place2d)} place2dTexture nodes.")
                
                # Clean up any shading networks that might not be deleted automatically
                if connected_shaders:
                    # Remove duplicates and check existence
                    connected_shaders = list(set(connected_shaders))
                    existing_shaders = [node for node in connected_shaders if cmds.objExists(node)]
                    if existing_shaders:
                        # Only delete shaders that have no other connections
                        for shader in existing_shaders[:]:  # Copy the list to avoid modification during iteration
                            # Check if this shader has any inputs other than from our deleted nodes
                            has_other_inputs = False
                            inputs = cmds.listConnections(shader, destination=False, source=True) or []
                            for input_node in inputs:
                                if input_node not in noisy_nodes and cmds.objExists(input_node):
                                    has_other_inputs = True
                                    break
                            
                            # Only delete if it has no other inputs
                            if not has_other_inputs and cmds.objExists(shader):
                                cmds.delete(shader)
                                print(f"Deleted orphaned shader: {shader}")
                
                # Clean up any shading groups that might be orphaned
                if connected_sg_sets:
                    connected_sg_sets = list(set(connected_sg_sets))
                    existing_sg = [node for node in connected_sg_sets if cmds.objExists(node)]
                    if existing_sg:
                        for sg in existing_sg[:]:  # Copy the list to avoid modification during iteration
                            # Check if this shading group has any surface shader connected
                            has_surface_shader = cmds.listConnections(f"{sg}.surfaceShader", destination=False, source=True)
                            # Delete only if it has no surface shader
                            if not has_surface_shader and cmds.objExists(sg):
                                cmds.delete(sg)
                                print(f"Deleted orphaned shading group: {sg}")
                
                print("Cleanup of NoisyHandy nodes and related networks completed.")
            else:
                print("No NoisyHandy nodes found to clean up.")
        except Exception as e:
            print(f"Error during node cleanup: {str(e)}")
            # Continue with deregistration even if cleanup fails
        
        # Now deregister the commands and node types
        mplugin.deregisterCommand(NoisyHandyInferenceCmd.command_name)
        mplugin.deregisterNode(NoisyHandyNode.id)
        mplugin.deregisterCommand(CreateNoisyHandyNodeCmd.command_name)
        
        # Clean up UI elements
        try:
            import noisyhandy_maya_ui
            noisyhandy_maya_ui.cleanup_ui()
        except Exception as e:
            OpenMaya.MGlobal.displayWarning(f"Error cleaning up UI: {str(e)}")
        
        # Clean up temporary files in temp_output directory
        try:
            temp_output_dir = PATHS['temp_output_dir']
            if os.path.exists(temp_output_dir):
                for tmp_file in os.listdir(temp_output_dir):
                    if tmp_file.startswith('tmp_'):
                        try:
                            file_path = os.path.join(temp_output_dir, tmp_file)
                            os.remove(file_path)
                            print(f"Deleted temporary file: {file_path}")
                        except Exception as file_e:
                            print(f"Failed to delete temporary file {tmp_file}: {str(file_e)}")
        except Exception as e:
            OpenMaya.MGlobal.displayWarning(f"Error cleaning up temporary files: {str(e)}")
        
        OpenMaya.MGlobal.displayInfo(f"{PLUGIN_NAME} v{PLUGIN_VERSION} unloaded successfully")
    except Exception as e:
        sys.stderr.write(f"Error during plugin unload: {str(e)}\n")
        raise