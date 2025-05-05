################################################################### IMPORT #######
##################################################################################


import maya.cmds as cmds
import maya.mel as mel
import os
import sys
import json
import tempfile

# Add parent directory to path to allow imports from sibling packages
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# Get paths from the plugin itself
from noisyhandy_config import PATHS
from PIL import Image
    
# Now import project-specific modules
try:
    from config.noise_config import noise_aliases, ntype_to_params_map
except ImportError:
    cmds.warning("Could not import some modules. Check your installation.")
    # Fallback defaults
    noise_aliases = {}
    ntype_to_params_map = {}

from config.noise_config import noise_aliases, ntype_to_params_map

##################################################################################
################################################################### END IMPORT ###
##################################################################################



# UI CLASS COMPONENT
class NoisyHandyUI:
    """
    UI for the NoisyHandy Maya plugin
    """
    
    WINDOW_NAME = "NoisyHandyUI"
    WINDOW_TITLE = "NoisyHandy"
    
    # Get paths from the centralized configuration
    ROOT_PATH = PATHS['root_dir']
    MASK_DIR = PATHS['mask_dir']

    # Define patterns and paths dynamically
    NOISE_PATTERNS = ["damas", "galvanic", "cells1", "cells4", "perlin", "gaussian", "voro", "liquid", "fibers", "micro", "rust"]
    MASK_SHAPES = [os.path.splitext(f)[0] for f in os.listdir(MASK_DIR) if f.endswith('.png') and not f.startswith('tmp')]

    NOISE_PARAMETERS = {}

    # Paths for preview images (to be populated)
    PREVIEW_IMAGES_PATH = tempfile.gettempdir()
    
    def __init__(self):
        # Ensure the plugin is loaded before attempting to use any of its commands
        self._ensure_plugin_loaded()
        
        self.pattern1_value = self.NOISE_PATTERNS[0]
        self.pattern2_value = self.NOISE_PATTERNS[1]
        self.mask_shape_value = self.MASK_SHAPES[0]
        self.blend_factor = 0.5

        # File paths for generated previews
        self.pattern1_preview_path = ""
        self.pattern2_preview_path = ""
        self.mask_preview_path = ""
        self.output_preview_path = ""
        
        # UI elements
        self.pattern1_menu = None
        self.pattern2_menu = None
        self.mask_shape_menu = None
        self.blend_slider = None
        self.pattern1_image = None
        self.pattern2_image = None
        self.blend_map_image = None
        self.output_image = None

        # Parameter UI elements and values
        self.pattern1_params_container = None
        self.pattern2_params_container = None
        self.pattern1_param_elements = {}
        self.pattern2_param_elements = {}
        self.pattern1_param_values = {}
        self.pattern2_param_values = {}

        for noise_pattern in self.NOISE_PATTERNS:
            self.NOISE_PARAMETERS[noise_pattern] = ntype_to_params_map.get(noise_aliases.get(noise_pattern, noise_pattern), [])
    
    def _ensure_plugin_loaded(self):
        """Make sure the NoisyHandy plugin is loaded before accessing its commands"""
        plugin_name = "noisyhandy_maya_plugin.py"
        
        # Check if the plugin is already loaded
        if not cmds.pluginInfo(plugin_name, query=True, loaded=True):
            try:
                # Try to load the plugin
                cmds.loadPlugin(plugin_name)
                print(f"Plugin {plugin_name} loaded successfully.")
            except Exception as e:
                cmds.warning(f"Failed to load plugin {plugin_name}: {str(e)}")
                # You might want to show a dialog to the user here
                cmds.confirmDialog(
                    title="Plugin Load Error",
                    message=f"Could not load the NoisyHandy plugin.\nError: {str(e)}",
                    button=["OK"],
                    defaultButton="OK"
                )
        else:
            print(f"Plugin {plugin_name} is already loaded.")

    def create_parameter_controls(self, pattern, parent_container, param_elements, param_values):
        """Create parameter sliders for a given noise pattern"""
        # Remove existing parameter controls
        if cmds.layout(parent_container, exists=True):
            children = cmds.layout(parent_container, query=True, childArray=True)
            if children:
                for child in children:
                    cmds.deleteUI(child)

        # Clear existing UI elements
        param_elements.clear()

        # Clear existing Parameter values
        param_values.clear()
        
        # Create new parameter controls
        for param in self.NOISE_PARAMETERS[pattern]:
            param_values[param] = 0.5
            frame = cmds.frameLayout(
                label=param.capitalize(),
                collapsable=False,
                borderStyle="etchedOut",
                marginWidth=5,
                marginHeight=5,
                labelVisible=True,
                height=50,
                parent=parent_container
            )
            
            # Create a row for the parameter slider
            row = cmds.rowLayout(
                numberOfColumns=3,
                columnWidth3=(20, 250, 80),
                adjustableColumn=2,
                columnAlign3=["left", "center", "right"],
                parent=frame
            )
            
            cmds.text(label="0", width=20)
            
            slider = cmds.floatSlider(
                min=0.0,
                max=1.0,
                value=param_values[param],
                step=0.01,
                changeCommand=lambda value, p=param, pattern=pattern: self.on_parameter_change(pattern, p, value),
                width=250,
                height=20
            )
            
            value_text = cmds.text(label=f"{param_values[param]:.2f}", width=80)
            
            cmds.setParent('..')  # Back to frame
            # Store UI elements for later reference
            param_elements[param] = {
                'slider': slider,
                'text': value_text
            }
            
        cmds.setParent('..')  # Back to container
        
    def create_ui(self):
        """Create the UI window"""
        # Close existing window if it exists
        if cmds.window(self.WINDOW_NAME, exists=True):
            cmds.deleteUI(self.WINDOW_NAME)
        
        # Create window
        window = cmds.window(
            self.WINDOW_NAME, 
            title=self.WINDOW_TITLE,
            widthHeight=(1050, 750)
        )
        
        # Main form layout to control the two main columns
        main_form = cmds.formLayout(parent=window)
        
        # Create left column for controls
        left_column = cmds.columnLayout(
            adjustableColumn=True, 
            columnWidth=365,
            rowSpacing=0,
            parent=main_form
        )
        
        # Pattern 1 selection
        cmds.frameLayout(
            label="Pattern 1", 
            collapsable=False, 
            borderStyle="etchedOut", 
            marginWidth=5, 
            marginHeight=5,
            labelVisible=True,
            height=60
        )
        
        # Pattern 1 dropdown
        self.pattern1_menu = cmds.optionMenu(
            changeCommand=self.on_pattern1_change,
            height=30
        )
        for pattern in self.NOISE_PATTERNS:
            cmds.menuItem(label=pattern)
        cmds.setParent('..')

        # Pattern 1 parameters container
        self.pattern1_params_container = cmds.columnLayout(
            adjustableColumn=True,
            rowSpacing=0
        )
        self.create_parameter_controls(
            self.pattern1_value, 
            self.pattern1_params_container, 
            self.pattern1_param_elements, 
            self.pattern1_param_values
        )
        cmds.setParent('..')
        
        # Pattern 2 selection
        cmds.frameLayout(
            label="Pattern 2", 
            collapsable=False, 
            borderStyle="etchedOut", 
            marginWidth=5, 
            marginHeight=5,
            labelVisible=True,
            height=60
        )
        
        # Pattern 2 dropdown
        self.pattern2_menu = cmds.optionMenu(
            changeCommand=self.on_pattern2_change,
            height=30
        )
        for pattern in self.NOISE_PATTERNS:
            cmds.menuItem(label=pattern)
        cmds.setParent('..')

        # Pattern 2 parameters container
        self.pattern2_params_container = cmds.columnLayout(
            adjustableColumn=True,
            rowSpacing=0
        )
        self.create_parameter_controls(
            self.pattern2_value, 
            self.pattern2_params_container, 
            self.pattern2_param_elements, 
            self.pattern2_param_values
        )
        cmds.setParent('..')
        
        # Mask Shape selection
        cmds.frameLayout(
            label="Mask Shape", 
            collapsable=False, 
            borderStyle="etchedOut", 
            marginWidth=5, 
            marginHeight=5,
            labelVisible=True,
            height=60
        )
        
        # Mask Shape dropdown
        self.mask_shape_menu = cmds.optionMenu(
            changeCommand=self.on_mask_shape_change,
            height=30
        )
        for shape in self.MASK_SHAPES:
            cmds.menuItem(label=shape)
        cmds.setParent('..')

        # Mask Upload Button
        cmds.button(
            label="Upload Custom Mask...",
            command=self.on_mask_file_upload,
            height=30,
            backgroundColor=[0.7, 0.7, 0.7]
        )
        
        # Blend factor frame
        cmds.frameLayout(
            label="Blend factor", 
            collapsable=False, 
            borderStyle="etchedOut", 
            marginWidth=5, 
            marginHeight=5,
            labelVisible=True,
            height=60
        )
        
        # Blend factor slider
        slider_row = cmds.rowLayout(
            numberOfColumns=3, 
            columnWidth3=(20, 280, 40), 
            adjustableColumn=2,
            columnAlign3=["left", "center", "right"]
        )
        
        cmds.text(label="0", width=20)
        self.blend_slider = cmds.floatSlider(
            min=0.0, 
            max=1.0, 
            value=self.blend_factor, 
            step=0.01,
            dragCommand=self.on_blend_change,
            changeCommand=self.on_blend_change,
            width=280,
            height=20
        )
        self.blend_value_text = cmds.text(label=f"{self.blend_factor:.2f}", width=40)
        
        cmds.setParent('..')  # Back to frameLayout
        cmds.setParent('..')  # Back to columnLayout
        
        # Add spacer before Generate button
        cmds.separator(height=20, style='none')
        
        # Generate button
        cmds.button(
            label="Generate", 
            command=self.on_generate,
            height=45,
            backgroundColor=[1.0, 0.5, 0.0]  # Orange color
        )
        
        # Add stretchy space at the bottom to push everything up
        cmds.text(label="", height=10)
        
        cmds.setParent('..')  # Back to main form
        
        # Create right column for images
        right_column = cmds.columnLayout(
            adjustableColumn=False, 
            rowSpacing=0,
            parent=main_form
        )
        
        # Top row images (Pattern 1 & 2 previews)
        cmds.rowLayout(
            numberOfColumns=2, 
            columnWidth2=(350, 350),
            adjustableColumn=2
        )
        
        # Pattern 1 preview
        cmds.columnLayout(adjustableColumn=False, width=367)
        cmds.text(label="Pattern 1 Preview", align="center", height=25)
        self.pattern1_image = cmds.image(
            width=350, 
            height=350, 
            backgroundColor=[0, 0, 0]
        )
        cmds.setParent('..')
        
        # Pattern 2 preview
        cmds.columnLayout(adjustableColumn=False, width=367)
        cmds.text(label="Pattern 2 Preview", align="center", height=25)
        self.pattern2_image = cmds.image(
            width=350, 
            height=350, 
            backgroundColor=[0, 0, 0]
        )
        cmds.setParent('..')
        
        cmds.setParent('..')  # Back to column layout
        
        # Bottom row images (Blend map & Output)
        cmds.rowLayout(
            numberOfColumns=2, 
            columnWidth2=(350, 350),
            adjustableColumn=2
        )
        
        # Blend map preview
        cmds.columnLayout(adjustableColumn=False, width=367)
        cmds.text(label="Blend map", align="center", height=25)
        self.blend_map_image = cmds.image(
            width=350, 
            height=350, 
            backgroundColor=[0, 0, 0]
        )
        cmds.setParent('..')
        
        # Output preview
        cmds.columnLayout(adjustableColumn=False, width=367)
        cmds.text(label="Output", align="center", height=25)
        self.output_image = cmds.image(
            width=350, 
            height=350, 
            backgroundColor=[0, 0, 0]
        )
        cmds.setParent('..')
        
        cmds.setParent('..')  # Back to column layout
        cmds.setParent('..')  # Back to main form
        
        # Arrange the two main columns in the form layout
        cmds.formLayout(
            main_form, 
            edit=True,
            attachForm=[
                (left_column, 'top', 0),
                (left_column, 'left', 0),
                (left_column, 'bottom', 0),
                (right_column, 'top', 0),
                (right_column, 'right', 0),
                (right_column, 'bottom', 0)
            ],
            attachControl=[
                (right_column, 'left', 0, left_column)
            ]
        )
        
        # Show the window
        cmds.showWindow(window)

    def resize_and_save(self, input_path, output_path, size=(350, 350)):
        im = Image.open(input_path)
        im = im.resize(size, Image.Resampling.LANCZOS)
        im.save(output_path)

    def update_single_noise_preview(self, pattern, pattern_image, params, size=(350, 350)):
        try:
            result = cmds.noisyHandyInference(
                pattern1 = pattern,
                pattern1Params = json.dumps(params),
                pattern2 = '',
                pattern2Params = json.dumps({}),
                maskPath = '',
                blendFactor = 0
            )
            cmds.image(pattern_image, edit=True, image=result)
            
        except Exception as e:
            cmds.warning(f"Error generating noise: {str(e)}")
            raise

    # Event handlers
    def on_pattern1_change(self, value):
        """Handler for pattern 1 selection change"""
        self.pattern1_value = value
        self.create_parameter_controls(
            value, 
            self.pattern1_params_container, 
            self.pattern1_param_elements, 
            self.pattern1_param_values,
        )
        self.update_single_noise_preview(value, self.pattern1_image, self.pattern1_param_values)
    
    def on_pattern2_change(self, value):
        """Handler for pattern 2 selection change"""
        self.pattern2_value = value
        self.create_parameter_controls(
            value, 
            self.pattern2_params_container, 
            self.pattern2_param_elements, 
            self.pattern2_param_values,
        )
        self.update_single_noise_preview(value, self.pattern2_image, self.pattern2_param_values)
    
    def on_parameter_change(self, pattern, parameter, value):
        """Handler for parameter slider changes"""
        if pattern == self.pattern1_value:
            param_values = self.pattern1_param_values
            param_elements = self.pattern1_param_elements
            image = self.pattern1_image
        else:
            param_values = self.pattern2_param_values
            param_elements = self.pattern2_param_elements
            image = self.pattern2_image
        
        param_values[parameter] = float(value)
        
        # Update the text display
        cmds.text(param_elements[parameter]['text'], edit=True, label=f"{value:.2f}")
        
        # Update the preview
        self.update_single_noise_preview(pattern, image, param_values)
    
    def on_mask_file_upload(self, *args):
        file_path = cmds.fileDialog2(fileMode=1, caption="Select a Mask Image", fileFilter="Image Files (*.png)", okCaption="Load")
        if file_path:
            selected_path = file_path[0]
            if selected_path.endswith('.png'):
                # Copy the file to MASK_DIR
                dest_name = os.path.basename(selected_path)
                dest_path = os.path.join(self.MASK_DIR, dest_name)
                try:
                    if not os.path.exists(dest_path):
                        cmds.sysFile(selected_path, copy=dest_path)
                    # Update mask list and dropdown
                    if dest_name[:-4] not in self.MASK_SHAPES:
                        self.MASK_SHAPES.append(dest_name[:-4])
                        cmds.menuItem(label=dest_name[:-4], parent=self.mask_shape_menu)
                    self.mask_shape_value = dest_name[:-4]
                    cmds.optionMenu(self.mask_shape_menu, edit=True, value=self.mask_shape_value)
                    self.on_mask_shape_change(self.mask_shape_value)
                except Exception as e:
                    cmds.warning("Failed to load mask: " + str(e))
            else:
                cmds.warning("Only PNG files are supported.")
    
    def on_mask_shape_change(self, value):
        """Handler for mask shape selection change"""
        self.mask_shape_value = value
        mask_path = os.path.join(self.MASK_DIR, self.mask_shape_value + '.png')

        if os.path.exists(mask_path):
            tmp_path = os.path.join(self.MASK_DIR, 'tmp_mask.png')
            self.resize_and_save(mask_path, tmp_path)

            # Update the UI image control with the new image
            cmds.image(self.blend_map_image, edit=True, image=tmp_path)
        
            # Store the path for future reference
            self.mask_preview_path = mask_path
        else:
            cmds.warning(f"Image file not found: {mask_path}")
    
    def on_blend_change(self, value):
        """Handler for blend factor slider change"""
        self.blend_factor = float(value)
        cmds.text(self.blend_value_text, edit=True, label=f"{self.blend_factor:.2f}")
 

    def on_generate(self, *args):
        """
        Handler for generating button click
        Will Generate an image, store that to {root_dir} + "/inference/temp_output/"
        """
        try:
            # Check if mask path is set and valid, use a default uniform mask if not
            mask_path = PATHS['mask_dir']
            if hasattr(self, 'mask_preview_path') and self.mask_preview_path and os.path.exists(self.mask_preview_path):
                mask_path = self.mask_preview_path
            else:
                # Use the uniform mask as a fallback
                mask_path = os.path.join(self.MASK_DIR, 'uniform.png')
                if not os.path.exists(mask_path):
                    # Create a blank white image if even the uniform mask doesn't exist
                    if PIL_AVAILABLE:
                        blank_mask = Image.new('RGB', (256, 256), color=(255, 255, 255))
                        blank_mask.save(mask_path)
                    else:
                        cmds.warning("Cannot create default mask - PIL not available")
            
            result = cmds.noisyHandyInference(
                pattern1=self.pattern1_value,
                pattern1Params=json.dumps(self.pattern1_param_values),
                pattern2=self.pattern2_value,
                pattern2Params=json.dumps(self.pattern2_param_values),
                maskPath=mask_path,
                blendFactor=self.blend_factor
            )

            cmds.image(self.output_image, edit=True, image=result)
            
            # Store the output path for creating a noise node
            self.output_preview_path = result
            
            # Display success message
            cmds.inViewMessage(
                assistMessage=f"Generated blended noise with {self.pattern1_value} and {self.pattern2_value}",
                position="topCenter",
                fade=True
            )
            
        except Exception as e:
            # Display error message
            error_msg = f"Error generating noise: {str(e)}"
            cmds.warning(error_msg)
            cmds.confirmDialog(
                title="Generation Error",
                message=error_msg,
                button=["OK"],
                defaultButton="OK"
            )

def create_menu():
    """
    Create a menu for Noisy Handy Plugin in Maya
    """
    # Clean up any existing menu first
    if cmds.menu('NoisyHandyMenu', exists=True):
        cmds.deleteUI('NoisyHandyMenu')

    # Create the menu
    main_menu = cmds.menu('NoisyHandyMenu', label='NoisyHandy', parent='MayaWindow', tearOff=True)
    
    # Menu items for main functions
    cmds.menuItem(label='Open Noise Generator', command=lambda x: show_noisy_handy_ui())
    cmds.menuItem(divider=True)
    
    # Examples submenu
    examples_menu = cmds.menuItem(label='Examples', subMenu=True)
    
    # Help/Info submenu
    help_menu = cmds.menuItem(label='Help', subMenu=True)
    
    cmds.menuItem(label='About NoisyHandy', command=lambda x: cmds.confirmDialog(
        title='About NoisyHandy',
        message='NoisyHandy Plugin\nVersion 1.0.1\n\nA Maya plugin for generating custom noise textures.',
        button='OK'
    ))

    cmds.menuItem(label='User Guide', command=show_user_guide)
    cmds.setParent('..', menu=True)  # Go back to main menu
    
    print("NoisyHandy menu created successfully")
    return main_menu


def show_user_guide(*args):
    """Show a user guide for NoisyHandy"""
    guide_text = """
    NoisyHandy - User Guide
    ======================
    
    1. Generating Noise:
       - Select noise patterns from dropdowns
       - Adjust parameters using sliders
       - Select a mask shape for blending
       - Click "Generate" to create the noise texture
    
    2. Creating Nodes:
       - After generating a noise texture, click "Create Noise Node"
       - The node can be connected to materials, displacement, etc.
       - Use "Create Custom Noise Node" for specialized setups
       
    3. Creating Terrain:
       - After generating a noise texture, use "Create Terrain from Noise" 
         from the NoisyHandy menu
       - This creates a terrain with the noise applied as displacement
       
    4. Object Deformation:
       - Use the "Deformable Object" example from the Examples menu
       - Or create a Custom Noise Node with "Enable for deformation" checked
       - Connect the node to a displacement deformer as shown in the instructions
       
    5. Animation:
       - Enable "animateNoise" on the node
       - Set animation speed and other parameters
       - The noise will change over time, animating textures and deformations
    """
    
    cmds.confirmDialog(
        title='NoisyHandy User Guide',
        message=guide_text,
        button='OK',
        defaultButton='OK'
    )

def update_slider_text(text_field, value):
    """
    Update text field with the slider value
    """
    # Format float values to 2 decimal places
    if isinstance(value, float):
        formatted_value = f"{value:.2f}"
    else:
        formatted_value = str(value)
    cmds.textField(text_field, edit=True, text=formatted_value)


def update_text_slider(slider, value, min_val, max_val, value_type):
    """
    Update slider with the text field value
    """
    try:
        # Parse and clamp the value
        parsed_value = value_type(value)
        clamped_value = max(min_val, min(max_val, parsed_value))
        
        # Set the slider value
        cmds.floatSlider(slider, edit=True, value=clamped_value)
        
        # If the value was clamped, update the text field
        if parsed_value != clamped_value:
            # Determine the corresponding text field name
            if slider == "frequencySlider":
                text_field = "frequencyValue"
            elif slider == "octavesSlider":
                text_field = "octavesValue"
            elif slider == "persistenceSlider":
                text_field = "persistenceValue"
            else:
                return
                
            if value_type == float:
                formatted_value = f"{clamped_value:.2f}"
            else:
                formatted_value = str(clamped_value)
            cmds.textField(text_field, edit=True, text=formatted_value)
    except ValueError:
        # If the entered value can't be parsed, reset to current slider value
        current_value = cmds.floatSlider(slider, query=True, value=True)
        
        # Determine the corresponding text field name
        if slider == "frequencySlider":
            text_field = "frequencyValue"
        elif slider == "octavesSlider":
            text_field = "octavesValue"
        elif slider == "persistenceSlider":
            text_field = "persistenceValue"
        else:
            return
            
        if value_type == float:
            formatted_value = f"{current_value:.2f}"
        else:
            formatted_value = str(int(current_value))
        cmds.textField(text_field, edit=True, text=formatted_value)

def cleanup_ui():
    """Remove all UI elements created by the plugin"""
    # Close the main window if it exists
    if cmds.window(NoisyHandyUI.WINDOW_NAME, exists=True):
        cmds.deleteUI(NoisyHandyUI.WINDOW_NAME)
        
    # Remove the menu if it exists
    if cmds.menu('NoisyHandyMenu', exists=True):
        cmds.deleteUI('NoisyHandyMenu')
        
    # Clean up any temporary files that might have been created
    mask_dir = PATHS['mask_dir']
    try:
        # Remove temporary files
        for tmp_file in os.listdir(mask_dir):
            if tmp_file.startswith('tmp_'):
                try:
                    os.remove(os.path.join(mask_dir, tmp_file))
                except:
                    pass
    except Exception as e:
        cmds.warning(f"Failed to clean up temporary files: {str(e)}")
    
    print("NoisyHandy UI elements have been removed")

# Function to create and show the UI
def show_noisy_handy_ui():
    ui = NoisyHandyUI()
    ui.create_ui()


# Only create the UI when this script is run directly (not when imported)
if __name__ == "__main__":
    # Show the UI directly when run as a script
    show_noisy_handy_ui()