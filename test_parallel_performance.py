#!/usr/bin/env python3

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from populate_csv_parallel import (
    parse_folder_name, get_image_files, 
    process_folder_parallel, PerformanceMonitor
)
from pathlib import Path
import time

def test_parsing_performance():
    """Test folder name parsing performance with caching."""
    test_cases = [
        "RS=1025.00 - RDD-MELLISA (CHIFFON)",
        "RS=255.00 - TP-BANDHAN (RENIYAL)",
        "RS=1345.00 - RDD-VERONICA VOL-14 (30-30 BRASSO)",
        "RS=250.00 - CAS-LEMON SILK (ZOMATO)"
    ] * 250  # 1000 total calls
    
    print("Testing cached parsing performance:")
    print("-" * 50)
    
    start_time = time.time()
    results = []
    for folder_name in test_cases:
        name, cost = parse_folder_name(folder_name)
        results.append((name, cost))
    
    elapsed = time.time() - start_time
    
    print(f"Parsed {len(test_cases)} folder names in {elapsed:.4f}s")
    print(f"Rate: {len(test_cases)/elapsed:.0f} parses/second")
    print(f"Cache efficiency: {parse_folder_name.cache_info()}")
    print()

def test_folder_structure():
    """Test folder structure and image detection."""
    output_path = Path("./output")
    
    if not output_path.exists():
        print("Output folder not found - skipping folder structure test")
        return
    
    folders = [d for d in output_path.iterdir() if d.is_dir()]
    print(f"Folder Structure Analysis:")
    print("-" * 50)
    print(f"Total folders: {len(folders)}")
    
    # Analyze first 5 folders
    for i, folder in enumerate(folders[:5]):
        image_files = get_image_files(folder, skip_last=2)
        print(f"{i+1}. {folder.name[:50]}...")
        print(f"   Images available: {len(image_files)}")
    
    print()

def simulate_parallel_processing():
    """Simulate parallel processing performance."""
    print("Simulating Parallel Processing Performance:")
    print("-" * 50)
    
    # Different worker configurations
    configs = [
        (1, 1, "Sequential"),
        (5, 3, "Conservative"),
        (10, 5, "Default"),
        (20, 10, "High Performance")
    ]
    
    # Simulate processing 100 folders with 8 images each
    folders = 100
    images_per_folder = 8
    total_images = folders * images_per_folder
    
    # Estimated upload time per image (seconds)
    base_upload_time = 2.0
    
    for folder_workers, image_workers, config_name in configs:
        # Calculate theoretical processing time
        # Time for uploading images in parallel within each folder
        time_per_folder = (images_per_folder * base_upload_time) / image_workers
        
        # Time for processing all folders in parallel
        total_time = (folders * time_per_folder) / folder_workers
        
        # Add some overhead for coordination
        overhead = total_time * 0.1
        estimated_time = total_time + overhead
        
        throughput = total_images / estimated_time
        
        print(f"{config_name:15} ({folder_workers:2d}f, {image_workers:2d}i): "
              f"{estimated_time:6.1f}s, {throughput:6.1f} images/sec")
    
    print()
    print("f = folder workers, i = image workers per folder")
    print()

def test_performance_monitor():
    """Test performance monitoring functionality."""
    print("Testing Performance Monitor:")
    print("-" * 50)
    
    monitor = PerformanceMonitor()
    
    # Simulate some processing
    for i in range(10):
        monitor.update_folder(1)
        monitor.update_images(8, 1.5)  # 8 images, 1.5s average upload time
        time.sleep(0.1)  # Small delay to show elapsed time
    
    stats = monitor.get_stats()
    
    print(f"Folders Processed: {stats['folders_processed']}")
    print(f"Images Processed: {stats['images_processed']}")
    print(f"Elapsed Time: {stats['elapsed_time']:.2f}s")
    print(f"Images per Second: {stats['images_per_second']:.1f}")
    print(f"Average Upload Time: {stats['avg_upload_time']:.2f}s")
    print(f"CPU Usage: {stats['cpu_percent']:.1f}%")
    print(f"Memory Usage: {stats['memory_percent']:.1f}%")
    print()

def main():
    print("Parallel Processing Performance Test")
    print("=" * 60)
    print()
    
    test_parsing_performance()
    test_folder_structure()
    simulate_parallel_processing()
    test_performance_monitor()
    
    print("Recommendations:")
    print("- For fast machines: --max-folder-workers 15-20, --max-image-workers 8-10")
    print("- For slow machines: --max-folder-workers 5-8, --max-image-workers 3-5")
    print("- Monitor CPU/memory usage and adjust accordingly")
    print("- Cloudinary rate limits may require lower worker counts")

if __name__ == "__main__":
    main()