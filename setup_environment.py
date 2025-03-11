#!/usr/bin/env python
import os
import platform
import subprocess
import sys
from pathlib import Path

def run_command(command, error_message="Command failed"):
    """Run a shell command and handle errors"""
    try:
        print(f"Running: {command}")
        subprocess.check_call(command, shell=True)
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error: {error_message}")
        print(f"Command '{command}' failed with exit code {e.returncode}")
        return False

def create_virtual_environment():
    """Create a virtual environment for the FTBA project"""
    print("\n===== Setting up FTBA virtual environment =====")
    
    # Determine the Python executable to use
    python_cmd = "python" if platform.system() == "Windows" else "python3"
    
    # Check Python version
    try:
        version = subprocess.check_output(f"{python_cmd} --version", shell=True).decode().strip()
        print(f"Using {version}")
        
        # Ensure Python 3.10 or higher
        major, minor = map(int, version.split()[1].split('.')[:2])
        if major < 3 or (major == 3 and minor < 10):
            print("Warning: FTBA requires Python 3.10 or newer.")
            choice = input("Continue anyway? (y/n): ")
            if choice.lower() != 'y':
                sys.exit(1)
    except Exception as e:
        print(f"Error checking Python version: {e}")
        sys.exit(1)

    # Create venv directory if it doesn't exist
    venv_dir = Path("venv")
    if venv_dir.exists():
        choice = input("Virtual environment already exists. Recreate? (y/n): ")
        if choice.lower() == 'y':
            import shutil
            shutil.rmtree(venv_dir)
        else:
            print("Using existing virtual environment.")
            return venv_dir
    
    # Create virtual environment
    print("Creating virtual environment...")
    if not run_command(f"{python_cmd} -m venv venv", "Failed to create virtual environment"):
        sys.exit(1)
    
    return venv_dir

def install_requirements(venv_dir):
    """Install project requirements"""
    print("\n===== Installing requirements =====")
    
    # Determine the pip executable to use
    pip_cmd = os.path.join(venv_dir, "Scripts", "pip") if platform.system() == "Windows" else os.path.join(venv_dir, "bin", "pip")
    
    # Upgrade pip
    if not run_command(f"{pip_cmd} install --upgrade pip", "Failed to upgrade pip"):
        sys.exit(1)
    
    # Install pytest-related requirements explicitly for testing
    test_requirements = [
        "pytest",
        "pytest-asyncio>=0.25.0",
        "pytest-cov",
        "pytest-mock"
    ]
    
    print("Installing test requirements...")
    if not run_command(f"{pip_cmd} install {' '.join(test_requirements)}", "Failed to install test requirements"):
        sys.exit(1)
    
    # Install project requirements
    print("Installing project requirements...")
    if not run_command(f"{pip_cmd} install -r requirements.txt", "Failed to install project requirements"):
        sys.exit(1)
    
    # Install the project in development mode
    print("Installing FTBA in development mode...")
    if not run_command(f"{pip_cmd} install -e .", "Failed to install project in development mode"):
        sys.exit(1)

def display_activation_instructions(venv_dir):
    """Display instructions for activating the virtual environment"""
    print("\n===== Activation Instructions =====")
    if platform.system() == "Windows":
        print(f"To activate the virtual environment, run:")
        print(f"    {venv_dir}\\Scripts\\activate")
    else:
        print(f"To activate the virtual environment, run:")
        print(f"    source {venv_dir}/bin/activate")
    
    print("\nAfter activation, you can run:")
    print("    python main.py            # Run the bot with default settings")
    print("    python main.py --simulation # Run in simulation mode (no real trades)")
    print("    pytest tests/             # Run tests")

def main():
    """Main function"""
    print("FTBA Environment Setup")
    print("=====================")
    
    # Make sure we're in the project root directory
    if not os.path.exists('main.py'):
        script_dir = os.path.dirname(os.path.abspath(__file__))
        os.chdir(script_dir)
        if not os.path.exists('main.py'):
            print("Error: This script must be run from the project root directory")
            sys.exit(1)
    
    # Create virtual environment
    venv_dir = create_virtual_environment()
    
    # Install requirements
    install_requirements(venv_dir)
    
    # Display activation instructions
    display_activation_instructions(venv_dir)
    
    print("\nSetup complete! You're ready to start working with FTBA.")

if __name__ == "__main__":
    main()