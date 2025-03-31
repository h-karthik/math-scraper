#!/usr/bin/env python3
"""
Math Paper Scraper - A unified tool to download past papers from Physics & Maths Tutor

This script combines functionality from separate OCR, OCR MEI, AQA, and Edexcel scrapers
into a single, configurable tool.
"""

import os
import argparse
from config import CONFIGS, DEFAULT_BASE_PATH, DEFAULT_CSV_NAME
from scrapers import scrape_papers

def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description="Download math papers from Physics & Maths Tutor")
    
    parser.add_argument('--board', type=str, default='all',
                        help='Exam boards to scrape (comma-separated, or "all")')
    
    parser.add_argument('--output', type=str, default=DEFAULT_BASE_PATH,
                        help=f'Output directory (default: {DEFAULT_BASE_PATH})')
    
    parser.add_argument('--dry-run', action='store_true',
                        help='Perform a dry run (no downloads)')
    
    return parser.parse_args()

def main():
    """Main entry point"""
    args = parse_args()
    
    # Determine which boards to scrape
    if args.board.lower() == 'all':
        boards = list(CONFIGS.keys())
    else:
        boards = [board.strip() for board in args.board.split(',')]
        # Validate requested boards
        for board in boards:
            if board not in CONFIGS:
                print(f"Error: Unknown board '{board}'. Available boards: {', '.join(CONFIGS.keys())}")
                return
    
    # Create base directory if it doesn't exist
    os.makedirs(args.output, exist_ok=True)
    
    # Path for the CSV tracking file
    csv_path = os.path.join(args.output, DEFAULT_CSV_NAME)
    
    # Track total downloads
    total_downloads = 0
    
    # Scrape each board
    for board in boards:
        print(f"\n{'=' * 60}")
        print(f"Scraping {CONFIGS[board]['name']} papers")
        print(f"{'=' * 60}")
        
        try:
            downloads = scrape_papers(args.output, csv_path, board, args.dry_run)
            total_downloads += downloads
            print(f"Completed scraping {CONFIGS[board]['name']} - {downloads} papers downloaded")
        except Exception as e:
            print(f"Error scraping {CONFIGS[board]['name']}: {e}")
    
    if args.dry_run:
        print(f"\nDry run completed. No files were downloaded.")
    else:
        print(f"\nAll scraping completed. {total_downloads} papers downloaded.")
        print(f"Download information saved to {csv_path}")

if __name__ == "__main__":
    main() 