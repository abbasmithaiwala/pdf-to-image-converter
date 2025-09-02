#!/usr/bin/env python3

import os
import pandas as pd
import cloudinary
import cloudinary.uploader
from pathlib import Path
from dotenv import load_dotenv
import re
import logging
from typing import List, Dict, Optional
import sys

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('csv_population.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Configure Cloudinary
cloudinary.config(
    cloud_name=os.getenv('CLOUDINARY_CLOUD_NAME'),
    api_key=os.getenv('CLOUDINARY_API_KEY'),
    api_secret=os.getenv('CLOUDINARY_API_SECRET')
)

def validate_cloudinary_config():
    """Validate that Cloudinary configuration is properly set."""
    required_vars = ['CLOUDINARY_CLOUD_NAME', 'CLOUDINARY_API_KEY', 'CLOUDINARY_API_SECRET']
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        logger.error(f"Missing required environment variables: {', '.join(missing_vars)}")
        logger.error("Please copy .env.example to .env and fill in your Cloudinary credentials")
        return False
    return True

def parse_folder_name(folder_name: str) -> Dict[str, str]:
    """
    Parse folder name to extract product name and cost price.
    Format: RS=1025.00 - RDD-MELLISA (CHIFFON)
    """
    try:
        # Extract cost price (between RS= and first -)
        cost_match = re.search(r'RS=([0-9.]+)\s*-', folder_name)
        cost_price = cost_match.group(1) if cost_match else ""
        
        # Extract product name (everything after first - and space)
        name_match = re.search(r'RS=[0-9.]+\s*-\s*(.+)', folder_name)
        product_name = name_match.group(1).strip() if name_match else folder_name
        
        return {
            'name': product_name,
            'cost_price': cost_price
        }
    except Exception as e:
        logger.error(f"Error parsing folder name '{folder_name}': {e}")
        return {'name': folder_name, 'cost_price': ''}

def get_image_files(folder_path: Path, skip_last: int = 2) -> List[Path]:
    """
    Get image files from folder, excluding the last N files.
    """
    try:
        # Get all PNG files sorted by name
        image_files = sorted(folder_path.glob('*.png'))
        
        # Skip the last N files if there are more than N files
        if len(image_files) > skip_last:
            return image_files[:-skip_last]
        else:
            # If there are too few files, return empty list or log warning
            logger.warning(f"Folder '{folder_path.name}' has only {len(image_files)} images, skipping all")
            return []
    except Exception as e:
        logger.error(f"Error getting image files from '{folder_path}': {e}")
        return []

def upload_to_cloudinary(image_path: Path, folder_name: str) -> Optional[str]:
    """
    Upload image to Cloudinary and return the URL.
    """
    try:
        # Create a clean public_id using folder name and image name
        public_id = f"{os.getenv('CLOUDINARY_UPLOAD_FOLDER', 'product_images')}/{folder_name}/{image_path.stem}"
        
        # Upload image
        result = cloudinary.uploader.upload(
            str(image_path),
            public_id=public_id,
            overwrite=True,
            resource_type="image"
        )
        
        return result.get('secure_url')
    except Exception as e:
        logger.error(f"Error uploading '{image_path}' to Cloudinary: {e}")
        return None

def process_folder(folder_path: Path) -> Dict[str, any]:
    """
    Process a single folder and return product data with CDN URLs.
    """
    logger.info(f"Processing folder: {folder_path.name}")
    
    # Parse folder name
    product_info = parse_folder_name(folder_path.name)
    
    # Get image files (skip last 2)
    image_files = get_image_files(folder_path, skip_last=2)
    
    # Upload images and get URLs
    media_urls = []
    for i, image_file in enumerate(image_files[:8]):  # Limit to 8 media fields
        logger.info(f"  Uploading image {i+1}/{min(len(image_files), 8)}: {image_file.name}")
        url = upload_to_cloudinary(image_file, folder_path.name)
        if url:
            media_urls.append(url)
        else:
            logger.warning(f"  Failed to upload {image_file.name}")
    
    # Create product data
    product_data = {
        'name': product_info['name'],
        'description': f"Product from {product_info['name']}",  # Default description
        'bulk_price': '',  # Empty as requested
        'preferred_supplier': '',  # Empty as requested
        'cost_price': product_info['cost_price'],
        'mrp': '',  # Empty as requested
        'uom': 'pcs',  # Default unit
        'set_size': '',  # Empty as requested
        'moq': '',  # Empty as requested
        'available_quantity': ''  # Empty as requested
    }
    
    # Add media URLs (up to 8)
    for i in range(8):
        media_key = f'media_{i+1}'
        product_data[media_key] = media_urls[i] if i < len(media_urls) else ''
    
    logger.info(f"  Processed {len(media_urls)} images for '{product_info['name']}'")
    return product_data

def populate_csv(output_folder: str, csv_file: str):
    """
    Main function to populate CSV with product data from output folder.
    """
    logger.info("Starting CSV population process")
    
    # Validate Cloudinary configuration
    if not validate_cloudinary_config():
        sys.exit(1)
    
    output_path = Path(output_folder)
    csv_path = Path(csv_file)
    
    # Check if output folder exists
    if not output_path.exists():
        logger.error(f"Output folder '{output_folder}' does not exist")
        return False
    
    # Read existing CSV
    try:
        if csv_path.exists():
            logger.info(f"Reading existing CSV: {csv_file}")
            df = pd.read_csv(csv_path)
        else:
            logger.info("Creating new CSV file")
            # Create empty DataFrame with required columns
            columns = [
                'name', 'description', 'bulk_price', 'media_1', 'media_2', 'media_3', 'media_4',
                'media_5', 'media_6', 'media_7', 'media_8', 'preferred_supplier', 'cost_price',
                'mrp', 'uom', 'set_size', 'moq', 'available_quantity'
            ]
            df = pd.DataFrame(columns=columns)
    except Exception as e:
        logger.error(f"Error reading CSV file: {e}")
        return False
    
    # Get all folders in output directory
    folders = [d for d in output_path.iterdir() if d.is_dir()]
    logger.info(f"Found {len(folders)} folders to process")
    
    # Process each folder
    new_products = []
    successful = 0
    failed = 0
    
    for folder in folders:
        try:
            product_data = process_folder(folder)
            new_products.append(product_data)
            successful += 1
        except Exception as e:
            logger.error(f"Failed to process folder '{folder.name}': {e}")
            failed += 1
    
    # Add new products to DataFrame
    if new_products:
        new_df = pd.DataFrame(new_products)
        df = pd.concat([df, new_df], ignore_index=True)
        
        # Save updated CSV
        df.to_csv(csv_path, index=False)
        logger.info(f"Updated CSV saved: {csv_file}")
    
    logger.info(f"Process complete: {successful} successful, {failed} failed")
    logger.info(f"Total products in CSV: {len(df)}")
    
    return failed == 0

def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Populate CSV with product data from PDF output folders using Cloudinary CDN',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                                    # Uses default folders
  %(prog)s -o ./output -c ./products.csv     # Custom paths
  %(prog)s --dry-run                         # Test without uploading
        """
    )
    
    parser.add_argument(
        '-o', '--output',
        type=str,
        default='./output',
        help='Output folder containing product folders (default: ./output)'
    )
    
    parser.add_argument(
        '-c', '--csv',
        type=str,
        default='./test_upload.csv',
        help='CSV file to populate (default: ./test_upload.csv)'
    )
    
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Test run without uploading to Cloudinary'
    )
    
    args = parser.parse_args()
    
    if args.dry_run:
        logger.info("DRY RUN MODE - No images will be uploaded")
        # TODO: Implement dry run mode
        return
    
    success = populate_csv(args.output, args.csv)
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()