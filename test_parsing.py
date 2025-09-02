#!/usr/bin/env python3

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from populate_csv import parse_folder_name, get_image_files
from pathlib import Path

def test_folder_parsing():
    """Test folder name parsing with sample folder names."""
    test_cases = [
        "RS=1025.00 - RDD-MELLISA (CHIFFON)",
        "RS=255.00 - TP-BANDHAN (RENIYAL)",
        "RS=1345.00 - RDD-VERONICA VOL-14 (30-30 BRASSO)",
        "RS=250.00 - CAS-LEMON SILK (ZOMATO)"
    ]
    
    print("Testing folder name parsing:")
    print("-" * 50)
    
    for folder_name in test_cases:
        result = parse_folder_name(folder_name)
        print(f"Folder: {folder_name}")
        print(f"  Name: '{result['name']}'")
        print(f"  Cost: '{result['cost_price']}'")
        print()

def test_image_files():
    """Test image file detection in a sample folder."""
    sample_folder = Path("./output/RS=1025.00 - RDD-MELLISA (CHIFFON)")
    
    if sample_folder.exists():
        print("Testing image file detection:")
        print("-" * 50)
        print(f"Folder: {sample_folder.name}")
        
        # Get all images
        all_images = list(sample_folder.glob('*.png'))
        print(f"Total images: {len(all_images)}")
        
        # Get images excluding last 2
        selected_images = get_image_files(sample_folder, skip_last=2)
        print(f"Selected images (excluding last 2): {len(selected_images)}")
        
        for i, img in enumerate(selected_images[:5], 1):  # Show first 5
            print(f"  {i}. {img.name}")
        
        if len(selected_images) > 5:
            print(f"  ... and {len(selected_images) - 5} more")
    else:
        print(f"Sample folder not found: {sample_folder}")

if __name__ == "__main__":
    test_folder_parsing()
    test_image_files()