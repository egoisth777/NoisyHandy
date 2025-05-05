"""
Noise Node creation module for NoisyHandy Maya plugin.
This module provides functionality for creating custom texture nodes based on generated noise patterns.
"""
import os
import random
import maya.cmds as cmds
import maya.OpenMaya as OpenMaya
import maya.OpenMayaMPx as OpenMayaMPx

from noisyhandy_config import PATHS

def create_custom_noise_node(texture_path):
    """
    Create a custom noise texture node in Maya with the specified texture path.
    
    Args:
        texture_path (str): Path to the generated texture image
        
    Returns:
        str: Name of the created file node
    """
    try:
        # Check if texture path exists
        if not os.path.exists(texture_path):
            cmds.warning(f"Texture path does not exist: {texture_path}")
            return None
            
        # Generate a random suffix for unique node names
        random_suffix = str(random.randint(1000, 9999))
            
        # Create a file node
        file_node = cmds.shadingNode('file', asTexture=True, name=f'noisyHandyTexture_{random_suffix}')
        
        # Set the file path on the file node
        cmds.setAttr(f"{file_node}.fileTextureName", texture_path, type="string")
        
        # Create placement node for UV coordinates
        place2d_node = cmds.shadingNode('place2dTexture', asUtility=True, name=f'noisyHandyPlace2d_{random_suffix}')
        
        # Connect place2d node to file node
        connections = [
            ("coverage", "coverage"),
            ("translateFrame", "translateFrame"),
            ("rotateFrame", "rotateFrame"),
            ("mirrorU", "mirrorU"),
            ("mirrorV", "mirrorV"),
            ("stagger", "stagger"),
            ("wrapU", "wrapU"),
            ("wrapV", "wrapV"),
            ("repeatUV", "repeatUV"),
            ("offset", "offset"),
            ("rotateUV", "rotateUV"),
            ("noiseUV", "noiseUV"),
            ("vertexUvOne", "vertexUvOne"),
            ("vertexUvTwo", "vertexUvTwo"),
            ("vertexUvThree", "vertexUvThree"),
            ("vertexCameraOne", "vertexCameraOne"),
            ("outUV", "uvCoord"),
            ("outUvFilterSize", "uvFilterSize")
        ]
        
        for src, dst in connections:
            cmds.connectAttr(f"{place2d_node}.{src}", f"{file_node}.{dst}")
        
        # Create a shading group for the file node
        sg_name = f"{file_node}_SG"
        sg = cmds.sets(renderable=True, noSurfaceShader=True, empty=True, name=sg_name)
        
        # Print success message
        cmds.inViewMessage(
            assistMessage=f"Created custom noise texture node: {file_node}",
            position="topCenter",
            fade=True
        )
        
        # Open the Hypershade editor to show the created node
        try:
            cmds.HypershadeWindow()
            cmds.hyperShadePanel(edit=True, setNodeEditorNodeSelected=file_node)
        except Exception as e:
            cmds.warning(f"Could not open Hypershade window: {str(e)}")
        
        return file_node
        
    except Exception as e:
        error_msg = f"Error creating custom noise node: {str(e)}"
        cmds.warning(error_msg)
        cmds.confirmDialog(
            title="Node Creation Error",
            message=error_msg,
            button=["OK"],
            defaultButton="OK"
        )
        return None 