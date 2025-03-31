import os
import re
import csv
from datetime import datetime
from config import CONFIGS

def create_folder_structure(base_path, config_key):
    """
    Create an organized folder structure based on configuration.
    
    Args:
        base_path: Root directory where papers will be stored
        config_key: Key to the configuration dictionary (e.g., 'ocr_alevel')
    """
    config = CONFIGS[config_key]

    # Extract exam board and level from config key
    parts = config_key.split("_")
    if config_key == "ocr_mei_alevel":
        board = "ocr-mei"  # Special case for OCR MEI
        level = "alevel"
    else:
        board = parts[0]  # e.g., 'ocr', 'aqa', 'edexcel'
        level = parts[1]  # e.g., 'alevel'

    # Create folders for each paper type and content type
    for section in config["paper_sections"]:
        # Extract paper number from section name
        if "Component" in section["name"]:
            # OCR MEI case
            paper_match = re.search(r'Component (\d+)', section["name"])
            paper_number = f"paper {paper_match.group(1)}"
        else:
            # Standard case
            paper_match = re.search(r'Paper (\d+)', section["name"])
            paper_number = paper_match.group(0).lower()
        
        # Create folders for question papers and mark schemes
        for content_type in section["content_types"]:
            folder_path = os.path.join(
                base_path, 
                level,
                board,
                paper_number,
                content_type.lower()  # "qp" or "ms"
            )
            # Create the directory if it doesn't exist
            os.makedirs(folder_path, exist_ok=True)

    print(f"Created folder structure for {config['name']}")

def initialize_tracking_csv(csv_path):
    """
    Create or clear the CSV file for tracking downloaded papers.
    
    Args:
        csv_path: Path where the CSV file will be created
    """
    with open(csv_path, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        # Create header row with all the metadata fields
        writer.writerow([
            'filename', 'exam_board', 'level', 'paper_type', 'subtype',
            'content_type', 'year', 'month', 'file_path', 'download_date'
        ])

def add_to_tracking_csv(csv_path, metadata, filename, file_path):
    """
    Add downloaded file information to tracking CSV.
    
    Args:
        csv_path: Path to the CSV file
        metadata: Dictionary containing paper metadata
        filename: Name of the downloaded file
        file_path: Full path where the file was saved
    """
    with open(csv_path, 'a', newline='') as csvfile:
        writer = csv.writer(csvfile)
        # Add a new row with all the metadata for this paper
        writer.writerow([
            filename,
            metadata['exam_board'],
            metadata['level'],
            metadata['paper_type'],
            metadata.get('subtype', ''),  # May not exist for all papers
            metadata['content_type'],
            metadata['year'],
            metadata.get('month', ''),    # May not be extracted
            file_path,
            datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        ])

def get_request_headers():
    """Return headers for HTTP requests to prevent blocking"""
    return {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Referer': 'https://www.physicsandmathstutor.com/'
    } 