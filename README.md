# Physics and Maths Tutor Scraper

A command-line tool for downloading A-Level Mathematics past papers from Physics and Maths Tutor (PMT). Automatically organizes papers by exam board, level, paper type, and content type.

## Features

- **Organized Download Structure**: Creates a logical folder hierarchy for papers
- **Smart Resumption**: Continues from where you left off if interrupted
- **PDF Validation**: Checks that downloaded files are valid PDFs
- **Progress Tracking**: Shows download progress with progress bars
- **Detailed Logging**: Logs all activity for troubleshooting
- **File Integrity**: Generates and stores MD5 hashes of downloaded files
- **Respectful Scraping**: Implements delays between requests to avoid overloading the server
- **Robust Error Handling**: Retries failed downloads with exponential backoff
- **Command-line Interface**: Configure all aspects through command-line arguments

## Installation

1. Clone this repository:
   ```bash
   git clone https://github.com/your-username/math-scraper.git
   cd math-scraper
   ```

2. Install the required dependencies:
   ```bash
   pip install requests beautifulsoup4 tqdm PyPDF2
   ```

## Usage

Basic usage:

```bash
python main.py
```

This will download all Edexcel A-Level Math papers to the `./exam_papers` directory and create a tracking file at `./downloaded_papers.csv`.

### Command-line Options

```
usage: main.py [-h] [--output OUTPUT] [--csv CSV] [--config {edexcel_alevel}] [--no-resume]
               [--no-validate] [--min-delay MIN_DELAY] [--max-delay MAX_DELAY] [--debug]

PMT Exam Paper Scraper

options:
  -h, --help            show this help message and exit
  --output OUTPUT, -o OUTPUT
                        Base directory to save downloaded papers
  --csv CSV             Path to tracking CSV file
  --config {edexcel_alevel}, -c {edexcel_alevel}
                        Configuration to use for scraping
  --no-resume           Do not resume from previous downloads, start fresh
  --no-validate         Skip PDF validation
  --min-delay MIN_DELAY
                        Minimum delay between requests in seconds
  --max-delay MAX_DELAY
                        Maximum delay between requests in seconds
  --debug               Enable debug logging
```

### Examples

Download to a custom directory:
```bash
python main.py --output ./my_papers
```

Start fresh (ignore previously downloaded files):
```bash
python main.py --no-resume
```

Adjust request delays (for faster/slower downloads):
```bash
python main.py --min-delay 0.5 --max-delay 1.0
```

Enable debug logging:
```bash
python main.py --debug
```

## Output Structure

The papers are organized in the following structure:

```
exam_papers/
├── Edexcel/
│   ├── ALEVEL/
│   │   ├── Paper_1/
│   │   │   ├── question_papers/
│   │   │   │   └── [Question papers for Paper 1]
│   │   │   └── mark_schemes/
│   │   │       └── [Mark schemes for Paper 1]
│   │   ├── Paper_2/
│   │   │   ├── question_papers/
│   │   │   │   └── [Question papers for Paper 2]
│   │   │   └── mark_schemes/
│   │   │       └── [Mark schemes for Paper 2]
│   │   └── Paper_3/
│   │       ├── Mechanics/
│   │       │   ├── question_papers/
│   │       │   │   └── [Mechanics question papers]
│   │       │   └── mark_schemes/
│   │       │       └── [Mechanics mark schemes]
│   │       └── Statistics/
│   │           ├── question_papers/
│   │           │   └── [Statistics question papers]
│   │           └── mark_schemes/
│   │               └── [Statistics mark schemes]
```

## Tracking File

A CSV file is created that tracks all downloaded papers with the following information:

- Filename
- Exam board
- Level
- Paper type
- Subtype (for Paper 3)
- Content type (QP or MS)
- Year
- Month
- File path
- Download date
- File hash (MD5)
- Validation status

## Extending for Other Exam Boards

The code is designed to be easily extended for other exam boards by adding new configurations to the `CONFIGS` dictionary in `main.py`.

## License

This project is for educational purposes only. Please respect the copyright of Physics and Maths Tutor and other content providers.

## Disclaimer

This tool is designed for personal use to help students organize study materials. Please use responsibly and respect the website's terms of service. 