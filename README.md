# PDF to Image Folder Converter

A Python script that converts PDF files into organized image folders. Each PDF is converted to a folder containing individual page images.

## Features

- 📁 Batch convert multiple PDFs at once
- 🖼️ Each PDF gets its own folder with page images
- 🎨 Multiple image formats supported (PNG, JPG, TIFF, BMP)
- 🔧 Adjustable image quality (DPI settings)
- ⏭️ Skip already converted PDFs
- 📊 Progress tracking for each conversion

## Prerequisites

### System Requirements
- Python 3.6 or higher
- Poppler utilities for PDF rendering

### Install Poppler

**macOS (using Homebrew):**
```bash
brew install poppler
```

**Ubuntu/Debian:**
```bash
sudo apt-get install poppler-utils
```

**Windows:**
Download from [Poppler for Windows](https://github.com/oschwartz10612/poppler-windows/releases/)

## Installation

1. Clone or download this repository
2. Install Python dependencies:
```bash
pip3 install -r requirements.txt
```

## Folder Structure

The script comes with default folders:
- **`pdfs/`** - Default source folder (place your PDF files here)
- **`output/`** - Default destination folder (converted images will be saved here)

## Usage

### Basic Usage
Using default folders (./pdfs → ./output):
```bash
python3 main.py
```

Or specify custom folders:
```bash
python3 main.py --source ./my_pdfs --destination ./my_images
```

### Command Line Options

| Option | Short | Description | Default |
|--------|-------|-------------|---------|
| `--source` | `-s` | Source folder containing PDF files | ./pdfs |
| `--destination` | `-d` | Destination folder for output images | ./output |
| `--format` | `-f` | Output image format (png, jpg, jpeg, tiff, bmp) | png |
| `--dpi` | | Image quality in DPI | 200 |
| `--skip-existing` | | Skip PDFs that already have converted images | False |

### Examples

**Simplest usage (uses default folders):**
```bash
# Place PDFs in ./pdfs folder, then run:
python3 main.py
```

**High quality JPEG conversion:**
```bash
python3 main.py --format jpg --dpi 300
```

**Custom folders with specific format:**
```bash
python3 main.py -s ./documents -d ./images --format jpg --dpi 300
```

**Skip already converted PDFs:**
```bash
python3 main.py --skip-existing
```

## Output Structure

For each PDF file, the script creates a folder with the same name:

```
destination_folder/
├── document1/
│   ├── page_0001.png
│   ├── page_0002.png
│   └── page_0003.png
├── document2/
│   ├── page_0001.png
│   └── page_0002.png
└── report/
    ├── page_0001.png
    ├── page_0002.png
    ├── page_0003.png
    └── page_0004.png
```

## DPI Guidelines

- **72 DPI**: Screen viewing only (smallest file size)
- **150 DPI**: Good for most purposes
- **200 DPI**: Default, good quality for viewing and printing
- **300 DPI**: High quality for professional printing
- **600 DPI**: Maximum quality (large file sizes)

## Troubleshooting

### "poppler-utils not installed" Error
Make sure you've installed Poppler for your operating system (see Prerequisites section).

### Permission Errors
Ensure you have read permissions for the source folder and write permissions for the destination folder.

### Memory Issues with Large PDFs
For very large PDFs, consider:
- Processing fewer PDFs at once
- Reducing DPI setting
- Ensuring adequate system memory

## License

MIT License - Feel free to use and modify as needed.