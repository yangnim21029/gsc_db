"""
Console output utilities with Windows compatibility
"""

import os
import sys


def get_success_symbol():
    """Get success symbol based on platform and encoding"""
    if sys.platform == "win32" or os.environ.get("GSC_ASCII_MODE") == "1":
        return "[OK]"
    return "✓"


def get_error_symbol():
    """Get error symbol based on platform and encoding"""
    if sys.platform == "win32" or os.environ.get("GSC_ASCII_MODE") == "1":
        return "[FAIL]"
    return "✗"


def get_warning_symbol():
    """Get warning symbol based on platform and encoding"""
    if sys.platform == "win32" or os.environ.get("GSC_ASCII_MODE") == "1":
        return "[WARN]"
    return "⚠"


def format_success_message(message):
    """Format success message with appropriate symbol"""
    return f"[green]{get_success_symbol()}[/green] {message}"


def format_error_message(message):
    """Format error message with appropriate symbol"""
    return f"[red]{get_error_symbol()}[/red] {message}"


def format_warning_message(message):
    """Format warning message with appropriate symbol"""
    return f"[yellow]{get_warning_symbol()}[/yellow] {message}"
