import os
import base64
import argparse
from pathlib import Path
from dotenv import load_dotenv
from PyPDF2 import PdfReader, PdfWriter
import anthropic
from tqdm import tqdm

# Load environment variables from .env file
load_dotenv()

def split_pdf(input_pdf, output_dir):
    """Split a PDF into individual pages"""
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        
    pdf = PdfReader(input_pdf)
    total_pages = len(pdf.pages)
    
    print(f"Splitting PDF into {total_pages} individual pages...")
    single_page_pdfs = []
    
    for i in tqdm(range(total_pages)):
        output_path = os.path.join(output_dir, f"page_{i+1}.pdf")
        
        pdf_writer = PdfWriter()
        pdf_writer.add_page(pdf.pages[i])
        
        with open(output_path, "wb") as f:
            pdf_writer.write(f)
            
        single_page_pdfs.append(output_path)
    
    return single_page_pdfs

def encode_pdf_to_base64(pdf_path):
    """Encode PDF file to base64"""
    with open(pdf_path, "rb") as pdf_file:
        return base64.b64encode(pdf_file.read()).decode("utf-8")

def ocr_with_claude(pdf_path, api_key):
    """Use Claude 3.7 to OCR a PDF page directly using PDF support"""
    client = anthropic.Anthropic(api_key=api_key)
    
    # Encode PDF to base64
    pdf_base64 = encode_pdf_to_base64(pdf_path)
    
    message = client.messages.create(
        model="claude-3-7-sonnet-latest",
        max_tokens=4000,
        system="""You are an OCR system specialized in accurately extracting Arabic text from PDF documents. 
Follow these rules strictly:
1. Always transcribe the exact text seen in the document in its original language (Arabic)
2. Preserve the layout, structure, and formatting of the text as much as possible
3. Include all headers, footnotes, and page numbers
4. NEVER translate or summarize the content
5. NEVER describe what you see - extract the actual text
6. Maintain any special characters, diacritics, and symbols exactly as they appear
7. Use Markdown formatting to help preserve structure where appropriate""",
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "document",
                        "source": {
                            "type": "base64",
                            "media_type": "application/pdf",
                            "data": pdf_base64
                        }
                    },
                    {
                        "type": "text", 
                        "text": "Extract ALL text from this PDF page in its original Arabic language. Do not translate or describe the content - extract the exact text as it appears with proper formatting. Be thorough and capture everything visible on the page."
                    }
                ]
            }
        ]
    )
    
    return message.content[0].text

def main():
    parser = argparse.ArgumentParser(description="Split PDF and OCR with Claude 3.7")
    parser.add_argument("pdf_path", help="Path to the PDF file")
    parser.add_argument("--output-dir", default="split_pdfs", help="Output directory for split PDFs")
    parser.add_argument("--result-file", default="ocr_results.txt", help="File to save OCR results")
    args = parser.parse_args()
    
    # Get API key from environment variable
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY environment variable not set")
    
    # Split PDF into individual pages
    single_page_pdfs = split_pdf(args.pdf_path, args.output_dir)
    
    # Process each page with Claude 3.7
    print(f"Processing {len(single_page_pdfs)} pages with Claude 3.7...")
    results = []
    
    for pdf_path in tqdm(single_page_pdfs):
        page_num = os.path.splitext(os.path.basename(pdf_path))[0]
        print(f"\nProcessing {page_num}...")
        
        try:
            ocr_text = ocr_with_claude(pdf_path, api_key)
            results.append((page_num, ocr_text))
            print(f"Successfully processed {page_num}")
        except Exception as e:
            print(f"Error processing {page_num}: {str(e)}")
    
    # Save results to file
    with open(args.result_file, "w", encoding="utf-8") as f:
        for page_num, text in results:
            f.write(f"===== {page_num} =====\n")
            f.write(text)
            f.write("\n\n")
    
    print(f"OCR results saved to {args.result_file}")

if __name__ == "__main__":
    main() 