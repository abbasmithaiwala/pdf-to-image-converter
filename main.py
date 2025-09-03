#!/usr/bin/env python3

import os
import argparse
import multiprocessing as mp
from pathlib import Path
from pdf2image import convert_from_path
from pdf2image.exceptions import PDFInfoNotInstalledError, PDFPageCountError, PDFSyntaxError
import sys
from functools import partial
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
try:
    from tqdm import tqdm
    TQDM_AVAILABLE = True
except ImportError:
    TQDM_AVAILABLE = False
    print("Note: Install 'tqdm' for better progress tracking: pip install tqdm")


def create_output_folder(pdf_path, destination_base):
    """Create output folder for a PDF file."""
    pdf_name = Path(pdf_path).stem
    output_folder = Path(destination_base) / pdf_name
    output_folder.mkdir(parents=True, exist_ok=True)
    return output_folder


def convert_pdf_to_images(pdf_path, output_folder, image_format='png', dpi=200, skip_existing=False, verbose=False):
    """Convert a single PDF to images and save them in the output folder."""
    try:
        pdf_name = Path(pdf_path).name
        
        # Check if folder already has images and skip if requested
        if skip_existing and output_folder.exists():
            existing_images = list(output_folder.glob(f'*.{image_format}'))
            if existing_images:
                if verbose:
                    print(f"  Skipping {pdf_name} - images already exist")
                return True
        
        if verbose:
            print(f"  Converting {pdf_name}...")
        
        # Convert PDF to list of images
        images = convert_from_path(
            pdf_path, 
            dpi=dpi,
            fmt=image_format,
            thread_count=2,
            use_pdftocairo=True  # More efficient than pdftoppm
        )
        
        # Save each page as an image
        for i, image in enumerate(images, 1):
            image_path = output_folder / f"page_{i:04d}.{image_format}"
            image.save(image_path, image_format.upper())
            if verbose:
                print(f"    Saved page {i}/{len(images)}")
        
        if verbose:
            print(f"  Completed {pdf_name}: {len(images)} pages")
        return True
        
    except PDFInfoNotInstalledError:
        print(f"  Error: poppler-utils not installed. Please install it:")
        print(f"    macOS: brew install poppler")
        print(f"    Ubuntu/Debian: sudo apt-get install poppler-utils")
        print(f"    Windows: Download from https://github.com/oschwartz10612/poppler-windows/releases/")
        return False
    except PDFPageCountError:
        print(f"  Error: Unable to get page count for {pdf_name}")
        return False
    except PDFSyntaxError:
        print(f"  Error: PDF syntax error in {pdf_name}")
        return False
    except Exception as e:
        print(f"  Error processing {pdf_name}: {str(e)}")
        return False


def process_single_pdf(pdf_info):
    """Process a single PDF - designed for multiprocessing."""
    pdf_path, dest_path, image_format, dpi, skip_existing, verbose = pdf_info
    
    try:
        output_folder = create_output_folder(pdf_path, dest_path)
        success = convert_pdf_to_images(pdf_path, output_folder, image_format, dpi, skip_existing, verbose)
        return {
            'pdf_path': pdf_path,
            'success': success,
            'pages': len(list(output_folder.glob(f'*.{image_format}'))) if success else 0,
            'error': None
        }
    except Exception as e:
        return {
            'pdf_path': pdf_path,
            'success': False,
            'pages': 0,
            'error': str(e)
        }


def process_all_pdfs(source_folder, destination_folder, image_format='png', dpi=200, skip_existing=False, workers=None, verbose=False):
    """Process all PDFs in the source folder."""
    source_path = Path(source_folder)
    dest_path = Path(destination_folder)
    
    # Check if source folder exists
    if not source_path.exists():
        print(f"Error: Source folder '{source_folder}' does not exist")
        return False
    
    # Create destination folder if it doesn't exist
    dest_path.mkdir(parents=True, exist_ok=True)
    
    # Find all PDF files
    pdf_files = list(source_path.glob('*.pdf'))
    
    if not pdf_files:
        print(f"No PDF files found in '{source_folder}'")
        return False
    
    # Determine optimal number of workers
    if workers is None:
        workers = min(len(pdf_files), mp.cpu_count())
    else:
        workers = min(workers, len(pdf_files))
    
    print(f"Found {len(pdf_files)} PDF file(s) to process")
    print(f"Source: {source_folder}")
    print(f"Destination: {destination_folder}")
    print(f"Settings: Format={image_format.upper()}, DPI={dpi}, Workers={workers}")
    print("-" * 50)
    
    # Prepare PDF info for multiprocessing
    pdf_infos = [(pdf_path, dest_path, image_format, dpi, skip_existing, verbose) for pdf_path in pdf_files]
    
    successful = 0
    failed = 0
    total_pages = 0
    start_time = time.time()
    
    # Use multiprocessing to process PDFs in parallel
    if workers > 1:
        with ProcessPoolExecutor(max_workers=workers) as executor:
            # Submit all jobs
            future_to_pdf = {executor.submit(process_single_pdf, pdf_info): pdf_info[0] for pdf_info in pdf_infos}
            
            # Process completed jobs with progress bar
            if TQDM_AVAILABLE and not verbose:
                progress_bar = tqdm(total=len(pdf_files), desc="Processing PDFs", unit="PDF")
            
            for future in as_completed(future_to_pdf):
                result = future.result()
                
                if result['success']:
                    successful += 1
                    total_pages += result['pages']
                    if verbose:
                        print(f"  ✓ Completed {Path(result['pdf_path']).name}: {result['pages']} pages")
                else:
                    failed += 1
                    if verbose or not TQDM_AVAILABLE:
                        error_msg = result['error'] if result['error'] else "Unknown error"
                        print(f"  ✗ Failed {Path(result['pdf_path']).name}: {error_msg}")
                
                if TQDM_AVAILABLE and not verbose:
                    progress_bar.update(1)
                    progress_bar.set_postfix({
                        'Success': successful,
                        'Failed': failed,
                        'Pages': total_pages
                    })
            
            if TQDM_AVAILABLE and not verbose:
                progress_bar.close()
    else:
        # Single-threaded processing (fallback)
        if TQDM_AVAILABLE and not verbose:
            pdf_infos = tqdm(pdf_infos, desc="Processing PDFs", unit="PDF")
        
        for pdf_info in pdf_infos:
            result = process_single_pdf(pdf_info)
            
            if result['success']:
                successful += 1
                total_pages += result['pages']
            else:
                failed += 1
    
    elapsed_time = time.time() - start_time
    
    print("-" * 50)
    print(f"Processing complete: {successful} successful, {failed} failed")
    print(f"Total pages converted: {total_pages}")
    print(f"Time elapsed: {elapsed_time:.2f}s")
    if total_pages > 0:
        print(f"Average speed: {total_pages/elapsed_time:.1f} pages/sec")
    return failed == 0


def main():
    parser = argparse.ArgumentParser(
        description='Convert PDFs to images and organize them in folders',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                        # Uses default folders: ./pdfs → ./output
  %(prog)s --format jpg --dpi 300 # Convert to JPG with high quality
  %(prog)s -s ./documents -d ./images --format jpg --dpi 300
  %(prog)s --skip-existing        # Skip already converted PDFs
  %(prog)s --workers 4 --verbose  # Use 4 workers with detailed output
  %(prog)s -w 8 --format jpg      # Use 8 parallel workers for JPG conversion
        """
    )
    
    parser.add_argument(
        '-s', '--source',
        type=str,
        default='./pdfs',
        help='Source folder containing PDF files (default: ./pdfs)'
    )
    
    parser.add_argument(
        '-d', '--destination',
        type=str,
        default='./output',
        help='Destination folder for output images (default: ./output)'
    )
    
    parser.add_argument(
        '-f', '--format',
        type=str,
        default='png',
        choices=['png', 'jpg', 'jpeg', 'tiff', 'bmp'],
        help='Output image format (default: png)'
    )
    
    parser.add_argument(
        '--dpi',
        type=int,
        default=200,
        help='DPI for image conversion (default: 200, higher = better quality but larger files)'
    )
    
    parser.add_argument(
        '--skip-existing',
        action='store_true',
        help='Skip PDFs that already have converted images'
    )
    
    parser.add_argument(
        '-w', '--workers',
        type=int,
        default=None,
        help='Number of parallel workers (default: auto-detect based on CPU cores)'
    )
    
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Show detailed progress information'
    )
    
    args = parser.parse_args()
    
    # Process all PDFs
    success = process_all_pdfs(
        args.source,
        args.destination,
        args.format,
        args.dpi,
        args.skip_existing,
        args.workers,
        args.verbose
    )
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()