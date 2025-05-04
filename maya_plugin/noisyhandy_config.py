"""
Shared configuration for NoisyHandy Maya plugin modules.
This resolves circular dependencies between modules.
"""
import os
import sys
import maya.cmds as cmds

# Plugin Information
PLUGIN_NAME = "NoisyHandyPlugin"
PLUGIN_VERSION = "1.0.1"

# Centralized path management
def config_paths():
    """
    Centralized function to manage all paths needed by the NoisyHandy plugin.
    Sets up required paths and returns a dictionary with all path configurations.
    """
    paths = {}
    
    # Get the plugin path - use __file__ if available, otherwise use Maya's API
    plugin_path = None
    if '__file__' in globals():
        # When running as a script
        plugin_path = os.path.join(os.path.dirname(__file__), "noisyhandy_maya_plugin.py")
    else:
        # When loaded as a plugin
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
PATHS = config_paths()