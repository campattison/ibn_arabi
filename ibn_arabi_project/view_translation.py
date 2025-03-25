#!/usr/bin/env python3
import os
import webbrowser
import sys
from pathlib import Path

def open_translation():
    """Open the HTML translation file in the default web browser."""
    # Get the directory of this script
    script_dir = Path(os.path.dirname(os.path.abspath(__file__)))
    
    # Path to the HTML file
    html_file = script_dir / "output" / "ibn_arabi_translation.html"
    
    # Convert to file URL with absolute path
    file_url = f"file://{html_file.absolute()}"
    
    print(f"Opening translation in browser: {file_url}")
    
    # Open the URL in the default web browser
    webbrowser.open(file_url)

if __name__ == "__main__":
    open_translation() 