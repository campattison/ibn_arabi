import os
import subprocess
from pathlib import Path

# Define paths
current_dir = Path(__file__).parent
input_dir = current_dir / "input"
output_dir = current_dir / "output" / "split_pdfs"
results_file = current_dir / "output" / "ocr_results.txt"

# Ensure output directory exists
os.makedirs(output_dir, exist_ok=True)

# Define PDF path
pdf_path = input_dir / "178_mansoub.pdf"

# Run the OCR script
cmd = [
    "python3", 
    str(current_dir / "scripts" / "claude_pdf_ocr.py"),
    str(pdf_path),
    "--output-dir", str(output_dir),
    "--result-file", str(results_file)
]

print(f"Running command: {' '.join(cmd)}")
print("This will process all 107 pages which may take some time. You can press Ctrl+C to stop the process if needed.")
print("The results will be saved incrementally, so you can check the output file even if the process is interrupted.")
subprocess.run(cmd)
print(f"OCR completed. Results saved to {results_file}") 