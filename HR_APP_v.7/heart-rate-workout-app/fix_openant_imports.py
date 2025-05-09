#!/usr/bin/env python3
"""
OpenANT Import Path Fixer

This script modifies the ant_manager_custom.py file to use absolute imports,
ensuring OpenANT can be found even in different Python environments.
"""

import os
import sys
import re
import importlib
import subprocess

def find_openant_path():
    """Find the actual path to OpenANT installation"""
    print("Searching for OpenANT installation...")
    
    # First try importing openant to see if it's available
    try:
        import openant
        openant_path = os.path.dirname(os.path.abspath(openant.__file__))
        print(f"Found OpenANT at: {openant_path}")
        print(f"Version: {getattr(openant, '__version__', 'unknown')}")
        return openant_path
    except ImportError:
        print("OpenANT not found in current Python environment.")
        
        # Try using pip to find the install location
        try:
            result = subprocess.run(
                [sys.executable, "-m", "pip", "show", "openant"],
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                for line in result.stdout.split("\n"):
                    if line.startswith("Location:"):
                        pip_location = line.split(":", 1)[1].strip()
                        openant_path = os.path.join(pip_location, "openant")
                        if os.path.exists(openant_path):
                            print(f"Found OpenANT via pip at: {openant_path}")
                            return openant_path
            
            print("OpenANT not found via pip.")
        except Exception as e:
            print(f"Error checking pip for OpenANT: {e}")
    
    return None

def update_ant_manager(openant_path=None):
    """Update the ANT+ manager file to use absolute imports"""
    manager_file = "ant_manager_custom.py"
    
    if not os.path.exists(manager_file):
        print(f"Error: {manager_file} not found in current directory.")
        return False
    
    print(f"Updating {manager_file} to use absolute imports...")
    
    # Read the original file
    with open(manager_file, 'r') as f:
        content = f.read()
    
    # Create a backup
    backup_file = f"{manager_file}.bak"
    with open(backup_file, 'w') as f:
        f.write(content)
    print(f"Created backup: {backup_file}")
    
    # Modify the imports
    # First approach: Add sys.path modification at the beginning
    updated_content = f"""\"\"\"
ANT+ Manager for the Heart Rate Monitor App (Custom for OpenANT 1.3.3)

This module provides a class to manage ANT+ device connections and data processing,
specifically for heart rate monitors. It is optimized for OpenANT version 1.3.3
and is designed to integrate with the main Kivy heart rate application.
\"\"\"

import threading
import time
import traceback
import sys
import os

# Ensure OpenANT can be found
try:
    import openant
except ImportError:
    # Try to add OpenANT to the path
    openant_paths = [
"""
    
    # Add potential OpenANT paths
    if openant_path:
        updated_content += f"        r\"{openant_path}\",  # Found installation\n"
    
    # Add some common locations
    updated_content += """        "/Library/Frameworks/Python.framework/Versions/3.13/lib/python3.13/site-packages",  # Common macOS path
        "/usr/local/lib/python3.13/site-packages",  # Common Unix path
        os.path.expanduser("~/.local/lib/python3.13/site-packages"),  # User install path
        os.path.expanduser("~/Library/Python/3.13/lib/python3.13/site-packages"),  # macOS user path
    ]
    
    for path in openant_paths:
        if path not in sys.path and os.path.exists(path):
            sys.path.insert(0, path)
            break

# Try to import OpenANT again
try:
    import openant
    from openant.easy.node import Node
    from openant.devices import ANTPLUS_NETWORK_KEY
    
    # For OpenANT 1.3.3, we need direct access to the Driver
    from openant.base.ant import Driver
    
    OPENANT_AVAILABLE = True
    print(f"Successfully imported OpenANT {getattr(openant, '__version__', 'unknown')}")
except ImportError as e:
    OPENANT_AVAILABLE = False
    print(f"Failed to import OpenANT: {e}")

from kivy.event import EventDispatcher
from kivy.properties import BooleanProperty, NumericProperty, StringProperty
from kivy.clock import Clock
"""
    
    # Replace the original imports section with our updated version
    import_pattern = r'import threading.*?OPENANT_AVAILABLE = False'
    import_pattern_compiled = re.compile(import_pattern, re.DOTALL)
    
    if import_pattern_compiled.search(content):
        new_content = import_pattern_compiled.sub(updated_content, content)
        
        # Write the updated file
        with open(manager_file, 'w') as f:
            f.write(new_content)
        
        print(f"Updated {manager_file} with absolute imports.")
        return True
    else:
        print("Could not find the import section to replace.")
        return False

def check_updated_import():
    """Test if the updated ANT+ manager can import OpenANT"""
    print("\nTesting updated imports...")
    
    # Clear any cached imports
    if 'ant_manager_custom' in sys.modules:
        del sys.modules['ant_manager_custom']
    
    try:
        import ant_manager_final
        print("✓ Successfully imported ant_manager_custom module")
        
        if hasattr(ant_manager_final, 'OPENANT_AVAILABLE'):
            if ant_manager_final.OPENANT_AVAILABLE:
                print("✓ OpenANT is now available in the ANT+ manager!")
                return True
            else:
                print("✗ OpenANT still not available in the ANT+ manager.")
                if hasattr(ant_manager_final, 'openant'):
                    print("  But openant was imported (partial success).")
                    return True
        else:
            print("✗ Could not determine if OpenANT is available.")
        
    except ImportError as e:
        print(f"✗ Failed to import ant_manager_custom: {e}")
    except Exception as e:
        print(f"✗ Error during ant_manager_custom import: {e}")
    
    return False

def main():
    """Main function to fix OpenANT imports"""
    print("=== OpenANT Import Path Fixer ===")
    
    # Find OpenANT
    openant_path = find_openant_path()
    
    # Update the ANT+ manager
    success = update_ant_manager(openant_path)
    
    if success:
        # Test the updated imports
        import_successful = check_updated_import()
        
        if import_successful:
            print("\n✓ Success! The ANT+ manager should now be able to find OpenANT.")
            print("  Try running your main application again.")
        else:
            print("\n✗ The import fix was not successful.")
            print("  You may need to manually install OpenANT in the correct Python environment:")
            print("  pip install openant")
    else:
        print("\n✗ Failed to update the ANT+ manager file.")
    
    print("\nIf you still have issues, try running:")
    print("python debug_imports.py")

if __name__ == "__main__":
    main()