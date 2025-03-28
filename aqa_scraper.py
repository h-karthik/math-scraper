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
    "aqa_alevel": {
        "name": "AQA A-Level",
        "base_url": "https://www.physicsandmathstutor.com/maths-revision/a-level-aqa/papers/",
        "paper_sections": [
            {
                "name": "Paper 1 - Pure",
                "identifier": "paper-1-pure",
                "content_types": ["QP", "MS"]  # QP = Question Papers, MS = Mark Schemes
            },
            {
                "name": "Paper 2 - Pure and Mechanics",
                "identifier": "paper-2-pure-mechanics",
                "content_types": ["QP", "MS"]
            },
            {
                "name": "Paper 3 - Pure and Statistics",
                "identifier": "paper-3-pure-statistics",
                "content_types": ["QP", "MS"]
            }
        ]
    }
    # Structure allows easy extension for other exam boards/levels:
    # "edexcel_gcse": { ... similar structure ... }
}

def create_folder_structure(base_path, config_key):
    """
    Create an organized folder structure based on configuration.
    
    Args:
        base_path: Root directory where papers will be stored
        config_key: Key to the configuration dictionary (e.g., 'aqa_alevel')
    """
    config = CONFIGS[config_key]

    # Extract exam board and level from config key
    parts = config_key.split("_")
    board = parts[0]  # e.g., 'aqa'
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

def scrape_pmt_papers(base_path, csv_path, config_key="aqa_alevel"):
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

    # Initialize tracking CSV if it doesn't exist
    if not os.path.exists(csv_path):
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
        # Only interested in links with QP or MS in the text and Paper in the URL or href path
        if (("QP" in link.text or "MS" in link.text) and 
            ("Paper" in link['href'] or "paper" in link['href'].lower())):
            paper_links.append((link['href'], link.text.strip()))
    
    print(f"Found {len(paper_links)} paper links")
    
    # Process each link
    for i, (href, link_text) in enumerate(paper_links):
        # Add delay to be respectful to the server (avoid getting blocked)
        time.sleep(random.uniform(1, 3))
        
        # Check if URL is a direct PDF or a redirect page
        if "pdf-pages" in href:
            # Extract the actual PDF URL from the redirect page URL
            pdf_url_param = href.split("?pdf=")[1]
            actual_pdf_url = unquote(pdf_url_param)
            href = actual_pdf_url
            
        # Determine paper number from URL using regex
        paper_match = re.search(r'Paper-(\d+)', href)
        if not paper_match:
            print(f"Skipping {link_text} - Cannot determine paper number")
            continue
            
        paper_number = paper_match.group(0).lower().replace('-', ' ')  # "paper 1", "paper 2", etc.
        
        # Determine content type from link text
        if "QP" in link_text:
            content_type = "qp"
            display_type = "question papers"
        elif "MS" in link_text:
            content_type = "ms"
            display_type = "mark schemes"
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
                print(f"  Metadata - Year: {metadata.get('year', 'Unknown')}, Month: {metadata.get('month', 'Unknown')}, Paper: {metadata['paper_type']}, Type: {display_type}")
            else:
                print(f"  ✗ Failed to download (Status code: {response.status_code})")
                
        except Exception as e:
            print(f"  ✗ Error downloading {filename}: {e}")

def main():
    # Base directory for storing papers
    base_path = "/Users/admin/Documents/Test Papers"
    
    # Path for the CSV file that tracks downloaded papers
    csv_path = os.path.join(base_path, "downloaded_papers.csv")

    # Scrape AQA A-level papers
    scrape_pmt_papers(base_path, csv_path, "aqa_alevel")

    print(f"\nDownload complete. Paper information saved to {csv_path}")

if __name__ == "__main__":
    main()
