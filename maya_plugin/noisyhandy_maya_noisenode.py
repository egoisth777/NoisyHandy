"""
NoisyHandy Node Generator module
Handles creation of Maya nodes including NoisyHandy nodes, terrain generation, and sample examples
"""
import maya.cmds as cmds
import maya.mel as mel
import os
import json


import maya.cmds as cmds
import maya.OpenMaya as OpenMaya
import maya.OpenMayaMPx as OpenMayaMPx 


# Node Definitionsa
NOISY_HANDY_NODE_TYPE = "noisyHandyNode"
NOISY_HANDY_NODE_ID = OpenMaya.MTypeId(0x00134567)  # Unique type ID for our node

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
        
        # Open the attribute editor on the new node - fixing the MEL command
        try:
            # First select the node to make it the active selection
            cmds.select(node_name)
            # Use simpler more reliable approach to show attribute editor
            mel.eval(f'openAEWindow;')
        except Exception as e:
            print(f"Warning: Could not focus attribute editor on new node: {str(e)}")
        
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
        
        # Make sure we have numpy available for texture operations
        try:
            import numpy as np
        except ImportError:
            print("Warning: NumPy not available. Some texture operations may not work.")

    @staticmethod
    def nodeCreator():
        """
        Create a new instance of the node
        """
        return OpenMayaMPx.asMPxPtr(NoisyHandyNode())
        
    @staticmethod
    def nodeInitializer():
        """
        Initialize the node attributes
        """
        # Create attributes
        numAttrFn = OpenMaya.MFnNumericAttribute()
        typedAttrFn = OpenMaya.MFnTypedAttribute()
        enumAttrFn = OpenMaya.MFnEnumAttribute()
        
        # Output color attribute (RGB)
        NoisyHandyNode.outColorAttr = numAttrFn.createColor("outColor", "oc")
        numAttrFn.setWritable(False)
        numAttrFn.setStorable(False)
        numAttrFn.setHidden(False)
        
        # Output alpha attribute (single float)
        NoisyHandyNode.outAlphaAttr = numAttrFn.create("outAlpha", "oa", 
                                                       OpenMaya.MFnNumericData.kFloat, 0.0)
        numAttrFn.setWritable(False)
        numAttrFn.setStorable(False)
        
        # Pattern attribute (string)
        NoisyHandyNode.patternAttr = typedAttrFn.create("pattern", "p", 
                                                      OpenMaya.MFnData.kString)
        typedAttrFn.setStorable(True)
        typedAttrFn.setKeyable(False)
        typedAttrFn.setConnectable(False)
        typedAttrFn.setDefault(OpenMaya.MFnStringData().create("perlin"))
        
        # Second pattern attribute (string)
        NoisyHandyNode.pattern2Attr = typedAttrFn.create("pattern2", "p2", 
                                                       OpenMaya.MFnData.kString)
        typedAttrFn.setStorable(True)
        typedAttrFn.setKeyable(False)
        typedAttrFn.setConnectable(False)
        typedAttrFn.setDefault(OpenMaya.MFnStringData().create(""))
        
        # Blend factor attribute (float)
        NoisyHandyNode.blendFactorAttr = numAttrFn.create("blendFactor", "bf", 
                                                      OpenMaya.MFnNumericData.kFloat, 0.5)
        numAttrFn.setMin(0.0)
        numAttrFn.setMax(1.0)
        numAttrFn.setStorable(True)
        numAttrFn.setKeyable(True)
        
        # Time attribute (float)
        NoisyHandyNode.timeAttr = numAttrFn.create("time", "tm", 
                                                 OpenMaya.MFnNumericData.kFloat, 0.0)
        numAttrFn.setStorable(True)
        numAttrFn.setKeyable(True)
        
        # Texture path attribute (string)
        NoisyHandyNode.texturePathAttr = typedAttrFn.create("texturePath", "tp", 
                                                         OpenMaya.MFnData.kString)
        typedAttrFn.setStorable(True)
        typedAttrFn.setKeyable(False)
        typedAttrFn.setConnectable(False)
        
        # UV Coordinate input
        NoisyHandyNode.uvCoordAttr = typedAttrFn.create("uvCoord", "uv", 
                                                     OpenMaya.MFnData.kFloatArray)
        typedAttrFn.setStorable(False)
        typedAttrFn.setKeyable(False)
        
        # Animation controls
        NoisyHandyNode.animateNoiseAttr = numAttrFn.create("animateNoise", "an", 
                                                       OpenMaya.MFnNumericData.kBoolean, False)
        numAttrFn.setStorable(True)
        numAttrFn.setKeyable(True)
        
        NoisyHandyNode.animationSpeedAttr = numAttrFn.create("animationSpeed", "as", 
                                                          OpenMaya.MFnNumericData.kFloat, 1.0)
        numAttrFn.setMin(0.01)
        numAttrFn.setMax(10.0)
        numAttrFn.setStorable(True)
        numAttrFn.setKeyable(True)
        
        # Resolution attribute
        NoisyHandyNode.resolutionAttr = numAttrFn.create("resolution", "res", 
                                                     OpenMaya.MFnNumericData.kInt, 256)
        numAttrFn.setMin(64)
        numAttrFn.setMax(4096)
        numAttrFn.setStorable(True)
        numAttrFn.setKeyable(False)
        
        # Noise parameters - to match what's in the API
        NoisyHandyNode.noiseFrequencyAttr = numAttrFn.create("noiseFrequency", "nf", 
                                                         OpenMaya.MFnNumericData.kFloat, 1.0)
        numAttrFn.setMin(0.01)
        numAttrFn.setMax(100.0)
        numAttrFn.setStorable(True)
        numAttrFn.setKeyable(True)
        
        NoisyHandyNode.noiseOctavesAttr = numAttrFn.create("noiseOctaves", "no", 
                                                       OpenMaya.MFnNumericData.kInt, 4)
        numAttrFn.setMin(1)
        numAttrFn.setMax(16)
        numAttrFn.setStorable(True)
        numAttrFn.setKeyable(True)
        
        NoisyHandyNode.noisePersistenceAttr = numAttrFn.create("noisePersistence", "np", 
                                                           OpenMaya.MFnNumericData.kFloat, 0.5)
        numAttrFn.setMin(0.0)
        numAttrFn.setMax(1.0)
        numAttrFn.setStorable(True)
        numAttrFn.setKeyable(True)
        
        # Add attributes to the node
        NoisyHandyNode.addAttribute(NoisyHandyNode.outColorAttr)
        NoisyHandyNode.addAttribute(NoisyHandyNode.outAlphaAttr)
        NoisyHandyNode.addAttribute(NoisyHandyNode.patternAttr)
        NoisyHandyNode.addAttribute(NoisyHandyNode.pattern2Attr)
        NoisyHandyNode.addAttribute(NoisyHandyNode.blendFactorAttr)
        NoisyHandyNode.addAttribute(NoisyHandyNode.timeAttr)
        NoisyHandyNode.addAttribute(NoisyHandyNode.texturePathAttr)
        NoisyHandyNode.addAttribute(NoisyHandyNode.uvCoordAttr)
        NoisyHandyNode.addAttribute(NoisyHandyNode.animateNoiseAttr)
        NoisyHandyNode.addAttribute(NoisyHandyNode.animationSpeedAttr)
        NoisyHandyNode.addAttribute(NoisyHandyNode.resolutionAttr)
        NoisyHandyNode.addAttribute(NoisyHandyNode.noiseFrequencyAttr)
        NoisyHandyNode.addAttribute(NoisyHandyNode.noiseOctavesAttr)
        NoisyHandyNode.addAttribute(NoisyHandyNode.noisePersistenceAttr)
        
        # Set up attribute dependencies - all inputs affect the output
        NoisyHandyNode.attributeAffects(NoisyHandyNode.patternAttr, NoisyHandyNode.outColorAttr)
        NoisyHandyNode.attributeAffects(NoisyHandyNode.pattern2Attr, NoisyHandyNode.outColorAttr)
        NoisyHandyNode.attributeAffects(NoisyHandyNode.blendFactorAttr, NoisyHandyNode.outColorAttr)
        NoisyHandyNode.attributeAffects(NoisyHandyNode.timeAttr, NoisyHandyNode.outColorAttr)
        NoisyHandyNode.attributeAffects(NoisyHandyNode.uvCoordAttr, NoisyHandyNode.outColorAttr)
        NoisyHandyNode.attributeAffects(NoisyHandyNode.animateNoiseAttr, NoisyHandyNode.outColorAttr)
        NoisyHandyNode.attributeAffects(NoisyHandyNode.animationSpeedAttr, NoisyHandyNode.outColorAttr)
        NoisyHandyNode.attributeAffects(NoisyHandyNode.noiseFrequencyAttr, NoisyHandyNode.outColorAttr)
        NoisyHandyNode.attributeAffects(NoisyHandyNode.noiseOctavesAttr, NoisyHandyNode.outColorAttr)
        NoisyHandyNode.attributeAffects(NoisyHandyNode.noisePersistenceAttr, NoisyHandyNode.outColorAttr)
        
        # Connect attributes to outAlpha too
        NoisyHandyNode.attributeAffects(NoisyHandyNode.patternAttr, NoisyHandyNode.outAlphaAttr)
        NoisyHandyNode.attributeAffects(NoisyHandyNode.pattern2Attr, NoisyHandyNode.outAlphaAttr)
        NoisyHandyNode.attributeAffects(NoisyHandyNode.blendFactorAttr, NoisyHandyNode.outAlphaAttr)
        NoisyHandyNode.attributeAffects(NoisyHandyNode.timeAttr, NoisyHandyNode.outAlphaAttr)
        NoisyHandyNode.attributeAffects(NoisyHandyNode.uvCoordAttr, NoisyHandyNode.outAlphaAttr)
        NoisyHandyNode.attributeAffects(NoisyHandyNode.animateNoiseAttr, NoisyHandyNode.outAlphaAttr)
        NoisyHandyNode.attributeAffects(NoisyHandyNode.animationSpeedAttr, NoisyHandyNode.outAlphaAttr)
        NoisyHandyNode.attributeAffects(NoisyHandyNode.noiseFrequencyAttr, NoisyHandyNode.outAlphaAttr)

    def compute(self, plug, dataBlock):
        """
        Compute the output values of the node based on the input values
        This is called by Maya when the node needs to be evaluated
        """
        if plug == NoisyHandyNode.outColorAttr or plug == NoisyHandyNode.outAlphaAttr:
            try:
                # Get input values from dataBlock
                patternHandle = dataBlock.inputValue(NoisyHandyNode.patternAttr)
                pattern = patternHandle.asString()
                
                pattern2Handle = dataBlock.inputValue(NoisyHandyNode.pattern2Attr)
                pattern2 = pattern2Handle.asString()
                
                blendHandle = dataBlock.inputValue(NoisyHandyNode.blendFactorAttr)
                blendFactor = blendHandle.asFloat()
                
                texturePathHandle = dataBlock.inputValue(NoisyHandyNode.texturePathAttr)
                texturePath = texturePathHandle.asString()
                
                timeHandle = dataBlock.inputValue(NoisyHandyNode.timeAttr)
                time = timeHandle.asFloat()
                
                animateHandle = dataBlock.inputValue(NoisyHandyNode.animateNoiseAttr)
                animate = animateHandle.asBool()
                
                speedHandle = dataBlock.inputValue(NoisyHandyNode.animationSpeedAttr)
                speed = speedHandle.asFloat()
                
                # Get UV coordinates if connected
                # Note: UV handling is simplified here, in a real node you'd want to handle this properly
                uvCoord = OpenMaya.MFloatArray()
                uvCoord.append(0.5)  # Default to center of UV space
                uvCoord.append(0.5)
                
                # Get node-specific noise parameters
                freqHandle = dataBlock.inputValue(NoisyHandyNode.noiseFrequencyAttr)
                frequency = freqHandle.asFloat()
                
                octavesHandle = dataBlock.inputValue(NoisyHandyNode.noiseOctavesAttr)
                octaves = octavesHandle.asInt()
                
                persistenceHandle = dataBlock.inputValue(NoisyHandyNode.noisePersistenceAttr)
                persistence = persistenceHandle.asFloat()
                
                # Store parameters for possible generation
                self.pattern1Value = pattern
                self.pattern2Value = pattern2
                self.pattern1Params = {
                    'frequency': frequency,
                    'octaves': octaves,
                    'persistence': persistence
                }
                
                # Check if we have a valid texture path
                validTexture = texturePath and os.path.exists(texturePath)
                
                # Output color handle
                outColorHandle = dataBlock.outputValue(NoisyHandyNode.outColorAttr)
                outColorObj = outColorHandle.asFloatVector()
                
                # Output alpha handle
                outAlphaHandle = dataBlock.outputValue(NoisyHandyNode.outAlphaAttr)
                
                if not validTexture:
                    # No texture - output a simple procedural noise as a fallback
                    # This is just a simple placeholder for when no texture is available
                    u = uvCoord[0]
                    v = uvCoord[1]
                    
                    # Very simple noise approximation for fallback
                    r = (u * frequency) % 1.0
                    g = (v * frequency) % 1.0
                    b = ((u + v) * frequency * 0.5) % 1.0
                    
                    if animate:
                        # Add time component for simple animation
                        animTime = time * speed * 0.1
                        r = (r + animTime) % 1.0
                        g = (g + animTime * 0.5) % 1.0
                        b = (b + animTime * 0.25) % 1.0
                    
                    outColorObj.x = r
                    outColorObj.y = g
                    outColorObj.z = b
                    alpha = (r + g + b) / 3.0  # Average for alpha
                else:
                    # We have a texture, so use it
                    # In a real implementation, you'd sample the texture based on UV coordinates
                    # Here, we're just using a solid color for simplicity
                    outColorObj.x = 1.0
                    outColorObj.y = 0.5
                    outColorObj.z = 0.25
                    alpha = 1.0
                
                outColorHandle.setClean()
                outAlphaHandle.setFloat(alpha)
                outAlphaHandle.setClean()
                
                return
                
            except Exception as e:
                OpenMaya.MGlobal.displayError(f"Error in NoisyHandy node compute: {str(e)}")
                # Set a default color on error
                outColorHandle = dataBlock.outputValue(NoisyHandyNode.outColorAttr)
                outColorObj = outColorHandle.asFloatVector()
                outColorObj.x = 1.0  # Red on error
                outColorObj.y = 0.0
                outColorObj.z = 0.0
                outColorHandle.setClean()
                
                outAlphaHandle = dataBlock.outputValue(NoisyHandyNode.outAlphaAttr)
                outAlphaHandle.setFloat(1.0)
                outAlphaHandle.setClean()
        
        return OpenMayaMPx.MPxNode.compute(self, plug, dataBlock)

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