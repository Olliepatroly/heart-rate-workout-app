"""
OpenANT Wrapper Module

This module provides a wrapper for the OpenANT library, ensuring it can be
imported even if the actual OpenANT library is in a different Python environment.
It dynamically locates and imports OpenANT at runtime.
"""

import os
import sys
import platform
import importlib.util

# Track if we've successfully imported OpenANT
OPENANT_AVAILABLE = False
Node = None
ANTPLUS_NETWORK_KEY = None
Driver = None

def find_and_import_openant():
    """
    Attempt to find and import OpenANT from various possible locations.
    Returns True if successful, False otherwise.
    """
    global OPENANT_AVAILABLE, Node, ANTPLUS_NETWORK_KEY, Driver
    
    # First try the normal import
    try:
        import openant
        from openant.easy.node import Node
        from openant.devices import ANTPLUS_NETWORK_KEY
        from openant.base.ant import Driver
        
        OPENANT_AVAILABLE = True
        print(f"Successfully imported OpenANT {getattr(openant, '__version__', 'unknown')}")
        return True
    except ImportError:
        pass
    
    # If that fails, try to find OpenANT in common locations
    potential_paths = []
    
    # System-specific paths
    system = platform.system()
    python_version = f"{sys.version_info.major}.{sys.version_info.minor}"
    
    if system == "Darwin":  # macOS
        potential_paths.extend([
            f"/Library/Frameworks/Python.framework/Versions/{python_version}/lib/python{python_version}/site-packages",
            os.path.expanduser(f"~/Library/Python/{python_version}/lib/python{python_version}/site-packages"),
        ])
    elif system == "Linux":
        potential_paths.extend([
            f"/usr/lib/python{python_version}/site-packages",
            f"/usr/local/lib/python{python_version}/site-packages",
            os.path.expanduser(f"~/.local/lib/python{python_version}/site-packages"),
        ])
    elif system == "Windows":
        # Windows paths with Python version
        program_files = os.environ.get("PROGRAMFILES", "C:\\Program Files")
        python_base = os.path.join(program_files, f"Python{python_version.replace('.', '')}")
        potential_paths.extend([
            os.path.join(python_base, "Lib", "site-packages"),
            os.path.join(os.environ.get("APPDATA", ""), "Python", "Python{}{}".format(*python_version.split('.')), "site-packages")
        ])
    
    # Look for openant in all the potential paths
    for path in potential_paths:
        openant_path = os.path.join(path, "openant")
        if os.path.exists(openant_path) and os.path.isdir(openant_path):
            # Found openant directory, try to import it
            if path not in sys.path:
                sys.path.insert(0, path)
            
            try:
                import openant
                from openant.easy.node import Node
                from openant.devices import ANTPLUS_NETWORK_KEY
                from openant.base.ant import Driver
                
                OPENANT_AVAILABLE = True
                print(f"Found and imported OpenANT from {path}")
                print(f"Version: {getattr(openant, '__version__', 'unknown')}")
                return True
            except ImportError as e:
                print(f"Found OpenANT at {path} but failed to import: {e}")
                sys.path.remove(path)  # Remove it from path to avoid conflicts
    
    print("Could not find OpenANT in any standard location.")
    return False

# Try to import OpenANT at module load time
find_and_import_openant()

def is_available():
    """Check if OpenANT is available"""
    return OPENANT_AVAILABLE

def get_node():
    """Get the Node class"""
    if not OPENANT_AVAILABLE:
        raise ImportError("OpenANT is not available")
    return Node

def get_network_key():
    """Get the ANTPLUS_NETWORK_KEY"""
    if not OPENANT_AVAILABLE:
        raise ImportError("OpenANT is not available")
    return ANTPLUS_NETWORK_KEY

def get_driver():
    """Get the Driver class"""
    if not OPENANT_AVAILABLE:
        raise ImportError("OpenANT is not available")
    return Driver