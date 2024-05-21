#!/bin/bash

# Define the filenames
file1="bp-agent.7z"
file2="contiki-2.7.7z"

# Check if p7zip is installed
if ! command -v 7z &> /dev/null
then
    echo "7z could not be found, please install p7zip."
    exit 1
fi

# Function to extract and remove the 7z file
extract_and_remove() {
    local file=$1
    if [ -f "$file" ]; then
        echo "Extracting $file..."
        7z x "$file" -y
        if [ $? -eq 0 ]; then
            echo "Extraction successful. Removing $file..."
            rm "$file"
        else
            echo "Failed to extract $file"
            exit 1
        fi
    else
        echo "$file not found!"
    fi
}

# Extract and remove the files
extract_and_remove "$file1"
extract_and_remove "$file2"

echo "Done!"
