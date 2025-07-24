"""
Legacy API module for backward compatibility

This module now imports the app from the new modular structure.
All the API logic has been moved to src/web/api/ directory.
"""

# Import the app from the new location
from .api import app

# For backward compatibility, also export commonly used items
__all__ = ["app"]

# Note: This file is kept for backward compatibility.
# New imports should use: from src.web.api import app
