import os
import re
import time
import json
import argparse
import logging
from pathlib import Path
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
from tqdm import tqdm
from dotenv import load_dotenv
from anthropic import Anthropic, RateLimitError, APIError

# Load environment variables from .env file if it exists
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("ibn_arabi_translation.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def natural_sort_key(s, _nsre=re.compile('([0-9]+)')):
    """Sort strings with embedded numbers naturally."""
    return [int(text) if text.isdigit() else text.lower() for text in re.split(_nsre, s)]

def initialize_anthropic(api_key=None):
    """Initialize the Anthropic client with the provided API key or from environment."""
    if api_key is None:
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("No API key provided. Set ANTHROPIC_API_KEY environment variable or provide it as an argument.")
    return Anthropic(api_key=api_key)

def parse_ocr_file(ocr_file_path):
    """Parse the OCR results file into individual page entries."""
    page_entries = []
    
    try:
        with open(ocr_file_path, 'r', encoding='utf-8') as file:
            content = file.read()
            
            # Split the content by page markers
            # Adjusted pattern to better match the actual format in the file
            page_pattern = re.compile(r'===== (page_\d+) =====\n(.*?)(?=\n=====|\Z)', re.DOTALL)
            matches = page_pattern.findall(content)
            
            for page_id, page_text in matches:
                page_entries.append((page_id, page_text.strip()))
                
        logger.info(f"Parsed {len(page_entries)} pages from OCR file {ocr_file_path}")
        return page_entries
    
    except Exception as e:
        logger.error(f"Failed to parse OCR file {ocr_file_path}: {str(e)}")
        return []

def translate_text(client, text, model="claude-3-7-sonnet-latest", max_retries=3, retry_delay=2):
    """Translate text using Anthropic's Claude API with retry logic."""
    system_prompt = """You are a scholar specializing in translating Ibn Arabi's complex mystical Arabic writings into English.

TRANSLATION GUIDELINES:
1. Preserve the original structure, format, and layout - especially for poetry and verse
2. Translate with extreme precision and fidelity to the source text
3. Maintain Ibn Arabi's distinct style, complex metaphors, and technical Sufi terminology
4. Render specialized Sufi terms accurately while preserving their technical meaning
5. DO NOT add explanatory notes, commentary, or interpolations
6. Respect line breaks, stanza divisions, and other formatting elements
7. When encountering ambiguities, render the most literal translation possible without interpretation
8. Preserve any footnotes, page numbers, or reference markers
9. For poetry, attempt to convey the rhythm and poetic qualities while prioritizing accuracy over style

Your goal is to create a scholarly, meticulous translation that captures both the letter and spirit of Ibn Arabi's work while avoiding any interpretive intrusion."""
    
    user_prompt = "Please translate the following Ibn Arabi text from Classical Arabic into English. Preserve all formatting, poetry structure, and technical terms. The text is from the Futūḥāt al-Makkiyya (Meccan Revelations) or related works.\n\n"
    
    combined_prompt = f"{user_prompt}{text}"
    
    for attempt in range(max_retries):
        try:
            # Set up parameters for the API call
            params = {
                "model": model,
                "max_tokens": 4000,
                "system": system_prompt,
                "messages": [
                    {"role": "user", "content": combined_prompt}
                ]
            }
            
            response = client.messages.create(**params)
            return response.content[0].text
        except RateLimitError:
            wait_time = retry_delay * (2 ** attempt)
            logger.warning(f"Rate limit exceeded. Waiting {wait_time} seconds before retry.")
            time.sleep(wait_time)
        except APIError as e:
            if attempt < max_retries - 1:
                wait_time = retry_delay * (2 ** attempt)
                logger.warning(f"API error: {str(e)}. Retrying in {wait_time} seconds.")
                time.sleep(wait_time)
            else:
                logger.error(f"Failed after {max_retries} attempts: {str(e)}")
                raise
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}")
            raise
    
    raise Exception(f"Failed to translate after {max_retries} attempts")

def process_page(args):
    """Process a single page for translation."""
    client, page_id, text, output_directory, model, force_retranslate = args
    
    output_filepath = Path(output_directory) / f"{page_id}.txt"
    
    # Skip if translation exists and force_retranslate is False
    if output_filepath.exists() and not force_retranslate:
        logger.info(f"Skipping {page_id} - translation already exists")
        return page_id, "skipped"
    
    try:
        logger.info(f"Translating {page_id}...")
        translation = translate_text(client, text, model=model)
        
        # Save translation to output file
        with open(output_filepath, 'w', encoding='utf-8') as file:
            file.write(translation)
        
        # Save metadata
        metadata = {
            "source_page": page_id,
            "translation_date": datetime.now().isoformat(),
            "model": model,
            "characters": len(text),
            "status": "completed"
        }
        
        metadata_path = output_filepath.with_suffix('.meta.json')
        with open(metadata_path, 'w', encoding='utf-8') as meta_file:
            json.dump(metadata, meta_file, indent=2)
        
        logger.info(f"Translation saved to {output_filepath}")
        return page_id, "completed"
    
    except Exception as e:
        logger.error(f"Failed to translate {page_id}: {str(e)}")
        
        # Save error information
        error_dir = Path(output_directory) / "errors"
        error_dir.mkdir(exist_ok=True)
        
        error_info = {
            "source_page": page_id,
            "error_date": datetime.now().isoformat(),
            "error_message": str(e),
            "status": "failed"
        }
        
        error_path = error_dir / f"{page_id}.error.json"
        with open(error_path, 'w', encoding='utf-8') as error_file:
            json.dump(error_info, error_file, indent=2)
        
        return page_id, "failed"

def main():
    """Main function to run the Ibn Arabi translator."""
    parser = argparse.ArgumentParser(description="Translate Ibn Arabi's Arabic texts using Claude API")
    parser.add_argument("--ocr-file", type=str, help="OCR results file with extracted Arabic text")
    parser.add_argument("--output", type=str, help="Output directory for translations")
    parser.add_argument("--model", type=str, default="claude-3-7-sonnet-latest", 
                        help="Claude model to use for translation")
    parser.add_argument("--api-key", type=str, help="Anthropic API key (optional, can use env var)")
    parser.add_argument("--workers", type=int, default=1, 
                        help="Number of parallel workers (default: 1)")
    parser.add_argument("--force", action="store_true", 
                        help="Force retranslation of already translated pages")
    parser.add_argument("--pages", type=str, nargs="+", 
                        help="Specific page IDs to translate (optional)")
    parser.add_argument("--create-combined", action="store_true",
                        help="Create a combined translation file")
    
    args = parser.parse_args()
    
    # Get the script's directory
    script_dir = Path(__file__).parent.parent.absolute()
    
    # Use provided paths or defaults with paths relative to the script's location
    ocr_file = args.ocr_file or os.getenv("OCR_FILE") or (script_dir / "output" / "ocr_results.txt")
    output_directory = args.output or os.getenv("OUTPUT_DIRECTORY") or (script_dir / "output" / "translations")
    
    # Convert Path objects to strings to avoid JSON serialization issues
    ocr_file = str(ocr_file)
    output_directory = str(output_directory)
    
    # Add timestamp to output directory if not specified
    if args.output is None and os.getenv("OUTPUT_DIRECTORY") is None:
        timestamp = datetime.now().strftime("%Y%m%d")
        output_directory = f"{output_directory}_{timestamp}"
    
    # Create output directory if it doesn't exist
    os.makedirs(output_directory, exist_ok=True)
    
    # Initialize the client
    try:
        client = initialize_anthropic(args.api_key)
    except ValueError as e:
        logger.error(str(e))
        return
    
    # Load pages to process
    page_entries = parse_ocr_file(ocr_file)
    
    if not page_entries:
        logger.error(f"No pages found in OCR file {ocr_file}")
        return
    
    # Filter specific pages if requested
    if args.pages:
        page_entries = [(page_id, text) for page_id, text in page_entries if page_id in args.pages]
        if not page_entries:
            logger.error("None of the specified pages were found")
            return
    
    logger.info(f"Starting translation of {len(page_entries)} pages")
    logger.info(f"OCR file: {ocr_file}")
    logger.info(f"Output directory: {output_directory}")
    logger.info(f"Model: {args.model}")
    logger.info(f"Workers: {args.workers}")
    
    # Prepare arguments for processing
    process_args = [
        (client, page_id, text, output_directory, args.model, args.force)
        for page_id, text in page_entries
    ]
    
    # Process pages with progress bar
    results = []
    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        for result in tqdm(
            executor.map(process_page, process_args),
            total=len(process_args),
            desc="Translating pages"
        ):
            results.append(result)
    
    # Summarize results
    completed = sum(1 for _, status in results if status == "completed")
    skipped = sum(1 for _, status in results if status == "skipped")
    failed = sum(1 for _, status in results if status == "failed")
    
    logger.info(f"Translation process completed:")
    logger.info(f"  - Completed: {completed}")
    logger.info(f"  - Skipped: {skipped}")
    logger.info(f"  - Failed: {failed}")
    
    # Save summary
    summary = {
        "timestamp": datetime.now().isoformat(),
        "ocr_file": ocr_file,
        "output_directory": output_directory,
        "model": args.model,
        "total_pages": len(page_entries),
        "completed": completed,
        "skipped": skipped,
        "failed": failed,
        "results": dict(results)
    }
    
    summary_path = Path(output_directory) / "translation_summary.json"
    with open(summary_path, 'w', encoding='utf-8') as summary_file:
        json.dump(summary, summary_file, indent=2)
    
    # Create combined translation file if requested
    if args.create_combined and completed > 0:
        create_combined_translation(output_directory)

def create_combined_translation(output_directory):
    """Create a combined file with all translated pages in order."""
    directory = Path(output_directory)
    
    # Get all translation files
    translation_files = []
    for filename in os.listdir(directory):
        if filename.startswith("page_") and filename.endswith(".txt") and not filename.endswith(".meta.json"):
            translation_files.append(filename)
    
    # Sort files by page number
    translation_files.sort(key=natural_sort_key)
    
    if not translation_files:
        logger.warning("No translation files found to combine")
        return
    
    # Combine all translations
    combined_path = directory / "combined_translation.txt"
    with open(combined_path, 'w', encoding='utf-8') as combined_file:
        for filename in translation_files:
            page_id = filename.replace(".txt", "")
            combined_file.write(f"===== {page_id} =====\n\n")
            
            try:
                with open(directory / filename, 'r', encoding='utf-8') as page_file:
                    combined_file.write(page_file.read())
                combined_file.write("\n\n")
            except Exception as e:
                logger.error(f"Error adding {filename} to combined file: {str(e)}")
    
    logger.info(f"Combined translation saved to {combined_path}")

if __name__ == "__main__":
    main() 