import requests
import os
from bs4 import BeautifulSoup
import re
from urllib.parse import urljoin, unquote
import time
import random
import csv
from datetime import datetime

# Configuration for different exam boards and paper types
# This makes it easy to extend to other boards/levels later
CONFIGS = {
    "edexcel_alevel": {
        "name": "Edexcel A-Level",
        "base_url": "https://www.physicsandmathstutor.com/maths-revision/a-level-edexcel/papers/",
        "paper_sections": [
            {
                "name": "Paper 1 - Pure",
                "identifier": "paper-1-pure",
                "content_types": ["QP", "MS"]  # QP = Question Papers, MS = Mark Schemes
            },
            {
                "name": "Paper 2 - Pure",
                "identifier": "paper-2-pure",
                "content_types": ["QP", "MS"]
            },
            {
                "name": "Paper 3 - Statistics & Mechanics",
                "identifier": "paper-3-statistics-mechanics",
                "content_types": ["QP", "MS"],
                "subtypes": ["Mechanics", "Statistics"]  # Paper 3 has two different sections
            }
        ]
    }
    # Structure allows easy extension for other exam boards/levels:
    # "aqa_alevel": { ... similar structure ... }
    # "edexcel_gcse": { ... similar structure ... }
}

def create_folder_structure(base_path, config_key):
    """
    Create an organized folder structure based on configuration.
    
    Args:
        base_path: Root directory where papers will be stored
        config_key: Key to the configuration dictionary (e.g., 'edexcel_alevel')
    """
    config = CONFIGS[config_key]

    # Extract exam board and level from config key
    parts = config_key.split("_")
    board = parts[0]  # e.g., 'edexcel'
    level = parts[1]  # e.g., 'alevel'

    # Create folders for each paper type and content type
    for section in config["paper_sections"]:
        # Extract paper number from section name (e.g., "Paper 1 - Pure" -> "paper 1")
        paper_number = re.search(r'Paper (\d+)', section["name"]).group(0).lower()
        
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

def extract_metadata_from_link(href, link_text, config_key, section):
    """
    Extract metadata from link href and text.
    
    Args:
        href: The URL of the link
        link_text: The visible text of the link
        config_key: Key to the configuration dictionary
        section: The section configuration for this paper type
        
    Returns:
        Dictionary containing all extracted metadata
    """
    metadata = {
        'exam_board': config_key.split('_')[0],
        'level': config_key.split('_')[1],
        'paper_type': section["name"],
        'content_type': None,
        'year': None,
        'month': None,
        'subtype': None
    }

    # Extract content type (QP/MS)
    if "QP" in link_text:
        metadata['content_type'] = "QP"
    elif "MS" in link_text:
        metadata['content_type'] = "MS"

    # Extract year using regex
    year_match = re.search(r'20(\d{2})', link_text)
    if year_match:
        metadata['year'] = f"20{year_match.group(1)}"

    # Extract month using regex
    month_match = re.search(r'(June|October|January|November)', link_text)
    if month_match:
        metadata['month'] = month_match.group(1)

    # Extract subtype for Paper 3 (Mechanics or Statistics)
    if "subtypes" in section:
        for subtype in section["subtypes"]:
            if subtype in link_text or f"({subtype[:4]})" in link_text:
                metadata['subtype'] = subtype
                break

    return metadata

def scrape_pmt_papers(base_path, csv_path, config_key="edexcel_alevel"):
    """
    Main function to scrape PMT website based on configuration.
    
    Args:
        base_path: Root directory where papers will be stored
        csv_path: Path where the CSV file will be created
        config_key: Key to the configuration dictionary
    """
    config = CONFIGS[config_key]

    # Create folders
    create_folder_structure(base_path, config_key)

    # Initialize tracking CSV
    initialize_tracking_csv(csv_path)

    # Set up headers for the request to mimic a real browser
    # This helps prevent the request from being blocked
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Referer': 'https://www.physicsandmathstutor.com/'
    }

    # Get the main page
    print(f"Fetching main page: {config['base_url']}")
    response = requests.get(config['base_url'], headers=headers)
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # Find all paper links (QP and MS) by checking link text and href
    paper_links = []
    for link in soup.find_all('a', href=True):
        # Only interested in links with QP or MS in the text and Paper in the URL
        if ("QP" in link.text or "MS" in link.text) and "Paper" in link['href']:
            paper_links.append((link['href'], link.text.strip()))
    
    print(f"Found {len(paper_links)} paper links")
    
    # Process each link
    for i, (href, link_text) in enumerate(paper_links):
        # Add delay to be respectful to the server (avoid getting blocked)
        time.sleep(random.uniform(1, 3))
        
        # Determine paper number from URL using regex
        paper_match = re.search(r'Paper-(\d+)', href)
        if not paper_match:
            print(f"Skipping {link_text} - Cannot determine paper number")
            continue
            
        paper_number = paper_match.group(0).lower().replace('-', ' ')  # "paper 1", "paper 2", etc.
        
        # Determine content type from link text
        if "QP" in link_text:
            content_type = "qp"
        elif "MS" in link_text:
            content_type = "ms"
        else:
            print(f"Skipping {link_text} - Unknown content type")
            continue
            
        # Extract metadata for CSV tracking
        metadata = {
            'exam_board': config_key.split('_')[0],
            'level': config_key.split('_')[1],
            'paper_type': f"Paper {paper_match.group(1)}",
            'content_type': content_type.upper(),
            'year': None,
            'month': None,
            'subtype': None
        }
        
        # Extract year and month from link text
        year_match = re.search(r'20(\d{2})', link_text)
        if year_match:
            metadata['year'] = f"20{year_match.group(1)}"
            
        month_match = re.search(r'(June|October|January|November)', link_text)
        if month_match:
            metadata['month'] = month_match.group(1)
            
        # Extract subtype for Paper 3 (Mechanics or Statistics)
        mech_match = re.search(r'\(Mech\)', link_text)
        stats_match = re.search(r'\(Stats\)', link_text)
        if mech_match:
            metadata['subtype'] = "Mechanics"
        elif stats_match:
            metadata['subtype'] = "Statistics"
            
        # Determine filename from the URL
        filename = os.path.basename(href)
        
        # Build the folder path according to our structure
        folder_components = [
            base_path,
            metadata['level'],
            metadata['exam_board'],
            paper_number,
            content_type
        ]
        
        save_folder = os.path.join(*folder_components)
        save_path = os.path.join(save_folder, filename)
        
        # Download the file
        try:
            print(f"[{i+1}/{len(paper_links)}] Downloading: {filename}")
            
            # Get the full URL for download
            download_url = href
            
            response = requests.get(download_url, headers=headers)
            
            if response.status_code == 200:
                # Save the file to disk
                with open(save_path, 'wb') as f:
                    f.write(response.content)
                print(f"  ✓ Saved to {save_path}")
                
                # Add to tracking CSV
                add_to_tracking_csv(csv_path, metadata, filename, save_path)
                
                # Print metadata
                print(f"  Metadata - Year: {metadata.get('year', 'Unknown')}, Month: {metadata.get('month', 'Unknown')}, Paper: {metadata['paper_type']}")
            else:
                print(f"  ✗ Failed to download (Status code: {response.status_code})")
                
        except Exception as e:
            print(f"  ✗ Error downloading {filename}: {e}")

def main():
    # Base directory for storing papers
    base_path = "/Users/admin/Documents/Test Papers"
    
    # Path for the CSV file that tracks downloaded papers
    csv_path = os.path.join(base_path, "downloaded_papers.csv")

    # For now, just scrape Edexcel A-level
    scrape_pmt_papers(base_path, csv_path, "edexcel_alevel")

    # In the future, you could easily add more configurations and scrape them:
    # if "aqa_alevel" in CONFIGS:
    #     scrape_pmt_papers(base_path, csv_path, "aqa_alevel")
    # if "edexcel_gcse" in CONFIGS:
    #     scrape_pmt_papers(base_path, csv_path, "edexcel_gcse")

    print(f"\nDownload complete. Paper information saved to {csv_path}")

if __name__ == "__main__":
    main()
