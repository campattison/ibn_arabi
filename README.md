# Claude PDF OCR

A script that breaks a PDF into single pages and uses Claude 3.7 API to perform OCR on each page.

## Requirements

- Python 3.6+
- Anthropic API key

## Installation

1. Install the required packages:

```bash
pip install -r requirements.txt
```

2. Set your Anthropic API key as an environment variable:

```bash
export ANTHROPIC_API_KEY="your_api_key_here"
```

## Usage

```bash
python claude_pdf_ocr.py path/to/your/pdf/file.pdf
```

### Optional Arguments

- `--output-dir`: Directory to save split PDF pages (default: "split_pdfs")
- `--result-file`: File to save OCR results (default: "ocr_results.txt")

Example:

```bash
python claude_pdf_ocr.py document.pdf --output-dir my_pages --result-file document_text.txt
```

## How It Works

1. The script splits the input PDF into individual pages
2. Each page is encoded as base64 and sent to Claude 3.7 API
3. Claude extracts the text using its OCR capabilities
4. All extracted text is saved to a single output file 