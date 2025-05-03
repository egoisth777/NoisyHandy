import maya.cmds as cmds
import maya.mel as mel
import os
import sys
import json
import tempfile
from PIL import Image

plugin_path = cmds.pluginInfo("noisyhandy_maya_plugin.py", query=True, path=True)
plugin_dir = os.path.dirname(plugin_path)
root_dir = os.path.dirname(plugin_dir)
if root_dir not in sys.path:
    sys.path.append(root_dir)
from config.noise_config import noise_aliases, ntype_to_params_map

class NoisyHandyUI:
    """UI for the NoisyHandy Maya plugin"""
    
    WINDOW_NAME = "NoisyHandyUI"
    WINDOW_TITLE = "NoisyHandy"
    
    NOISE_PATTERNS = ["damas", "galvanic", "cells1", "cells4", "perlin", "gaussian", "voro", "liquid", "fibers", "micro", "rust"]
    MASK_DIR = "D:/Projects/Upenn_CIS_6600/NoisyHandy/LYY/NoisyHandy/inference/masks"
    MASK_SHAPES = [os.path.splitext(f)[0] for f in os.listdir(MASK_DIR) if f.endswith('.png') and not f.startswith('tmp')]

    print(NOISE_PATTERNS)
    print(MASK_SHAPES)

    NOISE_PARAMETERS = {}

    # Paths for preview images (to be populated)
    PREVIEW_IMAGES_PATH = tempfile.gettempdir()
    
    def __init__(self):
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
        print(self.NOISE_PARAMETERS)
    
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
        print(params)
        try:
            print("into single noise preview")
            result = cmds.noisyHandyInference(
                pattern1 = pattern,
                pattern1Params = json.dumps(params),
                pattern2 = '',
                pattern2Params = json.dumps({}),
                maskPath = '',
                blendFactor = 0
            )
            print("get result from model")
            print(result)

            cmds.image(pattern_image, edit=True, image=result)

        except Exception as e:
            cmds.warning( f"Error generating noise: {str(e)}")
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
            tmp_path = 'D:/Projects/Upenn_CIS_6600/NoisyHandy/LYY/NoisyHandy/inference/masks/tmp_mask.png'
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
        """Handler for generate button click"""
        # Here is where you would call the NoisyHandy plugin command
        try:
            # Call the plugin command with the selected parameters
            print("into blending noise preview")
            result = cmds.noisyHandyInference(
                pattern1=self.pattern1_value,
                pattern1Params = json.dumps(self.pattern1_param_values),
                pattern2=self.pattern2_value,
                pattern2Params = json.dumps(self.pattern2_param_values),
                maskPath=self.mask_preview_path,
                blendFactor=self.blend_factor
            )
            print("get result from model")
            print(result)

            cmds.image(self.output_image, edit=True, image=result)
            
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
    """Create a menu in Maya with NoisyHandy options"""
    
    # Check if the menu already exists and delete it
    if cmds.menu('NoisyHandyMenu', exists=True):
        cmds.deleteUI('NoisyHandyMenu')
    
    # Get the main Maya menu bar
    gMainWindow = mel.eval('$temp=$gMainWindow')
    
    # Create a new menu on the menu bar
    noisy_menu = cmds.menu('NoisyHandyMenu', label='NoisyHandy', parent=gMainWindow, tearOff=True)
    
    # Add menu items
    cmds.menuItem(label='Generate Texture', command=lambda x: show_noisy_handy_ui())
    
    # Optional: Add a separator and more menu items if needed
    cmds.menuItem(divider=True)
    cmds.menuItem(label='About', command=lambda x: cmds.confirmDialog(
        title='About NoisyHandy',
        message='NoisyHandy v1.0.0\nProcedural Generator of Spatially-Varying Noise Patterns',
        button=['OK'],
        defaultButton='OK'
    ))
    
    return noisy_menu

# Function to create and show the UI
def show_noisy_handy_ui():
    ui = NoisyHandyUI()
    ui.create_ui()

# Create the menu when this script is imported
if __name__ == "__main__":
    # Show the UI directly when run as a script
    show_noisy_handy_ui()
else:
    # Just create the menu when imported
    create_menu()