# project-file-fetch

A Python script to fetch and list files from a project folder based on a project number.

## Usage

Run the script with required arguments:

```bash
python3 fetch_project_files.py --project-number <PROJECT_NUMBER> --folder <FOLDER_PATH>
```

Or using short options:

```bash
python3 fetch_project_files.py -p <PROJECT_NUMBER> -f <FOLDER_PATH>
```

### Arguments

- `--project-number, -p`: Project number identifier (required)
- `--folder, -f`: Path to the folder to fetch files from (required)

### Examples

```bash
# Fetch files from current directory for project 12345
python3 fetch_project_files.py --project-number 12345 --folder .

# Fetch files from a specific path
python3 fetch_project_files.py -p ABC-001 -f /path/to/project/files

# Show help
python3 fetch_project_files.py --help
```

## Features

- Validates that the specified folder exists and is accessible
- Lists all files and directories in the specified folder
- Shows file sizes for regular files
- Provides clear error messages for invalid inputs