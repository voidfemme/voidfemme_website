#!/bin/bash
# [project-root-dir]/build-css.sh
# Script to concatenate CSS files and handle backup/restore operations

# Define the source and output directories
CSS_DIR="src/static/css"
OUTPUT_FILE="$CSS_DIR/main.css"
BACKUP_FILE="$CSS_DIR/main.css.bak"

# Check if --revert flag is used
if [ "$1" = "--revert" ]; then
    if [ -f "$BACKUP_FILE" ]; then
        mv "$BACKUP_FILE" "$OUTPUT_FILE"
        echo "Restored previous version from $BACKUP_FILE"
        exit 0
    else
        echo "No backup file found at $BACKUP_FILE"
        exit 1
    fi
fi

# Create backup of existing file if it exists
if [ -f "$OUTPUT_FILE" ]; then
    cp "$OUTPUT_FILE" "$BACKUP_FILE"
fi

# Create or clear the output file
> "$OUTPUT_FILE"

# Function to append a file with a header comment
append_file() {
    echo "Processing: $1"
    cat "$1" >> "$OUTPUT_FILE"
}

# Function to append multiple files matching a pattern
append_files() {
    for file in $1; do
        if [ -f "$file" ]; then
            append_file "$file"
        fi
    done
}

# Abstracts
append_files "$CSS_DIR/abstracts/_*.css"

# Base
append_files "$CSS_DIR/base/_*.css"

# Layouts - main layouts first
append_files "$CSS_DIR/layouts/_grid.css"
append_files "$CSS_DIR/layouts/_header.css"
append_files "$CSS_DIR/layouts/_footer.css"

# Layouts - pages
append_files "$CSS_DIR/layouts/pages/_*.css"

# Components
append_files "$CSS_DIR/components/_*.css"

# Themes
append_files "$CSS_DIR/themes/_*.css"

echo "CSS files have been concatenated into $OUTPUT_FILE"
