import os
import sys
import json
from types import SimpleNamespace
import numpy as np
import torch
from PIL import Image

import maya.cmds as cmds
import maya.OpenMaya as OpenMaya
import maya.OpenMayaMPx as OpenMayaMPx

import noisyhandy_maya_ui

# Plugin information
PLUGIN_NAME = "NoisyHandyPlugin"
PLUGIN_VERSION = "1.0.0"

# Add project root to sys.path to import our model modules
def setup_paths():
    """Setup paths to ensure our model modules can be imported"""
    # Get the directory of this plugin
    plugin_path = cmds.pluginInfo("noisyhandy_maya_plugin.py", query=True, path=True)
    plugin_dir = os.path.dirname(plugin_path)

    # Get the root directory (parent of the plugin dir)
    root_dir = os.path.dirname(plugin_dir)

    # Add the root directory to sys.path if it's not already there
    if root_dir not in sys.path:
        sys.path.append(root_dir)
    
    print(f"Added {root_dir} to sys.path")

# Maya command for running inference
class NoisyHandyInferenceCmd(OpenMayaMPx.MPxCommand):
    """Maya command to run inference with the NoisyHandy model"""
    
    command_name = "noisyHandyInference"
    inf = None
    
    def __init__(self):
        OpenMayaMPx.MPxCommand.__init__(self)
        
        if NoisyHandyInferenceCmd.inf is None:
            try:
                from inference.inference import Inference, dict2cond

                # Load config from .json
                json_path = os.path.join('D:/Projects/Upenn_CIS_6600/NoisyHandy/LYY/NoisyHandy/config/model_config.json')
                with open(json_path, 'r') as f:
                    config = json.load(f)
                    config = SimpleNamespace(**config)

                config.out_dir = 'D:/Projects/Upenn_CIS_6600/NoisyHandy/LYY/NoisyHandy/checkpoints'
                config.exp_name = 'v1'
                config.sample_timesteps = 40  # Reduce for faster generation

                device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
                print(f"device :{device}")

                NoisyHandyInferenceCmd.inf = Inference(config, device=device)
                print("Successful Inference Setup")
            except Exception as e:
                print(f"Error initializing model for inference: {str(e)}")
                raise
        else:
            print("Inference already setup")
    
    def doIt(self, args):
        """Execute the command"""
        try:
            print("into doit")
            # Parse arguments
            argData = OpenMaya.MArgParser(self.syntax(), args)
            
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
            
            print(pattern1)
            print(pattern2)
            print(mask_path)
            print(blend_factor)

            res = None
            H, W = 256, 256

            from inference.inference import Inference, dict2cond
            from config.noise_config import noise_types, noise_aliases, ntype_to_params_map
            if pattern2:
                print("into blending")
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

                with torch.no_grad():
                    res = NoisyHandyInferenceCmd.inf.slerp_mask(
                        mask=mask_path,
                        dict1=c1,
                        dict2=c2,
                        H=H,
                        W=W,
                        blending_factor=blend_factor
                    )
                output_path = 'D:/Projects/Upenn_CIS_6600/NoisyHandy/LYY/NoisyHandy/inference/masks/tmp_output.png'
                print("finish blending")
            else:
                print("into single")
                # Set up parameters for noise pattern
                c = {
                    'cls': pattern1,
                    'sbsparams': {
                        p: 0.5 for p in ntype_to_params_map.get(noise_aliases.get(pattern1, pattern1), [])
                    }
                }
                
                # Generate the noise - use the standalone dict2cond function
                with torch.no_grad():
                    sbsparams, classes = dict2cond(c, H=H, W=W)
                    sbsparams = sbsparams.cuda()
                    classes = classes.cuda()
                    res = NoisyHandyInferenceCmd.inf.generate(sbsparams=sbsparams, classes=classes)
                output_path = 'D:/Projects/Upenn_CIS_6600/NoisyHandy/LYY/NoisyHandy/inference/masks/tmp_' + pattern1 + '.png'
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

        return syntax

# Plugin initialization and cleanup
def initializePlugin(mobject):
    """Initialize the plugin when Maya loads it"""
    mplugin = OpenMayaMPx.MFnPlugin(mobject, "cg@penn", PLUGIN_VERSION, "2025")
    
    # Setup paths for importing our modules
    setup_paths()
    
    try:
        mplugin.registerCommand(
            NoisyHandyInferenceCmd.command_name,
            NoisyHandyInferenceCmd.cmdCreator,
            NoisyHandyInferenceCmd.syntaxCreator
        )
        print(f"{PLUGIN_NAME} v{PLUGIN_VERSION} loaded successfully")
    except:
        sys.stderr.write(f"Failed to register command: {NoisyHandyInferenceCmd.command_name}\n")
        raise

def uninitializePlugin(mobject):
    """Clean up when the plugin is unloaded"""
    mplugin = OpenMayaMPx.MFnPlugin(mobject)
    
    try:
        mplugin.deregisterCommand(NoisyHandyInferenceCmd.command_name)
        OpenMaya.MGlobal.displayInfo(f"{PLUGIN_NAME} v{PLUGIN_VERSION} unloaded successfully")
    except:
        sys.stderr.write(f"Failed to unregister command: {NoisyHandyInferenceCmd.command_name}\n")
        raise