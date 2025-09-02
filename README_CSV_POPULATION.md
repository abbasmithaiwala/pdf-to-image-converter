# CSV Population Script with Cloudinary CDN

This script extracts product details from PDF output folders and populates a CSV file with product data, including CDN URLs for product images via Cloudinary.

## Features

- **Automatic Product Info Extraction**: Extracts product name and cost price from folder names
- **Cloudinary Integration**: Uploads images to Cloudinary CDN and generates optimized URLs
- **Smart Image Selection**: Automatically skips the last 2 images in each folder
- **CSV Population**: Updates existing CSV or creates new one with product data
- **Error Handling**: Comprehensive logging and error recovery
- **Flexible Configuration**: Customizable paths and settings

## Setup

### 1. Install Dependencies

```bash
pip install cloudinary pandas python-dotenv
```

### 2. Create Cloudinary Account

1. Sign up for a free account at [Cloudinary](https://cloudinary.com/)
2. Go to your Dashboard to get your credentials:
   - Cloud Name
   - API Key
   - API Secret

### 3. Configure Environment

Copy the environment template and fill in your credentials:

```bash
cp .env.example .env
```

Edit `.env` file:
```
CLOUDINARY_CLOUD_NAME=your_cloud_name_here
CLOUDINARY_API_KEY=your_api_key_here
CLOUDINARY_API_SECRET=your_api_secret_here
CLOUDINARY_UPLOAD_FOLDER=product_images
```

## Usage

### Basic Usage
```bash
python populate_csv.py
```

This will:
- Process all folders in `./output/`
- Upload images to Cloudinary
- Update `./test_upload.csv` with product data

### Custom Paths
```bash
python populate_csv.py -o /path/to/output -c /path/to/products.csv
```

### Test Parsing (No Upload)
```bash
python test_parsing.py
```

## How It Works

### 1. Folder Name Parsing
From folder names like `RS=1025.00 - RDD-MELLISA (CHIFFON)`:
- **Cost Price**: `1025.00` (between `RS=` and first `-`)
- **Product Name**: `RDD-MELLISA (CHIFFON)` (everything after first `- `)

### 2. Image Processing
For each folder:
- Lists all `.png` files
- Skips the last 2 images
- Uploads remaining images to Cloudinary (max 8 for media fields)
- Generates CDN URLs

### 3. CSV Population
Creates/updates CSV with columns:
- `name`: Product name from folder
- `cost_price`: Extracted cost price
- `media_1` through `media_8`: Cloudinary CDN URLs
- Other fields: Set to defaults or left empty

## CSV Structure

The script populates these columns:
```
name,description,bulk_price,media_1,media_2,media_3,media_4,media_5,media_6,media_7,media_8,preferred_supplier,cost_price,mrp,uom,set_size,moq,available_quantity
```

## Cloudinary URLs

Images are organized in Cloudinary as:
```
https://res.cloudinary.com/{cloud_name}/image/upload/product_images/{folder_name}/{image_name}
```

## Logging

The script creates detailed logs in:
- `csv_population.log` (file)
- Console output

## Error Handling

- Invalid folder names: Uses folder name as product name
- Upload failures: Logged but processing continues
- Missing credentials: Script stops with clear error message
- Empty folders: Skipped with warning

## Cloudinary Free Tier

- **Storage**: 25GB
- **Bandwidth**: 25GB/month  
- **Transformations**: 25,000/month

Perfect for most small to medium product catalogs.

## Examples

### Successful Processing
```
2025-01-15 10:30:15 - INFO - Processing folder: RS=1025.00 - RDD-MELLISA (CHIFFON)
2025-01-15 10:30:16 - INFO -   Uploading image 1/8: page_0001.png
2025-01-15 10:30:17 - INFO -   Uploading image 2/8: page_0002.png
...
2025-01-15 10:30:25 - INFO -   Processed 8 images for 'RDD-MELLISA (CHIFFON)'
```

### Generated CSV Entry
```csv
RDD-MELLISA (CHIFFON),Product from RDD-MELLISA (CHIFFON),,https://res.cloudinary.com/.../page_0001,https://res.cloudinary.com/.../page_0002,...,1025.00,pcs,,,
```

## Troubleshooting

**Missing credentials error**: Copy `.env.example` to `.env` and add your Cloudinary credentials

**Upload failures**: Check internet connection and Cloudinary quota

**Empty CSV**: Verify output folder path and folder name format

**Permission errors**: Ensure script has write permissions for CSV file