#!/usr/bin/env python3
"""
OpenANT Path Fixer

This script helps resolve environment path issues between VS Code and the ANT+ tester application.
It creates a simple bridge to ensure both applications use the same Python environment.
"""

import sys
import os
import site
import subprocess
import shutil

def get_environment_info():
    """Get information about the current Python environment"""
    print("=== Python Environment Info ===")
    print(f"Python Version: {sys.version}")
    print(f"Python Executable: {sys.executable}")
    print(f"Site Packages: {site.getsitepackages()}")
    
    # Check if running in virtual environment
    in_venv = hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix)
    print(f"In Virtual Environment: {in_venv}")
    
    return {
        'executable': sys.executable,
        'site_packages': site.getsitepackages(),
        'in_venv': in_venv
    }

def check_openant_installation():
    """Check if OpenANT is installed and where"""
    print("\n=== Checking OpenANT Installation ===")
    
    openant_path = None
    
    try:
        import openant
        openant_path = os.path.dirname(openant.__file__)
        print(f"OpenANT found at: {openant_path}")
        print(f"OpenANT version: {getattr(openant, '__version__', 'unknown')}")
        return True, openant_path
    except ImportError:
        print("OpenANT not found in current environment")
        return False, None

def create_launcher_script(tester_path):
    """Create a launcher script that ensures the correct Python environment is used"""
    print("\n=== Creating Launcher Script ===")
    
    # Get the full path to the ANT+ tester
    if not os.path.isabs(tester_path):
        tester_path = os.path.abspath(tester_path)
    
    if not os.path.exists(tester_path):
        print(f"Error: The specified tester file '{tester_path}' does not exist.")
        return False
    
    # Create launcher name based on the tester filename
    base_name = os.path.basename(tester_path)
    launcher_name = f"run_{base_name}"
    launcher_path = os.path.join(os.path.dirname(tester_path), launcher_name)
    
    # Create the launcher script content
    launcher_content = f"""#!/usr/bin/env python3
# Auto-generated launcher script for {base_name}
# This script ensures the correct Python environment is used

import os
import sys
import subprocess

def main():
    # Use the exact same Python interpreter that created this script
    python_executable = "{sys.executable}"
    target_script = "{tester_path}"
    
    # Print environment information
    print("=== ANT+ Tester Launcher ===")
    print(f"Using Python: {{python_executable}}")
    print(f"Running: {{target_script}}")
    print("=" * 50)
    
    # Run the target script with the specific Python interpreter
    try:
        # Pass all command line arguments to the target script
        cmd = [python_executable, target_script] + sys.argv[1:]
        process = subprocess.Popen(cmd)
        process.wait()
        return process.returncode
    except Exception as e:
        print(f"Error running target script: {{e}}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
"""

    # Write the launcher script
    try:
        with open(launcher_path, 'w') as f:
            f.write(launcher_content)
        
        # Make it executable on Unix-like systems
        if os.name == 'posix':
            os.chmod(launcher_path, 0o755)
        
        print(f"Launcher script created: {launcher_path}")
        print(f"Run with: python {launcher_path}")
        if os.name == 'posix':
            print(f"Or simply: ./{launcher_name}")
        
        return True
    except Exception as e:
        print(f"Error creating launcher script: {e}")
        return False

def install_openant_if_needed():
    """Install OpenANT if not already installed"""
    installed, _ = check_openant_installation()
    if not installed:
        print("\n=== Installing OpenANT ===")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "openant"])
            print("OpenANT installed successfully!")
            return True
        except subprocess.CalledProcessError as e:
            print(f"Error installing OpenANT: {e}")
            return False
    return True

def main():
    print("=== OpenANT Environment Path Fixer ===")
    
    # Get current environment information
    env_info = get_environment_info()
    
    # Install OpenANT if needed
    if not install_openant_if_needed():
        print("Failed to install OpenANT. Please install it manually.")
        return 1
    
    # Check OpenANT installation again to get path
    openant_installed, openant_path = check_openant_installation()
    if not openant_installed:
        print("OpenANT installation check failed after installation attempt.")
        return 1
    
    # Create launcher script for ANT+ tester
    tester_paths = [
        "ant_tester_fixed.py",
        "ant_tester.py"
    ]
    
    for path in tester_paths:
        if os.path.exists(path):
            if create_launcher_script(path):
                print(f"\nEnvironment path fix applied successfully for {path}!")
                print("\nThis should resolve the issue with VS Code seeing OpenANT but the tester not finding it.")
                return 0
    
    print("\nCould not find any ANT+ tester scripts in the current directory.")
    print("Please specify the path to the ANT+ tester script:")
    custom_path = input("> ").strip()
    
    if custom_path and os.path.exists(custom_path):
        if create_launcher_script(custom_path):
            print(f"\nEnvironment path fix applied successfully for {custom_path}!")
            return 0
    else:
        print(f"Error: Invalid path or file not found: {custom_path}")
    
    return 1

if __name__ == "__main__":
    sys.exit(main())