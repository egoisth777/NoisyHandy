"""
NoisyHandy Node Generator module
Handles creation of Maya nodes including NoisyHandy nodes, terrain generation, and sample examples
"""
import maya.cmds as cmds
import maya.mel as mel
import os
import json

# Get paths from the plugin itself
from noisyhandy_maya_plugin import PATHS


def create_noise_node(pattern1, pattern2, blend_factor, texture_path, pattern1_params={}, pattern2_params={}):
    """
    Create a NoisyHandy node using the parameters from the UI
    
    Args:
        pattern1 (str): Primary noise pattern
        pattern2 (str): Secondary noise pattern (optional)
        blend_factor (float): Blend factor between patterns
        texture_path (str): Path to the generated texture
        pattern1_params (dict): Parameters for pattern 1
        pattern2_params (dict): Parameters for pattern 2
    
    Returns:
        str: Name of the created node
    """
    try:
        # Check if texture path is valid
        if not texture_path or not os.path.exists(texture_path):
            cmds.warning("Please generate a noise texture first.")
            return None
        
        # Create a NoisyHandy node using our custom command
        node_name = cmds.createNoisyHandyNode(
            pattern=pattern1,
            pattern2=pattern2,
            blendFactor=blend_factor,
            texturePath=texture_path
        )
        
        # Store parameter values on the node
        if pattern1_params:
            # Store parameter values as node attributes
            for param, value in pattern1_params.items():
                # Create dynamic attribute if it doesn't exist
                attr_name = f"p1_{param}"
                if not cmds.attributeQuery(attr_name, node=node_name, exists=True):
                    cmds.addAttr(node_name, longName=attr_name, attributeType='float', min=0.0, max=1.0, defaultValue=value)
                    cmds.setAttr(f"{node_name}.{attr_name}", keyable=True)
                else:
                    cmds.setAttr(f"{node_name}.{attr_name}", value)
        
        if pattern2_params:
            # Store parameter values as node attributes
            for param, value in pattern2_params.items():
                # Create dynamic attribute if it doesn't exist
                attr_name = f"p2_{param}"
                if not cmds.attributeQuery(attr_name, node=node_name, exists=True):
                    cmds.addAttr(node_name, longName=attr_name, attributeType='float', min=0.0, max=1.0, defaultValue=value)
                    cmds.setAttr(f"{node_name}.{attr_name}", keyable=True)
                else:
                    cmds.setAttr(f"{node_name}.{attr_name}", value)
        
        # Connect time node to the noise node's time attribute for animation
        time_node = cmds.ls(type="time")
        if time_node:
            time_node = time_node[0]
            cmds.connectAttr(f"{time_node}.outTime", f"{node_name}.time")
        
        # Create a place2dTexture node to provide UV coordinates
        place2d_node = cmds.shadingNode("place2dTexture", asUtility=True, name=f"{node_name}_place2d")
        
        # Connect place2dTexture to NoisyHandy node
        cmds.connectAttr(f"{place2d_node}.outUV", f"{node_name}.uvCoord")
        
        # Select the node in the viewport
        cmds.select(node_name, replace=True)
        
        # Display success message
        cmds.inViewMessage(
            assistMessage=f"Created NoisyHandy node: {node_name}",
            position="topCenter",
            fade=True
        )
        
        # Open the attribute editor on the new node
        mel.eval(f'openAEWindow;')
        mel.eval(f'showTabLayout "{node_name}";')
        
        # Show how to use it in the script editor
        cmds.scriptEditorInfo(
            edit=True,
            suppressInfo=False,
            suppressWarnings=False,
            suppressErrors=False,
        )
        
        # Print useful examples in the script editor
        print("\n# ======== NoisyHandy Node Usage Examples ========")
        print("\n# 1. Connect to a Material:")
        print(f"# Connect to a bump3d node for normal mapping:")
        print(f"bump3d_node = cmds.shadingNode('bump3d', asUtility=True)")
        print(f"cmds.connectAttr('{node_name}.outColor', f'{{bump3d_node}}.bumpValue')")
        
        print("\n# 2. Connect to a displacement shader:")
        print(f"# cmds.connectAttr('{node_name}.outColor', 'YOUR_SHADER.displacementShader')")
        
        print("\n# 3. Terrain Generation Example:")
        print(f"# Create a plane for the terrain")
        print(f"terrain = cmds.polyPlane(width=10, height=10, subdivisionsX=100, subdivisionsY=100)[0]")
        print(f"# Create displacement node")
        print(f"disp_node = cmds.shadingNode('displacementShader', asShader=True)")
        print(f"# Connect noise to displacement")
        print(f"cmds.connectAttr('{node_name}.outColor', f'{{disp_node}}.displacement')")
        print(f"# Assign displacement to terrain")
        print(f"cmds.select(terrain)")
        print(f"cmds.sets(e=True, forceElement=f'{{disp_node}}SG')")
        
        print("\n# 4. Animation Control:")
        print(f"# The node is already connected to Maya's time. To animate parameters:")
        print(f"cmds.setKeyframe('{node_name}.noiseFrequency', time=1, value=0.5)")
        print(f"cmds.setKeyframe('{node_name}.noiseFrequency', time=24, value=2.0)")
        print(f"# Enable animation on the node:")
        print(f"cmds.setAttr('{node_name}.animateNoise', True)")
        
        print("\n# ===============================================")
        
        return node_name
        
    except Exception as e:
        error_msg = f"Error creating NoisyHandy node: {str(e)}"
        cmds.warning(error_msg)
        cmds.confirmDialog(
            title="Node Creation Error",
            message=error_msg,
            button=["OK"],
            defaultButton="OK"
        )
        return None


def create_terrain_from_noise(output_preview_path, pattern1, pattern2, blend_factor, pattern1_params={}, pattern2_params={}):
    """
    Creates a terrain object using the generated noise as displacement
    
    Args:
        output_preview_path (str): Path to the generated noise texture
        pattern1 (str): Primary noise pattern
        pattern2 (str): Secondary noise pattern (optional)
        blend_factor (float): Blend factor between patterns
        pattern1_params (dict): Parameters for pattern 1
        pattern2_params (dict): Parameters for pattern 2
    
    Returns:
        str: Name of the created terrain
    """
    try:
        # Check if we have a generated output
        if not output_preview_path or not os.path.exists(output_preview_path):
            cmds.warning("Please generate a noise texture first.")
            return None
            
        # First create the noise node
        noise_node = create_noise_node(pattern1, pattern2, blend_factor, output_preview_path, 
                                      pattern1_params, pattern2_params)
        if not noise_node:
            return None
            
        # Create a plane for the terrain
        terrain_name = cmds.polyPlane(
            name="noisyHandyTerrain",
            width=10, 
            height=10, 
            subdivisionsX=100, 
            subdivisionsY=100
        )[0]
        
        # Create a shading group for the terrain
        shader = cmds.shadingNode("lambert", asShader=True, name=f"{terrain_name}_material")
        sg = cmds.sets(renderable=True, noSurfaceShader=True, empty=True, name=f"{shader}SG")
        cmds.connectAttr(f"{shader}.outColor", f"{sg}.surfaceShader", force=True)
        
        # Create bump node
        bump = cmds.shadingNode("bump3d", asUtility=True, name=f"{terrain_name}_bump")
        cmds.setAttr(f"{bump}.bumpDepth", 0.2)
        
        # Connect noise to bump
        cmds.connectAttr(f"{noise_node}.outColor", f"{bump}.bumpValue")
        
        # Connect bump to shader
        cmds.connectAttr(f"{bump}.outNormal", f"{shader}.normalCamera")
        
        # Create displacement node for the actual terrain displacement
        disp_node = cmds.shadingNode("displacementShader", asShader=True, name=f"{terrain_name}_displacement")
        disp_sg = cmds.sets(renderable=True, noSurfaceShader=True, empty=True, name=f"{disp_node}SG")
        cmds.connectAttr(f"{disp_node}.displacement", f"{disp_sg}.displacementShader", force=True)
        
        # Connect noise to displacement
        cmds.connectAttr(f"{noise_node}.outColor", f"{disp_node}.displacement")
        
        # Set displacement attributes for better effect
        cmds.setAttr(f"{disp_node}.scale", 0.5)
        
        # Assign shader and displacement to terrain
        cmds.select(terrain_name)
        cmds.sets(e=True, forceElement=sg)
        cmds.sets(e=True, forceElement=disp_sg)
        
        # Center terrain in the scene
        cmds.xform(terrain_name, centerPivots=True)
        
        # Create a directional light if none exists
        lights = cmds.ls(type="directionalLight")
        if not lights:
            light = cmds.directionalLight(name="noisyHandy_key_light")
            # Position light appropriately
            cmds.xform(light, rotation=(-45, 45, 0))
            cmds.setAttr(f"{light}.intensity", 1.5)
        
        # Select the terrain
        cmds.select(terrain_name)
        
        # Display success message
        cmds.inViewMessage(
            assistMessage=f"Created terrain {terrain_name} with noise {noise_node}",
            position="topCenter",
            fade=True
        )
        
        # Return the terrain name
        return terrain_name
        
    except Exception as e:
        error_msg = f"Error creating terrain: {str(e)}"
        cmds.warning(error_msg)
        cmds.confirmDialog(
            title="Terrain Creation Error",
            message=error_msg,
            button=["OK"],
            defaultButton="OK"
        )
        return None


def create_perlin_example(*args):
    """Create a simple perlin noise node"""
    # Create the node
    node_name = cmds.createNoisyHandyNode(
        pattern="perlin",
        pattern2="",
        blendFactor=0.0,
        texturePath=""
    )
    
    # Set up some default parameters
    cmds.setAttr(f"{node_name}.noiseFrequency", 2.0)
    cmds.setAttr(f"{node_name}.noiseOctaves", 4)
    cmds.setAttr(f"{node_name}.noisePersistence", 0.5)
    
    # Create a place2dTexture node to provide UV coordinates
    place2d_node = cmds.shadingNode("place2dTexture", asUtility=True, name=f"{node_name}_place2d")
    
    # Connect place2dTexture to NoisyHandy node
    cmds.connectAttr(f"{place2d_node}.outUV", f"{node_name}.uvCoord")
    
    # Create a simple material to show the noise
    lambert = cmds.shadingNode("lambert", asShader=True, name=f"{node_name}_material")
    
    # Connect noise to material color
    cmds.connectAttr(f"{node_name}.outColor", f"{lambert}.color")
    
    # Select the node
    cmds.select(node_name)
    
    # Display success message
    cmds.inViewMessage(
        assistMessage=f"Created Perlin noise example node: {node_name}",
        position="topCenter",
        fade=True
    )
    
    return node_name


def create_animated_noise_example(*args):
    """Create an animated noise example"""
    # Create the node
    node_name = cmds.createNoisyHandyNode(
        pattern="galvanic",
        pattern2="",
        blendFactor=0.0,
        texturePath=""
    )
    
    # Set up animation parameters
    cmds.setAttr(f"{node_name}.animateNoise", True)
    cmds.setAttr(f"{node_name}.animationSpeed", 0.5)
    cmds.setAttr(f"{node_name}.noiseFrequency", 1.5)
    
    # Create a place2dTexture node to provide UV coordinates
    place2d_node = cmds.shadingNode("place2dTexture", asUtility=True, name=f"{node_name}_place2d")
    
    # Connect place2dTexture to NoisyHandy node
    cmds.connectAttr(f"{place2d_node}.outUV", f"{node_name}.uvCoord")
    
    # Connect time node
    time_node = cmds.ls(type="time")
    if time_node:
        time_node = time_node[0]
        cmds.connectAttr(f"{time_node}.outTime", f"{node_name}.time")
    
    # Create a material to show the animated noise
    blinn = cmds.shadingNode("blinn", asShader=True, name=f"{node_name}_material")
    
    # Connect noise to material
    cmds.connectAttr(f"{node_name}.outColor", f"{blinn}.color")
    
    # Select the node
    cmds.select(node_name)
    
    # Display success message
    cmds.inViewMessage(
        assistMessage=f"Created animated noise example: {node_name}. Press Play to see animation.",
        position="topCenter",
        fade=True
    )
    
    return node_name


def create_terrain_example(*args):
    """Create a simple terrain example with noise"""
    # Create the node
    node_name = cmds.createNoisyHandyNode(
        pattern="cells1",
        pattern2="perlin",
        blendFactor=0.7,
        texturePath=""
    )
    
    # Set up noise parameters
    cmds.setAttr(f"{node_name}.noiseFrequency", 1.2)
    cmds.setAttr(f"{node_name}.noiseOctaves", 3)
    
    # Create a place2dTexture node to provide UV coordinates
    place2d_node = cmds.shadingNode("place2dTexture", asUtility=True, name=f"{node_name}_place2d")
    
    # Connect place2dTexture to NoisyHandy node
    cmds.connectAttr(f"{place2d_node}.outUV", f"{node_name}.uvCoord")
    
    # Create a plane for the terrain
    terrain_name = cmds.polyPlane(
        name="noisyHandyExampleTerrain",
        width=10, 
        height=10, 
        subdivisionsX=100, 
        subdivisionsY=100
    )[0]
    
    # Create a standard surface material for the terrain
    terrain_mat = cmds.shadingNode("lambert", asShader=True, name=f"{terrain_name}_material")
    terrain_sg = cmds.sets(renderable=True, noSurfaceShader=True, empty=True, name=f"{terrain_mat}SG")
    cmds.connectAttr(f"{terrain_mat}.outColor", f"{terrain_sg}.surfaceShader", force=True)
    
    # Add some color to the material
    cmds.setAttr(f"{terrain_mat}.color", 0.4, 0.5, 0.2)
    
    # Create bump node
    bump = cmds.shadingNode("bump3d", asUtility=True, name=f"{terrain_name}_bump")
    cmds.setAttr(f"{bump}.bumpDepth", 0.2)
    
    # Connect noise to bump
    cmds.connectAttr(f"{node_name}.outColor", f"{bump}.bumpValue")
    
    # Connect bump to material
    cmds.connectAttr(f"{bump}.outNormal", f"{terrain_mat}.normalCamera")
    
    # Create displacement node
    disp_node = cmds.shadingNode("displacementShader", asShader=True, name=f"{terrain_name}_displacement")
    disp_sg = cmds.sets(renderable=True, noSurfaceShader=True, empty=True, name=f"{disp_node}SG")
    cmds.connectAttr(f"{disp_node}.displacement", f"{disp_sg}.displacementShader", force=True)
    
    # Connect noise to displacement
    cmds.connectAttr(f"{node_name}.outColor", f"{disp_node}.displacement")
    
    # Set displacement attributes
    cmds.setAttr(f"{disp_node}.scale", 0.5)
    
    # Assign material and displacement to terrain
    cmds.select(terrain_name)
    cmds.sets(e=True, forceElement=terrain_sg)
    cmds.sets(e=True, forceElement=disp_sg)
    
    # Center terrain in scene
    cmds.xform(terrain_name, centerPivots=True)
    
    # Create a directional light if none exists
    lights = cmds.ls(type="directionalLight")
    if not lights:
        light = cmds.directionalLight(name="noisyHandy_example_light")
        # Position light appropriately
        cmds.xform(light, rotation=(-45, 45, 0))
        cmds.setAttr(f"{light}.intensity", 1.5)
    
    # Select the terrain
    cmds.select(terrain_name)
    
    # Display success message
    cmds.inViewMessage(
        assistMessage=f"Created terrain example with noise: {terrain_name}",
        position="topCenter",
        fade=True
    )
    
    return terrain_name