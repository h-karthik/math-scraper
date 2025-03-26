import requests
import os
from bs4 import BeautifulSoup
import re
from urllib.parse import urljoin, unquote
import time
import random
import csv
from datetime import datetime
import logging
import argparse
import hashlib
import sys
from pathlib import Path
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
from tqdm import tqdm
import PyPDF2
import io

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("scraper.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Configuration for different exam boards and paper types
# This makes it easy to extend to other boards/levels later
CONFIGS = {
    "edexcel_alevel": {
        "name": "Edexcel A-Level",
        "base_url": "https://www.physicsandmathstutor.com/maths-revision/a-level-edexcel/papers/",
        "paper_sections": [
            {
                "name": "Paper 1",
                "identifier": "paper1",
                "content_types": ["QP", "MS"]  # Question Papers and Mark Schemes
            },
            {
                "name": "Paper 2",
                "identifier": "paper2",
                "content_types": ["QP", "MS"]
            },
            {
                "name": "Paper 3",
                "identifier": "paper1",  # Yes, this is correct! The HTML has a typo and uses paper1 for Paper 3
                "display_name": "Paper 3 - Statistics & Mechanics",
                "content_types": ["QP", "MS"],
                "subtypes": ["Mechanics", "Statistics"]  # Special case for Paper 3
            }
        ]
    }
    # Example extension for future:
    # "aqa_alevel": { ... similar structure ... }
    # "edexcel_gcse": { ... similar structure ... }
}

def create_session_with_retries(retries=5, backoff_factor=0.3):
    """Create requests session with retry capabilities"""
    session = requests.Session()
    retry = Retry(
        total=retries,
        read=retries,
        connect=retries,
        backoff_factor=backoff_factor,
        status_forcelist=[429, 500, 502, 503, 504],
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount('http://', adapter)
    session.mount('https://', adapter)
    
    # Set up headers for the request
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Referer': 'https://www.physicsandmathstutor.com/'
    })
    
    return session

def create_folder_structure(base_path, config_key):
    """Create organized folder structure based on configuration"""
    config = CONFIGS[config_key]

    # Extract exam board and level from config key
    parts = config_key.split("_")
    board = parts[0].capitalize()
    level = parts[1].upper()

    for section in config["paper_sections"]:
        section_name = section.get('display_name', section['name']).replace(" ", "_")

        # Handle special case for Paper 3 with subtypes
        if "subtypes" in section and section["subtypes"]:
            for subtype in section["subtypes"]:
                for content_type in section["content_types"]:
                    folder_path = os.path.join(
                        base_path, board, level,
                        section_name, subtype,
                        "question_papers" if content_type == "QP" else "mark_schemes"
                    )
                    os.makedirs(folder_path, exist_ok=True)
        else:
            # Standard case for Paper 1 and Paper 2
            for content_type in section["content_types"]:
                folder_path = os.path.join(
                    base_path, board, level,
                    section_name,
                    "question_papers" if content_type == "QP" else "mark_schemes"
                )
                os.makedirs(folder_path, exist_ok=True)

    logger.info(f"Created folder structure for {config['name']}")

def initialize_tracking_csv(csv_path, overwrite=False):
    """Create or prepare the CSV file for tracking downloaded papers"""
    # Check if file exists and has content
    exists = os.path.isfile(csv_path) and os.path.getsize(csv_path) > 0
    
    if exists and not overwrite:
        logger.info(f"Using existing tracking file: {csv_path}")
        return
    
    with open(csv_path, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow([
            'filename', 'exam_board', 'level', 'paper_type', 'subtype',
            'content_type', 'year', 'month', 'file_path', 'download_date',
            'file_hash', 'validated'
        ])
    logger.info(f"{'Reinitialized' if exists else 'Created'} tracking CSV: {csv_path}")

def add_to_tracking_csv(csv_path, metadata, filename, file_path, file_hash="", validated=False):
    """Add downloaded file info to tracking CSV"""
    with open(csv_path, 'a', newline='') as csvfile:
        writer = csv.writer(csvfile)
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
            datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            file_hash,
            str(validated)
        ])

def get_downloaded_files(csv_path):
    """Get a set of already downloaded filenames to avoid duplicates"""
    downloaded = set()
    if not os.path.exists(csv_path):
        return downloaded
        
    try:
        with open(csv_path, 'r', newline='') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                downloaded.add(row['filename'])
    except Exception as e:
        logger.error(f"Error reading tracking CSV: {e}")
    
    return downloaded

def extract_metadata_from_link(href, link_text, config_key, section):
    """Extract metadata from link href and text"""
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

    # Extract year
    year_match = re.search(r'20(\d{2})', link_text)
    if year_match:
        metadata['year'] = f"20{year_match.group(1)}"

    # Extract month - expanded to catch more exam sessions
    month_match = re.search(r'(January|February|March|April|May|June|July|August|September|October|November|December)', link_text, re.IGNORECASE)
    if month_match:
        metadata['month'] = month_match.group(1).capitalize()

    # Extract subtype for Paper 3
    if "subtypes" in section:
        for subtype in section["subtypes"]:
            if subtype in link_text or f"({subtype[:4]})" in link_text:
                metadata['subtype'] = subtype
                break

    return metadata

def validate_pdf(file_path):
    """Validate that a file is a valid PDF"""
    try:
        with open(file_path, 'rb') as f:
            reader = PyPDF2.PdfReader(f)
            if len(reader.pages) > 0:
                return True
            return False
    except Exception as e:
        logger.error(f"PDF validation failed for {file_path}: {e}")
        return False

def calculate_file_hash(file_path):
    """Calculate MD5 hash of file for integrity checking"""
    try:
        with open(file_path, 'rb') as f:
            file_hash = hashlib.md5()
            while chunk := f.read(8192):
                file_hash.update(chunk)
        return file_hash.hexdigest()
    except Exception as e:
        logger.error(f"Error calculating file hash: {e}")
        return ""

def download_file_with_progress(session, url, save_path, retries=3):
    """Download a file with progress bar and retry capabilities"""
    for attempt in range(retries):
        try:
            response = session.get(url, stream=True)
            response.raise_for_status()
            
            total_size = int(response.headers.get('content-length', 0))
            block_size = 1024  # 1 Kibibyte
            
            with open(save_path, 'wb') as f, tqdm(
                    desc=os.path.basename(save_path),
                    total=total_size,
                    unit='iB',
                    unit_scale=True,
                    unit_divisor=1024,
                ) as bar:
                for data in response.iter_content(block_size):
                    size = f.write(data)
                    bar.update(size)
            
            return True
        except requests.RequestException as e:
            wait_time = 2 ** attempt  # Exponential backoff
            logger.warning(f"Download attempt {attempt+1}/{retries} failed: {e}. Retrying in {wait_time}s...")
            time.sleep(wait_time)
            
            # If this was the last attempt
            if attempt == retries - 1:
                logger.error(f"Failed to download after {retries} attempts: {e}")
                return False
    
    return False  # Should not reach here, but just in case

def scrape_pmt_papers(base_path, csv_path, config_key="edexcel_alevel", resume=True, validate_files=True, min_delay=1, max_delay=3):
    """Main function to scrape PMT based on configuration"""
    config = CONFIGS[config_key]

    # Create folders
    create_folder_structure(base_path, config_key)

    # Initialize or use existing tracking CSV
    initialize_tracking_csv(csv_path, overwrite=not resume)

    # Get already downloaded files if resuming
    downloaded_files = get_downloaded_files(csv_path) if resume else set()
    
    # Create session with retry capabilities
    session = create_session_with_retries()

    # Get the main page
    logger.info(f"Fetching main page: {config['base_url']}")
    try:
        response = session.get(config['base_url'])
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
    except requests.RequestException as e:
        logger.error(f"Failed to fetch main page: {e}")
        return False

    # Go through each paper section
    for section in config["paper_sections"]:
        logger.info(f"\nProcessing section: {section.get('display_name', section['name'])}")

        # Find the section in the page by its anchor ID
        section_anchor = soup.find('a', id=section['identifier'])
        
        if not section_anchor:
            logger.warning(f"Could not find section anchor with id: {section['identifier']}")
            continue
            
        # Find the heading element containing the anchor
        section_heading = section_anchor.find_parent(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
        
        if not section_heading:
            logger.warning(f"Could not find heading for section: {section['name']}")
            continue
            
        # For Paper 3, we need to find the correct heading
        if section.get('display_name') and 'Paper 3' in section.get('display_name'):
            # Find all headings after this anchor
            all_h4s = soup.find_all('h4')
            
            # Get the index of our current heading
            current_index = all_h4s.index(section_heading)
            
            # Look for the next heading that contains "Paper 3"
            for i in range(current_index, len(all_h4s)):
                if 'Paper 3' in all_h4s[i].text:
                    section_heading = all_h4s[i]
                    break
            
        # Find the container div that holds the question papers and mark schemes
        # This is typically structured with div.one_fourth elements
        section_container = section_heading.find_next_sibling('div')
        
        if not section_container:
            logger.warning(f"Could not find content container for section: {section.get('display_name', section['name'])}")
            continue
            
        # Find all file links in this section
        links = []
        
        # Find all sibling divs until we hit a horizontal rule or another heading
        current_element = section_container
        
        while current_element and not (current_element.name == 'hr' or current_element.name in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']):
            # Look for links within this element
            if current_element.name == 'div':
                # Find the type of content (QP or MS) from the heading
                content_heading = current_element.find(['h5', 'h6'])
                content_type = None
                
                if content_heading:
                    if "Question" in content_heading.text:
                        content_type = "QP"
                    elif "Mark" in content_heading.text or "MS" in content_heading.text:
                        content_type = "MS"
                
                # Get all links if we found a valid content type
                if content_type:
                    for link in current_element.find_all('a', href=True):
                        links.append((link['href'], link.text, content_type))
            
            # Move to next sibling
            current_element = current_element.find_next_sibling()
        
        logger.info(f"Found {len(links)} links for {section.get('display_name', section['name'])}")

        # Process each link with progress bar
        successful_downloads = 0
        for href, link_text, content_type in tqdm(links, desc=f"Section: {section.get('display_name', section['name'])}"):
            # Get full URL
            full_url = href if href.startswith('http') else urljoin(config['base_url'], href)

            # Create metadata
            metadata = {
                'exam_board': config_key.split('_')[0],
                'level': config_key.split('_')[1],
                'paper_type': section["name"],
                'content_type': content_type,
                'year': None,
                'month': None,
                'subtype': None
            }
            
            # Extract year
            year_match = re.search(r'20(\d{2})', link_text)
            if year_match:
                metadata['year'] = f"20{year_match.group(1)}"
            
            # Extract month - expanded to catch more exam sessions
            month_match = re.search(r'(January|February|March|April|May|June|July|August|September|October|November|December)', 
                                    link_text, re.IGNORECASE)
            if month_match:
                metadata['month'] = month_match.group(1).capitalize()
            
            # Extract subtype for Paper 3
            if "subtypes" in section:
                for subtype in section["subtypes"]:
                    if subtype.lower() in link_text.lower() or f"({subtype[:4].lower()})" in link_text.lower():
                        metadata['subtype'] = subtype
                        break

            # Skip if we couldn't extract the year
            if not metadata['year']:
                logger.debug(f"Skipping {link_text} - Missing year metadata")
                continue

            # Determine filename
            filename = os.path.basename(full_url)
            
            # Clean up filename if needed
            if not filename.endswith('.pdf'):
                filename = f"{link_text.strip()}.pdf"
                filename = re.sub(r'[<>:"/\\|?*]', '_', filename)  # Replace invalid chars
            
            # Skip if already downloaded and resuming
            if resume and filename in downloaded_files:
                logger.debug(f"Skipping {filename} - Already downloaded")
                continue

            # Determine folder to save in
            folder_components = [
                base_path,
                metadata['exam_board'].capitalize(),
                metadata['level'].upper(),
                metadata['paper_type'].replace(" ", "_")
            ]

            # For Paper 3, we need to handle subtypes differently
            if 'Paper 3' in metadata['paper_type'] and metadata.get('subtype'):
                # If no subtype info in filename but this is Paper 3, try to detect from filename
                if '(Mech)' in link_text or '(Mechanics)' in link_text:
                    metadata['subtype'] = 'Mechanics'
                elif '(Stats)' in link_text or '(Statistics)' in link_text:
                    metadata['subtype'] = 'Statistics'
                
                # Add subtype to folder path
                folder_components.append(metadata['subtype'])

            folder_components.append(
                "question_papers" if metadata['content_type'] == "QP" else "mark_schemes"
            )

            save_folder = os.path.join(*folder_components)
            
            # Ensure the folder exists
            os.makedirs(save_folder, exist_ok=True)
            
            save_path = os.path.join(save_folder, filename)

            # Download the file
            try:
                # Add delay to be respectful to the server
                time.sleep(random.uniform(min_delay, max_delay))

                # Download with progress
                download_success = download_file_with_progress(session, full_url, save_path)
                
                if download_success:
                    # Validate the PDF
                    validated = False
                    file_hash = ""
                    
                    if validate_files:
                        validated = validate_pdf(save_path)
                        if not validated:
                            logger.warning(f"Invalid PDF file: {save_path}")
                            os.remove(save_path)  # Remove invalid file
                            continue
                    
                    # Calculate file hash
                    file_hash = calculate_file_hash(save_path)
                    
                    # Add to tracking CSV
                    add_to_tracking_csv(csv_path, metadata, filename, save_path, file_hash, validated)
                    
                    logger.debug(f"Successfully downloaded: {filename}")
                    successful_downloads += 1
                else:
                    logger.warning(f"Failed to download: {filename}")
            except Exception as e:
                logger.error(f"Error processing {filename}: {e}")
        
        logger.info(f"Successfully downloaded {successful_downloads} files for {section.get('display_name', section['name'])}")
    
    return True

def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description="PMT Exam Paper Scraper")
    parser.add_argument("--output", "-o", default="./exam_papers", 
                        help="Base directory to save downloaded papers")
    parser.add_argument("--csv", default="./downloaded_papers.csv", 
                        help="Path to tracking CSV file")
    parser.add_argument("--config", "-c", default="edexcel_alevel", choices=CONFIGS.keys(),
                        help="Configuration to use for scraping")
    parser.add_argument("--no-resume", action="store_true", 
                        help="Do not resume from previous downloads, start fresh")
    parser.add_argument("--no-validate", action="store_true", 
                        help="Skip PDF validation")
    parser.add_argument("--min-delay", type=float, default=1.0, 
                        help="Minimum delay between requests in seconds")
    parser.add_argument("--max-delay", type=float, default=3.0, 
                        help="Maximum delay between requests in seconds")
    parser.add_argument("--debug", action="store_true", 
                        help="Enable debug logging")
    
    return parser.parse_args()

def main():
    # Parse command line arguments
    args = parse_arguments()
    
    # Configure logging level
    if args.debug:
        logger.setLevel(logging.DEBUG)
    
    # Convert paths to absolute
    base_path = os.path.abspath(args.output)
    csv_path = os.path.abspath(args.csv)
    
    logger.info(f"Starting PMT Exam Paper Scraper")
    logger.info(f"Output directory: {base_path}")
    logger.info(f"Tracking CSV: {csv_path}")
    logger.info(f"Configuration: {args.config}")
    logger.info(f"Resume downloads: {not args.no_resume}")
    logger.info(f"Validate PDFs: {not args.no_validate}")
    
    # Run the scraper
    success = scrape_pmt_papers(
        base_path=base_path,
        csv_path=csv_path,
        config_key=args.config,
        resume=not args.no_resume,
        validate_files=not args.no_validate,
        min_delay=args.min_delay,
        max_delay=args.max_delay
    )
    
    if success:
        logger.info(f"Download complete. Paper information saved to {csv_path}")
    else:
        logger.error("Scraping failed. Check logs for details.")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())