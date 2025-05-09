#!/usr/bin/env python3
"""
Import Debugging Tool

This script helps identify import and environment issues when integrating ANT+ support.
"""

import sys
import os
import traceback

def print_environment_info():
    """Print detailed environment information"""
    print("\n=== Python Environment Information ===")
    print(f"Python version: {sys.version}")
    print(f"Python executable: {sys.executable}")
    print(f"Current working directory: {os.getcwd()}")
    
    # Check if running in virtual environment
    in_venv = hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix)
    print(f"Running in virtual environment: {in_venv}")
    
    # Print sys.path (where Python looks for modules)
    print("\nPython module search paths:")
    for i, path in enumerate(sys.path):
        print(f"  {i}: {path}")

def check_openant_installation():
    """Check for OpenANT installation"""
    print("\n=== OpenANT Library Check ===")
    
    try:
        import openant
        print(f"✓ OpenANT successfully imported")
        print(f"  Version: {getattr(openant, '__version__', 'unknown')}")
        print(f"  Location: {getattr(openant, '__file__', 'unknown')}")
        return True
    except ImportError as e:
        print(f"✗ OpenANT import failed: {e}")
        traceback.print_exc()
        
        # Check if the module exists but can't be imported properly
        try:
            print("\nChecking for openant module in Python path:")
            for path in sys.path:
                openant_path = os.path.join(path, 'openant')
                if os.path.exists(openant_path):
                    print(f"  Found openant directory at: {openant_path}")
                    print("  But import still failed. This suggests module structure issues.")
                    
                    # List files in the directory
                    if os.path.isdir(openant_path):
                        print("\n  Files in openant directory:")
                        for item in os.listdir(openant_path):
                            print(f"    - {item}")
        except Exception as e2:
            print(f"  Error checking for openant directory: {e2}")
        
        return False

def check_ant_manager_file():
    """Check if the ANT+ manager file exists in the correct location"""
    print("\n=== ANT+ Manager File Check ===")
    
    filename = "ant_manager_custom.py"
    if os.path.exists(filename):
        print(f"✓ Found {filename} in current directory")
        
        # Check if the file contains the expected content
        try:
            with open(filename, 'r') as f:
                content = f.read()
                if "class ANTManager(EventDispatcher):" in content:
                    print(f"✓ {filename} contains the ANTManager class")
                else:
                    print(f"✗ {filename} does not contain the expected ANTManager class")
        except Exception as e:
            print(f"✗ Error reading {filename}: {e}")
    else:
        print(f"✗ {filename} not found in current directory ({os.getcwd()})")
        
        # Look for the file in the Python path
        for path in sys.path:
            filepath = os.path.join(path, filename)
            if os.path.exists(filepath):
                print(f"  Found {filename} at: {filepath}")

def test_ant_manager_import():
    """Try to import the ANT+ manager"""
    print("\n=== ANT+ Manager Import Test ===")
    
    try:
        import ant_manager_final
        print(f"✓ Successfully imported ant_manager_133 module")
        
        # Check if ANTManager class exists
        if hasattr(ant_manager_final, 'ANTManager'):
            print(f"✓ ANTManager class found in module")
            
            # Check if OPENANT_AVAILABLE flag is set
            if hasattr(ant_manager_final, 'OPENANT_AVAILABLE'):
                print(f"  OPENANT_AVAILABLE flag: {ant_manager_final.OPENANT_AVAILABLE}")
            
            return True
        else:
            print(f"✗ ANTManager class not found in module")
    except ImportError as e:
        print(f"✗ Failed to import ant_manager_133: {e}")
        traceback.print_exc()
    except Exception as e:
        print(f"✗ Error during ant_manager_133 import: {e}")
        traceback.print_exc()
    
    return False

def main():
    """Run all diagnostic checks"""
    print("=== ANT+ Integration Diagnostic Tool ===")
    
    # Check environment
    print_environment_info()
    
    # Check OpenANT
    openant_available = check_openant_installation()
    
    # Check ANT+ manager file
    check_ant_manager_file()
    
    # Test ANT+ manager import
    manager_importable = test_ant_manager_import()
    
    # Summary
    print("\n=== Diagnostic Summary ===")
    print(f"OpenANT library available: {openant_available}")
    print(f"ANT+ manager importable: {manager_importable}")
    
    # Recommendations
    print("\n=== Recommendations ===")
    if not openant_available:
        print("1. Install OpenANT in the current Python environment:")
        print("   pip install openant")
        print("\n2. If you've already installed OpenANT, you might be running")
        print("   the application in a different Python environment.")
        print("   Try running from the command line with:")
        print("   python -m pip install openant")
        print("   python main.py")
        
    if not manager_importable:
        print("\n3. Make sure ant_manager_custom.py is in the same directory as main.py")
        print("   Current directory:", os.getcwd())
        
    print("\n4. After making changes, run this diagnostic tool again")
    print("   python debug_imports.py")

if __name__ == "__main__":
    main()
    