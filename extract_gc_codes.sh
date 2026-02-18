#!/bin/bash

# Extract GC codes from iCaching app and copy to clipboard

cd "$(dirname "$0")" || exit

# Activate virtual environment if it exists
if [ -d ".venv" ]; then
    source .venv/bin/activate
elif [ -d "venv" ]; then
    source venv/bin/activate
fi

# Run the extraction script
python3 src/extract_gc_codes.py
