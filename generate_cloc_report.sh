#!/bin/bash

# File: generate_report.sh
# Usage: ./generate_report.sh

# Specify the output file
output_file="cloc_report.md"

# Get the current date and time
current_date=$(date "+%Y-%m-%d %H:%M:%S")

# Write the header to the output file
echo "# Code Analysis Report" > "$output_file"
echo "## Generated on $current_date" >> "$output_file"
echo "" >> "$output_file"

# Run cloc and append its output in Markdown format to the output file
echo '```' >> "$output_file"
cloc ./sierra_ils_utils >> "$output_file"
echo '```' >> "$output_file"
