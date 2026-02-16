#!/usr/bin/env python3
"""
Project File Fetch Script
Fetches files from a project folder based on project number.
"""

import argparse
import os
import sys


def main():
    """Main function to handle project file fetching."""
    parser = argparse.ArgumentParser(
        description='Fetch project files based on project number and folder path.'
    )
    
    parser.add_argument(
        '--project-number',
        '-p',
        type=str,
        required=True,
        help='Project number identifier'
    )
    
    parser.add_argument(
        '--folder',
        '-f',
        type=str,
        required=True,
        help='Folder path to fetch files from'
    )
    
    args = parser.parse_args()
    
    project_number = args.project_number
    folder_path = args.folder
    
    # Validate inputs
    if not project_number:
        print("Error: Project number cannot be empty.", file=sys.stderr)
        sys.exit(1)
    
    if not folder_path:
        print("Error: Folder path cannot be empty.", file=sys.stderr)
        sys.exit(1)
    
    # Check if folder exists
    if not os.path.exists(folder_path):
        print(f"Error: Folder '{folder_path}' does not exist.", file=sys.stderr)
        sys.exit(1)
    
    if not os.path.isdir(folder_path):
        print(f"Error: '{folder_path}' is not a directory.", file=sys.stderr)
        sys.exit(1)
    
    # Process the request
    print(f"Fetching files for project: {project_number}")
    print(f"From folder: {os.path.abspath(folder_path)}")
    
    # List files in the folder
    try:
        files = os.listdir(folder_path)
        if not files:
            print("No files found in the specified folder.")
        else:
            print(f"\nFound {len(files)} item(s):")
            for item in sorted(files):
                item_path = os.path.join(folder_path, item)
                if os.path.isfile(item_path):
                    size = os.path.getsize(item_path)
                    print(f"  [FILE] {item} ({size} bytes)")
                elif os.path.isdir(item_path):
                    print(f"  [DIR]  {item}")
    except PermissionError:
        print(f"Error: Permission denied accessing '{folder_path}'.", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: {str(e)}", file=sys.stderr)
        sys.exit(1)
    
    print("\nOperation completed successfully.")


if __name__ == '__main__':
    main()
