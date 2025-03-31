import re
import os
import time
import random
import requests
from urllib.parse import unquote
from bs4 import BeautifulSoup

from config import CONFIGS
from utils import create_folder_structure, initialize_tracking_csv, add_to_tracking_csv, get_request_headers

def determine_paper_number(href, link_text, config_key):
    """
    Determine paper number based on exam board specific patterns
    
    Args:
        href: URL of the paper
        link_text: Text of the link
        config_key: Key in the CONFIGS dictionary
    
    Returns:
        Tuple of (paper_number, paper_display_name)
    """
    paper_number = None
    paper_display_name = None
    
    if config_key == "ocr_alevel":
        # OCR A-Level uses "Component" in text or URL
        component_match = re.search(r'Component (\d+)', link_text)
        if component_match:
            number = component_match.group(1)
            paper_number = f"paper {number}"
            paper_display_name = f"Paper {number}"
        else:
            # Try to find in URL
            url_match = re.search(r'component-(\d+)', href.lower())
            if url_match:
                number = url_match.group(1)
                paper_number = f"paper {number}"
                paper_display_name = f"Paper {number}"
            # Content-based inference
            elif "pure-mathematics" in href.lower() and "statistics" not in href.lower() and "mechanics" not in href.lower():
                paper_number = "paper 1"
                paper_display_name = "Paper 1"
            elif "statistics" in href.lower() or "stats" in href.lower():
                paper_number = "paper 2"
                paper_display_name = "Paper 2"
            elif "mechanics" in href.lower() or "mech" in href.lower():
                paper_number = "paper 3"
                paper_display_name = "Paper 3"
    
    elif config_key == "ocr_mei_alevel":
        # OCR MEI A-Level also uses "Component" in text or URL
        component_match = re.search(r'Component (\d+)', link_text)
        if component_match:
            number = component_match.group(1)
            paper_number = f"paper {number}"
            paper_display_name = f"Paper {number}"
        else:
            # Try to find in URL
            url_match = re.search(r'Paper-(\d+)', href)
            if url_match:
                number = url_match.group(1)
                paper_number = f"paper {number}"
                paper_display_name = f"Paper {number}"
            # Content-based inference
            elif "mechanics" in href.lower() or "mech" in href.lower() or "component-1" in href.lower():
                paper_number = "paper 1"
                paper_display_name = "Paper 1"
            elif "statistics" in href.lower() or "stats" in href.lower() or "component-2" in href.lower():
                paper_number = "paper 2"
                paper_display_name = "Paper 2"
            elif "comprehension" in href.lower() or "comp" in href.lower() or "component-3" in href.lower():
                paper_number = "paper 3"
                paper_display_name = "Paper 3"
    
    elif config_key == "aqa_alevel" or config_key == "edexcel_alevel":
        # AQA and Edexcel use "Paper-X" in URL
        paper_match = re.search(r'Paper-(\d+)', href)
        if paper_match:
            paper_number = paper_match.group(0).lower().replace('-', ' ')
            paper_display_name = f"Paper {paper_match.group(1)}"
    
    return paper_number, paper_display_name

def extract_metadata(href, link_text, config_key, paper_number, paper_display_name):
    """
    Extract metadata based on exam board specific patterns
    
    Args:
        href: URL of the paper
        link_text: Text of the link
        config_key: Key in the CONFIGS dictionary
        paper_number: Paper number (e.g., "paper 1")
        paper_display_name: Display name (e.g., "Paper 1")
    
    Returns:
        Dictionary with metadata
    """
    metadata = {
        'paper_type': paper_display_name,
        'year': None,
        'month': None,
        'subtype': None,
        'content_type': None
    }
    
    # Set exam board and level
    if config_key == "ocr_mei_alevel":
        metadata['exam_board'] = "ocr-mei"
        metadata['level'] = "alevel"
    else:
        metadata['exam_board'] = config_key.split('_')[0]
        metadata['level'] = config_key.split('_')[1]
    
    # Determine content type from link text
    if "QP" in link_text:
        metadata['content_type'] = "QP"
    elif "MS" in link_text:
        metadata['content_type'] = "MS"
    
    # Extract year and month
    year_match = re.search(r'20(\d{2})', link_text)
    if year_match:
        metadata['year'] = f"20{year_match.group(1)}"
        
    month_match = re.search(r'(June|October|January|November|Nov)', link_text)
    if month_match:
        month = month_match.group(1)
        # Standardize month name
        if month == "Nov":
            month = "November"
        metadata['month'] = month
    
    # Extract subtype for Edexcel Paper 3
    if config_key == "edexcel_alevel" and "paper 3" in paper_number:
        if "Mech" in link_text or "mech" in link_text.lower():
            metadata['subtype'] = "Mechanics"
        elif "Stat" in link_text or "stat" in link_text.lower():
            metadata['subtype'] = "Statistics"
    
    return metadata

def scrape_papers(base_path, csv_path, config_key, dry_run=False):
    """
    Scrape papers for a specific exam board
    
    Args:
        base_path: Base path to save papers
        csv_path: Path to the CSV tracking file
        config_key: Key in the CONFIGS dictionary
        dry_run: If True, don't actually download files
    
    Returns:
        Number of papers downloaded
    """
    config = CONFIGS[config_key]
    
    # Setup folders and CSV
    create_folder_structure(base_path, config_key)
    if not os.path.exists(csv_path):
        initialize_tracking_csv(csv_path)
    
    # HTTP request headers
    headers = get_request_headers()
    
    # Fetch main page
    print(f"Fetching main page: {config['base_url']}")
    response = requests.get(config['base_url'], headers=headers)
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # Find links (different logic per board)
    paper_links = []
    for link in soup.find_all('a', href=True):
        if config_key == "aqa_alevel":
            # AQA - papers have "QP" or "MS" in text and "Paper" in href
            if (("QP" in link.text or "MS" in link.text) and 
                ("Paper" in link['href'] or "paper" in link['href'].lower())):
                paper_links.append((link['href'], link.text.strip()))
        else:
            # OCR, OCR MEI, Edexcel - papers have "QP" or "MS" in text
            if ("QP" in link.text or "MS" in link.text):
                paper_links.append((link['href'], link.text.strip()))
    
    print(f"Found {len(paper_links)} paper links")
    
    # Process each link
    downloads_count = 0
    for i, (href, link_text) in enumerate(paper_links):
        # Add delay to be respectful to the server
        time.sleep(random.uniform(1, 3))
        
        # Check if URL is a direct PDF or a redirect page
        if "pdf-pages" in href:
            # Extract the actual PDF URL from the redirect page URL
            pdf_url_param = href.split("?pdf=")[1]
            actual_pdf_url = unquote(pdf_url_param)
            href = actual_pdf_url
            
        # Determine paper number and display name
        paper_number, paper_display_name = determine_paper_number(href, link_text, config_key)
        if not paper_number:
            print(f"Skipping {link_text} - Cannot determine paper number")
            continue
        
        # Determine content type and display type
        content_type = None
        display_type = None
        if "QP" in link_text:
            content_type = "qp"
            display_type = "question papers"
        elif "MS" in link_text:
            content_type = "ms"
            display_type = "mark schemes"
        
        if not content_type:
            print(f"Skipping {link_text} - Unknown content type")
            continue
        
        # Extract metadata
        metadata = extract_metadata(href, link_text, config_key, paper_number, paper_display_name)
        metadata['content_type'] = content_type.upper()
        
        # Determine filename from the URL
        filename = os.path.basename(href)
        
        # Build the folder path
        folder_components = [
            base_path,
            metadata['level'],
            metadata['exam_board'],
            paper_number,
            content_type
        ]
        
        save_folder = os.path.join(*folder_components)
        save_path = os.path.join(save_folder, filename)
        
        # Download the file (unless dry run)
        if dry_run:
            print(f"[DRY RUN] [{i+1}/{len(paper_links)}] Would download: {filename}")
            print(f"  → Would save to {save_path}")
            print(f"  → Metadata: Year: {metadata.get('year', 'Unknown')}, Month: {metadata.get('month', 'Unknown')}, Paper: {metadata['paper_type']}, Type: {display_type}")
            continue
        
        try:
            print(f"[{i+1}/{len(paper_links)}] Downloading: {filename}")
            
            # Get the full URL for download
            download_url = href
            
            response = requests.get(download_url, headers=headers)
            
            # If status code is 400, retry once
            if response.status_code == 400:
                print(f"  ⚠ Got status code 400, retrying once...")
                time.sleep(random.uniform(2, 4))
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
                
                downloads_count += 1
            else:
                print(f"  ✗ Failed to download (Status code: {response.status_code})")
                
        except Exception as e:
            print(f"  ✗ Error downloading {filename}: {e}")
    
    return downloads_count 