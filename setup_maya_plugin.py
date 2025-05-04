"""
Setup script for NoisyHandy Maya plugin dependencies
This script installs the required Python packages for the NoisyHandy Maya plugin
"""

import os
import sys
import subprocess
import site
import platform

def find_maya_python():
    """Find Maya's Python executable (mayapy.exe)"""
    # Start with environment variable if set
    maya_python = os.environ.get('MAYA_PYTHON', '')
    
    if maya_python and os.path.exists(maya_python):
        return maya_python
    
    # Try to find mayapy.exe based on common installation paths
    if platform.system() == 'Windows':
        # Common Maya installation paths on Windows
        maya_versions = ['2025', '2024', '2023', '2022']
        possible_paths = [
            os.path.join(os.environ.get('MAYA_LOCATION', ''), 'bin', 'mayapy.exe'),
            *[os.path.join(r'C:\Program Files\Autodesk\Maya{}'.format(ver), 'bin', 'mayapy.exe') for ver in maya_versions]
        ]
        
        for path in possible_paths:
            if os.path.exists(path):
                print(f"Found Maya Python at: {path}")
                return path
                
    elif platform.system() == 'Darwin':  # macOS
        # Common Maya installation paths on macOS
        possible_paths = [
            '/Applications/Autodesk/maya2025/Maya.app/Contents/bin/mayapy',
            '/Applications/Autodesk/maya2024/Maya.app/Contents/bin/mayapy',
            '/Applications/Autodesk/maya2023/Maya.app/Contents/bin/mayapy'
        ]
        
        for path in possible_paths:
            if os.path.exists(path):
                return path
                
    elif platform.system() == 'Linux':
        # Common Maya installation paths on Linux
        possible_paths = [
            '/usr/autodesk/maya2025/bin/mayapy',
            '/usr/autodesk/maya2024/bin/mayapy',
            '/usr/autodesk/maya2023/bin/mayapy'
        ]
        
        for path in possible_paths:
            if os.path.exists(path):
                return path
    
    # Fallback to system Python if Maya Python not found
    print("⚠️ Could not find Maya Python (mayapy.exe). Using system Python instead.")
    return sys.executable

def ensure_package_installed(package_name, maya_python):
    """Try to import a package, install it if not available using Maya's Python"""
    try:
        # Try to check if the package is installed in Maya's Python
        check_cmd = [maya_python, "-c", f"import {package_name}; print('Package is installed')"]
        result = subprocess.run(check_cmd, capture_output=True, text=True)
        
        if "Package is installed" in result.stdout:
            print(f"✓ {package_name} is already installed in Maya's Python")
            return True
        else:
            print(f"× {package_name} not found in Maya's Python. Installing...")
    except Exception as e:
        print(f"× Error checking for {package_name}: {str(e)}")
        print(f"× Will attempt to install {package_name}...")
    
    # Install the package using Maya's pip
    try:
        install_cmd = [maya_python, "-m", "pip", "install", package_name]
        print(f"Running: {' '.join(install_cmd)}")
        subprocess.check_call(install_cmd)
        print(f"✓ Successfully installed {package_name} for Maya's Python")
        return True
    except Exception as e:
        print(f"× Failed to install {package_name} for Maya's Python: {str(e)}")
        return False

def main():
    """Main function to set up dependencies"""
    print("Setting up dependencies for NoisyHandy Maya plugin...")
    
    # Get Maya's Python executable path
    maya_python = find_maya_python()
    print(f"Using Maya Python at: {maya_python}")
    
    # List of required packages
    required_packages = [
        "numpy",
        "pillow",  # For PIL
        "torch",   # Note: Installing PyTorch via pip might not be ideal for CUDA compatibility
    ]
    
    # Add site-packages to path to ensure installations are available
    for site_path in site.getsitepackages():
        if site_path not in sys.path:
            sys.path.append(site_path)
            print(f"Added site-packages path: {site_path}")
    
    # Install each required package using Maya's Python
    all_successful = True
    for package in required_packages:
        if not ensure_package_installed(package, maya_python):
            all_successful = False
    
    # Print summary
    if all_successful:
        print("\nSetup completed successfully! All required packages are installed for Maya's Python.")
        print("You can now load the NoisyHandy Maya plugin.")
    else:
        print("\nSetup completed with some issues. Some packages may need to be installed manually.")
        print(f"To manually install packages for Maya's Python, run:")
        print(f"{maya_python} -m pip install <package_name>")
        print("\nFor PyTorch, if needed, visit: https://pytorch.org/get-started/locally/")
        print("and follow the instructions for your specific CUDA version.")
    
    return all_successful

if __name__ == "__main__":
    main()