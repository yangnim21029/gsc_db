#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GSC Database Manager - Initial Setup Script

This script creates the necessary directory structure and performs initial setup
for the GSC Database Manager project.
"""

import sys
from pathlib import Path


def create_directory_structure():
    """Create the required directory structure for the project."""
    project_root = Path(__file__).parent

    # Required directories
    required_dirs = ["data", "data/backups", "logs", "reports", "cred"]

    print("🔧 Creating project directory structure...")

    for dir_path in required_dirs:
        full_path = project_root / dir_path
        full_path.mkdir(parents=True, exist_ok=True)
        print(f"   ✅ Created: {dir_path}")

    # Create .gitkeep files for empty directories to ensure they're tracked
    gitkeep_dirs = ["data/backups", "logs", "reports"]

    for dir_path in gitkeep_dirs:
        gitkeep_path = project_root / dir_path / ".gitkeep"
        if not gitkeep_path.exists():
            gitkeep_path.touch()
            print(f"   📝 Created .gitkeep in: {dir_path}")


def create_config_templates():
    """Create template configuration files if they don't exist."""
    project_root = Path(__file__).parent

    # Create credentials directory readme
    cred_readme_path = project_root / "cred" / "README.md"
    if not cred_readme_path.exists():
        cred_readme_content = """# Credentials Directory

This directory stores Google API credentials and other sensitive configuration files.

## Required Files

1. **client_secret.json** - Google OAuth 2.0 client credentials
   - Download from Google Cloud Console
   - Required for Google Search Console API access

2. **sync_state.json** - Application state file (auto-generated)
   - Tracks synchronization progress
   - Created automatically during first run

## Security Notes

- Never commit credential files to version control
- These files contain sensitive information
- Ensure proper file permissions (600 for credentials)

## Setup Instructions

1. Visit [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing one
3. Enable Google Search Console API
4. Create OAuth 2.0 credentials
5. Download client_secret.json to this directory
6. Run `just auth` to complete authentication
"""
        cred_readme_path.write_text(cred_readme_content, encoding="utf-8")
        print("   📄 Created: cred/README.md")


def validate_environment():
    """Validate that the environment is properly set up."""
    print("\n🔍 Validating environment...")

    # Check Python version
    if sys.version_info < (3, 11):
        print(
            "   ⚠️  Warning: Python 3.11+ recommended, found {}.{}.{}".format(
                sys.version_info.major, sys.version_info.minor, sys.version_info.micro
            )
        )
    else:
        print(
            f"   ✅ Python version: {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
        )

    # Check for Poetry
    import subprocess

    try:
        result = subprocess.run(["poetry", "--version"], capture_output=True, text=True)
        if result.returncode == 0:
            print(f"   ✅ Poetry found: {result.stdout.strip()}")
        else:
            print("   ❌ Poetry not found - please install Poetry")
            return False
    except FileNotFoundError:
        print("   ❌ Poetry not found - please install Poetry")
        return False

    # Check for Just (optional)
    try:
        result = subprocess.run(["just", "--version"], capture_output=True, text=True)
        if result.returncode == 0:
            print(f"   ✅ Just found: {result.stdout.strip()}")
        else:
            print("   ⚠️  Just not found - install for easier task management")
            if sys.platform == "win32":
                print("      Alternative: Use setup.bat for Windows-specific setup")
    except FileNotFoundError:
        print("   ⚠️  Just not found - install for easier task management")
        if sys.platform == "win32":
            print("      Alternative: Use setup.bat for Windows-specific setup")

    return True


def main():
    """Main setup function."""
    print("=" * 60)
    print("🚀 GSC Database Manager - Initial Setup")
    print("=" * 60)

    # Create directory structure
    create_directory_structure()

    # Create configuration templates
    create_config_templates()

    # Validate environment
    if not validate_environment():
        print("\n❌ Environment validation failed. Please fix issues before continuing.")
        sys.exit(1)

    print("\n" + "=" * 60)
    print("✅ Setup completed successfully!")
    print("=" * 60)
    print("\n📝 Next steps:")
    print("1. Install dependencies: poetry install")
    print("2. Set up Google API credentials in cred/ directory")
    print("3. Enable Google Search Console API in Google Cloud Console")
    print("4. Run authentication: just auth (or poetry run gsc-cli auth login)")
    print('5. Add your first site: just site-add "sc-domain:example.com"')
    print("\n📚 For detailed setup instructions, see README.md")


if __name__ == "__main__":
    main()
