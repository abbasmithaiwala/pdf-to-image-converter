#!/usr/bin/env python3

import os
import argparse
from pathlib import Path
from pdf2image import convert_from_path
from pdf2image.exceptions import PDFInfoNotInstalledError, PDFPageCountError, PDFSyntaxError
import sys


def create_output_folder(pdf_path, destination_base):
    """Create output folder for a PDF file."""
    pdf_name = Path(pdf_path).stem
    output_folder = Path(destination_base) / pdf_name
    output_folder.mkdir(parents=True, exist_ok=True)
    return output_folder


def convert_pdf_to_images(pdf_path, output_folder, image_format='png', dpi=200, skip_existing=False):
    """Convert a single PDF to images and save them in the output folder."""
    try:
        pdf_name = Path(pdf_path).name
        
        # Check if folder already has images and skip if requested
        if skip_existing and output_folder.exists():
            existing_images = list(output_folder.glob(f'*.{image_format}'))
            if existing_images:
                print(f"  Skipping {pdf_name} - images already exist")
                return True
        
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
            print(f"    Saved page {i}/{len(images)}")
        
        print(f"   Completed {pdf_name}: {len(images)} pages")
        return True
        
    except PDFInfoNotInstalledError:
        print(f"   Error: poppler-utils not installed. Please install it:")
        print(f"    macOS: brew install poppler")
        print(f"    Ubuntu/Debian: sudo apt-get install poppler-utils")
        print(f"    Windows: Download from https://github.com/oschwartz10612/poppler-windows/releases/")
        return False
    except PDFPageCountError:
        print(f"   Error: Unable to get page count for {pdf_name}")
        return False
    except PDFSyntaxError:
        print(f"   Error: PDF syntax error in {pdf_name}")
        return False
    except Exception as e:
        print(f"   Error processing {pdf_name}: {str(e)}")
        return False


def process_all_pdfs(source_folder, destination_folder, image_format='png', dpi=200, skip_existing=False):
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
    
    print(f"Found {len(pdf_files)} PDF file(s) to process")
    print(f"Source: {source_folder}")
    print(f"Destination: {destination_folder}")
    print(f"Settings: Format={image_format.upper()}, DPI={dpi}")
    print("-" * 50)
    
    successful = 0
    failed = 0
    
    for pdf_path in pdf_files:
        output_folder = create_output_folder(pdf_path, dest_path)
        if convert_pdf_to_images(pdf_path, output_folder, image_format, dpi, skip_existing):
            successful += 1
        else:
            failed += 1
    
    print("-" * 50)
    print(f"Processing complete: {successful} successful, {failed} failed")
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
    
    args = parser.parse_args()
    
    # Process all PDFs
    success = process_all_pdfs(
        args.source,
        args.destination,
        args.format,
        args.dpi,
        args.skip_existing
    )
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()