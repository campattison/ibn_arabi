import os
import subprocess
from pathlib import Path

# Define paths
current_dir = Path(__file__).parent
ocr_file = current_dir / "output" / "ocr_results.txt"
output_dir = current_dir / "output" / "translations"

# Ensure output directory exists
os.makedirs(output_dir, exist_ok=True)

def run_translation(pages=None, workers=1, force=False, create_combined=True):
    """Run the Ibn Arabi translator with specified parameters."""
    
    # Build command
    cmd = [
        "python3",
        str(current_dir / "scripts" / "translate_ibn_arabi.py"),
        "--ocr-file", str(ocr_file),
        "--output", str(output_dir),
        "--workers", str(workers)
    ]
    
    # Add optional arguments
    if force:
        cmd.append("--force")
    
    if create_combined:
        cmd.append("--create-combined")
    
    if pages:
        cmd.extend(["--pages"] + pages)
    
    # Print command info
    print(f"Starting Ibn Arabi translation with:")
    print(f"  OCR file: {ocr_file}")
    print(f"  Output directory: {output_dir}")
    print(f"  Workers: {workers}")
    if pages:
        print(f"  Pages to translate: {', '.join(pages)}")
    else:
        print("  Translating all available pages")
    
    print("\nRunning command:", ' '.join(cmd))
    print("This will translate the OCR results to English. The process may take some time.")
    print("Press Ctrl+C to stop the process if needed.\n")
    
    # Run the translator
    subprocess.run(cmd)
    
    print(f"\nTranslation completed. Results saved to {output_dir}")
    print(f"If requested, a combined translation file is available at {output_dir}/combined_translation.txt")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Run the Ibn Arabi translator")
    parser.add_argument("--pages", type=str, nargs="+", help="Specific pages to translate (e.g., page_1 page_2)")
    parser.add_argument("--workers", type=int, default=1, help="Number of parallel workers (default: 1)")
    parser.add_argument("--force", action="store_true", help="Force retranslation of already translated pages")
    parser.add_argument("--no-combined", action="store_true", help="Don't create a combined translation file")
    
    args = parser.parse_args()
    
    run_translation(
        pages=args.pages,
        workers=args.workers,
        force=args.force,
        create_combined=not args.no_combined
    ) 