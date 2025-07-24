"""
Windows encoding fix for console output
"""

import io
import os
import sys


def fix_windows_encoding():
    """
    Fix Windows console encoding issues for UTF-8 output.
    This should be called as early as possible in the application.
    """
    if sys.platform != "win32":
        return

    # Set environment variable for Python to use UTF-8
    os.environ["PYTHONIOENCODING"] = "utf-8"

    # Force stdout and stderr to use UTF-8
    if hasattr(sys.stdout, "buffer"):
        sys.stdout = io.TextIOWrapper(
            sys.stdout.buffer, encoding="utf-8", errors="replace", line_buffering=True
        )
    if hasattr(sys.stderr, "buffer"):
        sys.stderr = io.TextIOWrapper(
            sys.stderr.buffer, encoding="utf-8", errors="replace", line_buffering=True
        )

    # Try to set Windows console code page to UTF-8 (65001)
    try:
        import subprocess

        subprocess.run(["chcp", "65001"], shell=True, capture_output=True)
    except Exception:
        pass

    # Configure locale if possible
    try:
        import locale

        locale.setlocale(locale.LC_ALL, "en_US.UTF-8")
    except Exception:
        try:
            locale.setlocale(locale.LC_ALL, "")
        except Exception:
            pass
