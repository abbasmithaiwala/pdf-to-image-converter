#!/usr/bin/env python3

import os
import pandas as pd
import cloudinary
import cloudinary.uploader
from pathlib import Path
from dotenv import load_dotenv
import re
import logging
from typing import List, Dict, Optional, Tuple
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from functools import partial, lru_cache
import threading
from tqdm import tqdm
import psutil

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('csv_population_parallel.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Thread-local storage for Cloudinary configuration
thread_local = threading.local()

def get_cloudinary_config():
    """Get thread-local Cloudinary configuration."""
    if not hasattr(thread_local, 'cloudinary_configured'):
        cloudinary.config(
            cloud_name=os.getenv('CLOUDINARY_CLOUD_NAME'),
            api_key=os.getenv('CLOUDINARY_API_KEY'),
            api_secret=os.getenv('CLOUDINARY_API_SECRET')
        )
        thread_local.cloudinary_configured = True
    return True

class PerformanceMonitor:
    """Monitor performance metrics during processing."""
    
    def __init__(self):
        self.start_time = time.time()
        self.processed_folders = 0
        self.processed_images = 0
        self.failed_uploads = 0
        self.total_upload_time = 0
        self.lock = threading.Lock()
    
    def update_folder(self, increment: int = 1):
        with self.lock:
            self.processed_folders += increment
    
    def update_images(self, increment: int = 1, upload_time: float = 0):
        with self.lock:
            self.processed_images += increment
            self.total_upload_time += upload_time
    
    def update_failed(self, increment: int = 1):
        with self.lock:
            self.failed_uploads += increment
    
    def get_stats(self) -> Dict[str, any]:
        elapsed = time.time() - self.start_time
        with self.lock:
            avg_upload_time = self.total_upload_time / max(self.processed_images, 1)
            return {
                'elapsed_time': elapsed,
                'folders_processed': self.processed_folders,
                'images_processed': self.processed_images,
                'failed_uploads': self.failed_uploads,
                'avg_upload_time': avg_upload_time,
                'images_per_second': self.processed_images / max(elapsed, 1),
                'cpu_percent': psutil.cpu_percent(),
                'memory_percent': psutil.virtual_memory().percent
            }

# Global performance monitor
perf_monitor = PerformanceMonitor()

def validate_cloudinary_config():
    """Validate that Cloudinary configuration is properly set."""
    required_vars = ['CLOUDINARY_CLOUD_NAME', 'CLOUDINARY_API_KEY', 'CLOUDINARY_API_SECRET']
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        logger.error(f"Missing required environment variables: {', '.join(missing_vars)}")
        logger.error("Please copy .env.example to .env and fill in your Cloudinary credentials")
        return False
    return True

@lru_cache(maxsize=1000)
def parse_folder_name(folder_name: str) -> Tuple[str, str]:
    """
    Parse folder name to extract product name and cost price.
    Format: RS=1025.00 - RDD-MELLISA (CHIFFON)
    Cached for performance.
    """
    try:
        # Extract cost price (between RS= and first -)
        cost_match = re.search(r'RS=([0-9.]+)\s*-', folder_name)
        cost_price = cost_match.group(1) if cost_match else ""
        
        # Extract product name (everything after first - and space)
        name_match = re.search(r'RS=[0-9.]+\s*-\s*(.+)', folder_name)
        product_name = name_match.group(1).strip() if name_match else folder_name
        
        return product_name, cost_price
    except Exception as e:
        logger.error(f"Error parsing folder name '{folder_name}': {e}")
        return folder_name, ''

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
            # If there are too few files, return empty list
            logger.warning(f"Folder '{folder_path.name}' has only {len(image_files)} images, skipping all")
            return []
    except Exception as e:
        logger.error(f"Error getting image files from '{folder_path}': {e}")
        return []

def upload_to_cloudinary_with_retry(image_path: Path, folder_name: str, max_retries: int = 3, timeout: int = 30) -> Optional[str]:
    """
    Upload image to Cloudinary with retry logic and return the URL.
    """
    get_cloudinary_config()  # Ensure thread-local config
    
    for attempt in range(max_retries):
        try:
            start_time = time.time()
            
            # Create a clean public_id using folder name and image name
            public_id = f"{os.getenv('CLOUDINARY_UPLOAD_FOLDER', 'product_images')}/{folder_name}/{image_path.stem}"
            
            # Upload image
            result = cloudinary.uploader.upload(
                str(image_path),
                public_id=public_id,
                overwrite=True,
                resource_type="image",
                timeout=timeout
            )
            
            upload_time = time.time() - start_time
            perf_monitor.update_images(1, upload_time)
            
            return result.get('secure_url')
            
        except Exception as e:
            logger.warning(f"Upload attempt {attempt + 1}/{max_retries} failed for '{image_path.name}': {e}")
            if attempt == max_retries - 1:
                logger.error(f"Final upload failure for '{image_path}': {e}")
                perf_monitor.update_failed(1)
                return None
            # Exponential backoff
            time.sleep(2 ** attempt)
    
    return None

def upload_images_concurrently(image_files: List[Path], folder_name: str, max_workers: int = 5) -> List[str]:
    """
    Upload multiple images concurrently and return list of URLs.
    """
    media_urls = []
    
    if not image_files:
        return media_urls
    
    # Create progress bar for this folder's images
    with tqdm(total=len(image_files), desc=f"Uploading {folder_name[:30]}...", leave=False) as pbar:
        with ThreadPoolExecutor(max_workers=min(max_workers, len(image_files))) as executor:
            # Submit all upload tasks
            future_to_index = {}
            for i, image_file in enumerate(image_files):
                future = executor.submit(upload_to_cloudinary_with_retry, image_file, folder_name)
                future_to_index[future] = i
            
            # Initialize results list with None values
            results = [None] * len(image_files)
            
            # Collect results as they complete
            for future in as_completed(future_to_index):
                index = future_to_index[future]
                try:
                    url = future.result()
                    results[index] = url
                    if url:
                        pbar.set_postfix(status="Success")
                    else:
                        pbar.set_postfix(status="Failed")
                except Exception as e:
                    logger.error(f"Exception in upload future: {e}")
                    results[index] = None
                finally:
                    pbar.update(1)
    
    # Filter out None values and maintain order
    media_urls = [url for url in results if url is not None]
    return media_urls

def process_folder_parallel(folder_path: Path, max_image_workers: int = 5) -> Dict[str, any]:
    """
    Process a single folder with concurrent image uploads.
    """
    folder_name = folder_path.name
    logger.info(f"Processing folder: {folder_name}")
    
    # Parse folder name
    product_name, cost_price = parse_folder_name(folder_name)
    
    # Get image files (skip last 2)
    image_files = get_image_files(folder_path, skip_last=2)
    
    # Limit to 8 media fields
    image_files = image_files[:8]
    
    # Upload images concurrently
    media_urls = upload_images_concurrently(image_files, folder_name, max_image_workers)
    
    # Create product data
    product_data = {
        'name': product_name,
        'description': f"Product from {product_name}",
        'bulk_price': '',
        'preferred_supplier': '',
        'cost_price': cost_price,
        'mrp': '',
        'uom': 'pcs',
        'set_size': '',
        'moq': '',
        'available_quantity': ''
    }
    
    # Add media URLs (up to 8)
    for i in range(8):
        media_key = f'media_{i+1}'
        product_data[media_key] = media_urls[i] if i < len(media_urls) else ''
    
    perf_monitor.update_folder(1)
    logger.info(f"Completed folder: {folder_name} ({len(media_urls)} images)")
    
    return product_data

def process_folders_in_batches(folders: List[Path], max_folder_workers: int = 10, max_image_workers: int = 5) -> List[Dict[str, any]]:
    """
    Process multiple folders concurrently using ThreadPoolExecutor.
    """
    new_products = []
    
    # Create main progress bar
    with tqdm(total=len(folders), desc="Processing folders", unit="folder") as pbar:
        with ThreadPoolExecutor(max_workers=max_folder_workers) as executor:
            # Create partial function with fixed max_image_workers
            process_func = partial(process_folder_parallel, max_image_workers=max_image_workers)
            
            # Submit all folder processing tasks
            future_to_folder = {executor.submit(process_func, folder): folder for folder in folders}
            
            # Collect results as they complete
            for future in as_completed(future_to_folder):
                folder = future_to_folder[future]
                try:
                    product_data = future.result()
                    new_products.append(product_data)
                    pbar.set_postfix(folder=folder.name[:30])
                except Exception as e:
                    logger.error(f"Failed to process folder '{folder.name}': {e}")
                finally:
                    pbar.update(1)
    
    return new_products

def log_performance_stats():
    """Log current performance statistics."""
    stats = perf_monitor.get_stats()
    logger.info(f"Performance Stats:")
    logger.info(f"  Elapsed Time: {stats['elapsed_time']:.2f}s")
    logger.info(f"  Folders Processed: {stats['folders_processed']}")
    logger.info(f"  Images Processed: {stats['images_processed']}")
    logger.info(f"  Failed Uploads: {stats['failed_uploads']}")
    logger.info(f"  Avg Upload Time: {stats['avg_upload_time']:.2f}s")
    logger.info(f"  Images/Second: {stats['images_per_second']:.2f}")
    logger.info(f"  CPU Usage: {stats['cpu_percent']:.1f}%")
    logger.info(f"  Memory Usage: {stats['memory_percent']:.1f}%")

def populate_csv_parallel(output_folder: str, csv_file: str, max_folder_workers: int = 10, max_image_workers: int = 5):
    """
    Main function to populate CSV with product data using parallel processing.
    """
    logger.info("Starting parallel CSV population process")
    logger.info(f"Configuration: {max_folder_workers} folder workers, {max_image_workers} image workers per folder")
    
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
    
    if not folders:
        logger.warning("No folders found to process")
        return True
    
    # Process folders in parallel
    start_time = time.time()
    new_products = process_folders_in_batches(folders, max_folder_workers, max_image_workers)
    processing_time = time.time() - start_time
    
    # Log performance statistics
    log_performance_stats()
    
    # Add new products to DataFrame
    if new_products:
        new_df = pd.DataFrame(new_products)
        df = pd.concat([df, new_df], ignore_index=True)
        
        # Save updated CSV
        df.to_csv(csv_path, index=False)
        logger.info(f"Updated CSV saved: {csv_file}")
    
    logger.info(f"Parallel processing complete in {processing_time:.2f}s")
    logger.info(f"Total products in CSV: {len(df)}")
    
    return len(new_products) == len(folders)  # Success if all folders processed

def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Populate CSV with product data using parallel processing and Cloudinary CDN',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                                              # Default settings
  %(prog)s --max-folder-workers 20 --max-image-workers 10  # High performance
  %(prog)s --max-folder-workers 5 --max-image-workers 3    # Conservative
  %(prog)s -o ./output -c ./products.csv               # Custom paths
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
        '--max-folder-workers',
        type=int,
        default=10,
        help='Maximum number of folders to process concurrently (default: 10)'
    )
    
    parser.add_argument(
        '--max-image-workers',
        type=int,
        default=5,
        help='Maximum number of images to upload concurrently per folder (default: 5)'
    )
    
    parser.add_argument(
        '--sequential',
        action='store_true',
        help='Use sequential processing (fallback mode)'
    )
    
    parser.add_argument(
        '--stats-interval',
        type=int,
        default=30,
        help='Interval in seconds to log performance stats (default: 30)'
    )
    
    args = parser.parse_args()
    
    # Validate worker counts
    if args.max_folder_workers < 1 or args.max_folder_workers > 50:
        logger.error("max-folder-workers must be between 1 and 50")
        sys.exit(1)
    
    if args.max_image_workers < 1 or args.max_image_workers > 20:
        logger.error("max-image-workers must be between 1 and 20")
        sys.exit(1)
    
    if args.sequential:
        logger.info("Sequential mode requested - using original script logic")
        # Import and use original function
        from populate_csv import populate_csv
        success = populate_csv(args.output, args.csv)
    else:
        success = populate_csv_parallel(
            args.output, 
            args.csv, 
            args.max_folder_workers,
            args.max_image_workers
        )
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()