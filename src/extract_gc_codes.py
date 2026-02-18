#!/usr/bin/env python3
"""
Extract GC codes from a CSV file and copy to clipboard.
"""

import subprocess
import csv
from pathlib import Path


def copy_to_clipboard(text):
    """Copy text to macOS clipboard using pbcopy."""
    try:
        process = subprocess.Popen(['pbcopy'], stdin=subprocess.PIPE)
        process.communicate(text.encode('utf-8'))
        process.wait()
        return True
    except Exception as e:
        print(f"Error copying to clipboard: {e}")
        return False


def extract_gc_codes_from_csv(csv_path):
    """
    Extract GC codes from a CSV file.
    Looks for a column named 'GC Code' or similar variations.
    """
    try:
        csv_file = Path(csv_path)
        
        if not csv_file.exists():
            print(f"Error: CSV file not found at {csv_path}")
            return None
        
        gc_codes = []
        gc_code_column = None
        
        with open(csv_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            
            if not reader.fieldnames:
                print("Error: CSV file is empty or cannot be read")
                return None
            
            # Find the GC Code column (try various names)
            possible_names = ['GC Code', 'gc code', 'GCCode', 'gccode', 'Code', 'code']
            for col_name in reader.fieldnames:
                if col_name in possible_names or col_name.lower().strip() in [n.lower() for n in possible_names]:
                    gc_code_column = col_name
                    print(f"Found GC Code column: '{gc_code_column}'")
                    break
            
            if not gc_code_column:
                print(f"Error: Could not find GC Code column")
                print(f"Available columns: {', '.join(reader.fieldnames)}")
                return None
            
            # Extract GC codes
            for row in reader:
                code = row.get(gc_code_column, "").strip()
                if code:
                    gc_codes.append(code)
        
        return gc_codes if gc_codes else None
    
    except Exception as e:
        print(f"Error reading CSV file: {e}")
        import traceback
        traceback.print_exc()
        return None


def main():
    """Main function to extract and copy GC codes."""
    csv_path = Path.home() / "Downloads" / "geocaches.csv"
    
    print(f"Reading GC codes from: {csv_path}")
    
    gc_codes = extract_gc_codes_from_csv(csv_path)
    
    if gc_codes:
        # Create comma-separated list
        gc_code_list = ", ".join(gc_codes)
        
        print(f"\nFound {len(gc_codes)} GC codes:")
        print(gc_code_list)
        
        # Copy to clipboard
        if copy_to_clipboard(gc_code_list):
            print("\n✓ GC codes copied to clipboard!")
        else:
            print("\n✗ Failed to copy to clipboard")
    else:
        print("\nNo GC codes found. Please check:")
        print(f"1. File exists at: {csv_path}")
        print("2. CSV has a 'GC Code' column")
        print("3. There are GC codes in the file")


if __name__ == "__main__":
    main()
