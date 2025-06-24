#!/usr/bin/env python3
"""
Setup script for Claude Desktop Archiver
"""

import os
import sys
import subprocess
from pathlib import Path

def check_python_version():
    """Ensure Python 3.7+"""
    if sys.version_info < (3, 7):
        print("Python 3.7 or higher required")
        print(f"Current version: {sys.version}")
        return False
    print(f"Python version: {sys.version}")
    return True

def install_dependencies():
    """Install required packages"""
    print("Installing dependencies...")
    
    try:
        subprocess.check_call([
            sys.executable, "-m", "pip", "install", "-r", "requirements.txt"
        ])
        print("Dependencies installed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Failed to install dependencies: {e}")
        return False
    
# ! removing not needed 
# def create_launch_script():
#     """Create a convenient launch script"""
#     script_content = '''#!/usr/bin/env python3
# import sys
# import os
# sys.path.insert(0, os.path.dirname(__file__))
# from claude_archiver import main

# if __name__ == "__main__":
#     main()
# '''
    
#     with open("launch_archiver.py", "w") as f:
#         f.write(script_content)
    
#     # Make executable
#     os.chmod("launch_archiver.py", 0o755)
#     print("Created launch script: launch_archiver.py")

def setup_directories():
    """Create necessary directories"""
    home = Path.home()
    archives_dir = home / "test_archive"
    archives_dir.mkdir(exist_ok=True)
    print(f"Created archives directory: {archives_dir}")

def print_next_steps():
    """Print instructions for the user"""
    print("\nSetup complete!")
    print("\nNext steps:")
    print("1. Grant Accessibility permissions:")
    print("   → System Preferences → Security & Privacy → Privacy → Accessibility")
    print("   → Add Terminal (or your Python IDE) to the list")
    print("\n2. Make sure Claude Desktop app is installed")
    print("\n3. Run the archiver:")
    print("   python3 claude_archiver.py")
    print("\n4. Open Claude Desktop and start a conversation")
    print("\nArchives will be saved to: ~/test_archive/")

def main():
    print("Claude Desktop Archiver Setup")
    print("=" * 40)
    
    if not check_python_version():
        return False
    
    if not install_dependencies():
        return False
    
    # ! removing not needed 
    # create_launch_script()
    setup_directories()
    print_next_steps()
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)