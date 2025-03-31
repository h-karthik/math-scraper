import os

# Configuration for different exam boards and paper types
CONFIGS = {
    "ocr_alevel": {
        "name": "OCR A-Level",
        "base_url": "https://www.physicsandmathstutor.com/maths-revision/a-level-ocr/papers/",
        "paper_sections": [
            {
                "name": "Paper 1 - Pure",
                "identifier": "component-1-pure",
                "content_types": ["QP", "MS"]  # QP = Question Papers, MS = Mark Schemes
            },
            {
                "name": "Paper 2 - Pure and Statistics",
                "identifier": "component-2-pure-and-statistics",
                "content_types": ["QP", "MS"]
            },
            {
                "name": "Paper 3 - Pure and Mechanics",
                "identifier": "component-3-pure-and-mechanics",
                "content_types": ["QP", "MS"]
            }
        ]
    },
    "ocr_mei_alevel": {
        "name": "OCR MEI A-Level",
        "base_url": "https://www.physicsandmathstutor.com/maths-revision/a-level-ocr-mei/papers/",
        "paper_sections": [
            {
                "name": "Component 1 - Pure and Mechanics",
                "identifier": "component-1-pure-and-mechanics",
                "content_types": ["QP", "MS"]
            },
            {
                "name": "Component 2 - Pure and Statistics",
                "identifier": "component-2-pure-and-statistics",
                "content_types": ["QP", "MS"]
            },
            {
                "name": "Component 3 - Pure and Comprehension",
                "identifier": "component-3-pure-and-comprehension",
                "content_types": ["QP", "MS"]
            }
        ]
    },
    "aqa_alevel": {
        "name": "AQA A-Level",
        "base_url": "https://www.physicsandmathstutor.com/maths-revision/a-level-aqa/papers/",
        "paper_sections": [
            {
                "name": "Paper 1 - Pure",
                "identifier": "paper-1-pure",
                "content_types": ["QP", "MS"]
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
    },
    "edexcel_alevel": {
        "name": "Edexcel A-Level",
        "base_url": "https://www.physicsandmathstutor.com/maths-revision/a-level-edexcel/papers/",
        "paper_sections": [
            {
                "name": "Paper 1 - Pure",
                "identifier": "paper-1-pure",
                "content_types": ["QP", "MS"]
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
                "subtypes": ["Mechanics", "Statistics"]
            }
        ]
    }
}

# Constants
DEFAULT_BASE_PATH = "/Users/admin/Documents/Test Papers"
DEFAULT_CSV_NAME = "downloaded_papers.csv" 