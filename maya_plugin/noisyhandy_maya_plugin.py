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

# Import Noise Node Related settings
from noisyhandy_maya_noisenode import CreateNoisyHandyNodeCmd, NoisyHandyNode, NOISY_HANDY_NODE_TYPE, NOISY_HANDY_NODE_ID
import noisyhandy_maya_ui
from noisyhandy_config import PATHS, PLUGIN_VERSION, PLUGIN_NAME

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
        print("<<<<<<<<<<<<<<<<<<<<<<<<<<")
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

# Value Initialization
HAS_DEPENDENCIES = setup_dependencies()

##################################################################################################################################
##################################################################################################################################
##################################################################################################################################
##################################################################################################################################
############################################## END OF SETUP ######################################################################

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
        
        # Register node with texture classification for Hypershade visibility
        mplugin.registerNode(
            NoisyHandyNode.typeName,
            NoisyHandyNode.id,
            NoisyHandyNode.nodeCreator,
            NoisyHandyNode.nodeInitializer,
            OpenMayaMPx.MPxNode.kDependNode,
            "texture/2d"  # This classification makes it visible in Hypershade
        )
        
        mplugin.registerCommand(
            CreateNoisyHandyNodeCmd.command_name,
            CreateNoisyHandyNodeCmd.cmdCreator,
            CreateNoisyHandyNodeCmd.syntaxCreator
        )
        
        # Create the UI when plugin is loaded
        try:
            import noisyhandy_maya_ui
            # Add custom example functions for direct access
            from noisyhandy_maya_noisenode import create_simple_terrain_example
            noisyhandy_maya_ui.create_menu()  # Create menu instead of showing UI directly
            
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