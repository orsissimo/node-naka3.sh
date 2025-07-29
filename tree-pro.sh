#!/bin/bash

# ==============================================================================
# tree-pro.sh
#
# A script to generate a comprehensive snapshot of a specified directory.
#
# Usage: ./tree-pro.sh "/path/to/folder"
#
# 1. It runs 'tree' on the target directory to show its structure.
# 2. It then iterates through every file and appends its content,
#    skipping files inside directories defined in the EXCLUDE_FROM_CAT array.
# 3. The final combined output is saved to 'folder-scan.txt'.
# ==============================================================================

# Exit immediately if a command exits with a non-zero status.
set -e

# --- Configuration ---

# The name of the output file. It will be created in the current directory.
OUTPUT_FILE="folder-scan.txt"

# An array of directory names to exclude from the 'cat' command.
# Any file inside a directory with these names will be skipped.
# The check is for "/dirname/" so it won't match "my_contract_file.txt".
# Add or remove names as needed.
EXCLUDE_FROM_CAT=("contracts" "__pycache__" ".claude" "node_modules" ".git" "venv")


# --- Pre-run Checks ---

# 1. Check if the 'tree' command is installed.
if ! command -v tree &> /dev/null; then
    echo "Error: The 'tree' command is not installed." >&2
    echo "Please install it to run this script (e.g., 'sudo apt install tree')." >&2
    exit 1
fi

# 2. Check for the correct number of arguments.
if [ "$#" -ne 1 ]; then
    echo "Error: Incorrect number of arguments." >&2
    echo "Usage: $0 \"/path/to/folder/to/scan\"" >&2
    exit 1
fi

# 3. Check if the provided argument is a valid directory.
TARGET_DIR="$1"
if [ ! -d "$TARGET_DIR" ]; then
    echo "Error: The path '$TARGET_DIR' is not a valid directory." >&2
    exit 1
fi


# --- Main Logic ---

echo "Scanning directory: '$TARGET_DIR'..."
echo "Excluding contents of directories named: ${EXCLUDE_FROM_CAT[*]}"
echo "Output will be saved to '$OUTPUT_FILE' in the current directory."

# Start with a clean slate for the output file.
{
    echo "=================================================="
    echo "      Folder Scan Report for: $TARGET_DIR"
    echo "      Generated on: $(date)"
    echo "=================================================="
    echo ""
    echo "### DIRECTORY STRUCTURE ###"
    echo ""
} > "$OUTPUT_FILE"

# 1. Get the full directory tree structure.
tree "$TARGET_DIR" >> "$OUTPUT_FILE"

# 2. Add a separator before file contents.
{
    echo -e "\n\n##################################################"
    echo "###               FILE CONTENTS                ###"
    echo "##################################################"
} >> "$OUTPUT_FILE"

# 3. Find all files and process them, applying exclusions.
find "$TARGET_DIR" -type f | while read -r filepath; do
    is_excluded=false
    # Check if the file path contains any of the exclusion patterns.
    for dir_to_exclude in "${EXCLUDE_FROM_CAT[@]}"; do
        # We check for "/dir_to_exclude/" to ensure we match a directory name,
        # not just a file that happens to contain the string.
        if [[ "$filepath" == *"/${dir_to_exclude}/"* ]]; then
            is_excluded=true
            break # Found a match, no need to check other patterns
        fi
    done

    if [ "$is_excluded" = true ]; then
        # If the file is in an excluded directory, note it and skip.
        echo -e "\n\n---[ SKIPPING content of: $filepath (in excluded directory) ]---" >> "$OUTPUT_FILE"
    else
        # Otherwise, append the file's content.
        {
            echo -e "\n\n---[ START content of: $filepath ]---"
            # Use 'cat' and suppress errors for unreadable files.
            cat "$filepath" 2>/dev/null || echo "Error: Could not read file."
            echo -e "\n---[  END  content of: $filepath ]---"
        } >> "$OUTPUT_FILE"
    fi
done

echo "✅ Scan complete! Output saved to '$OUTPUT_FILE'."