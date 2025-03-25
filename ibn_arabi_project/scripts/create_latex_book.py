import os
import re
import argparse
import logging
from pathlib import Path
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("latex_generation.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def natural_sort_key(s, _nsre=re.compile('([0-9]+)')):
    """Sort strings with embedded numbers naturally."""
    return [int(text) if text.isdigit() else text.lower() for text in re.split(_nsre, s)]

def parse_ocr_file(ocr_file_path):
    """Parse the OCR results file into individual page entries."""
    page_entries = []
    
    try:
        with open(ocr_file_path, 'r', encoding='utf-8') as file:
            content = file.read()
            
            # Split the content by page markers
            page_pattern = re.compile(r'===== (page_\d+) =====\n(.*?)(?=\n=====|\Z)', re.DOTALL)
            matches = page_pattern.findall(content)
            
            for page_id, page_text in matches:
                page_entries.append((page_id, page_text.strip()))
                
        logger.info(f"Parsed {len(page_entries)} pages from OCR file {ocr_file_path}")
        return page_entries
    
    except Exception as e:
        logger.error(f"Failed to parse OCR file {ocr_file_path}: {str(e)}")
        return []

def load_translations(translations_dir):
    """Load all translation files from the directory."""
    translation_files = []
    translation_entries = []
    
    try:
        dir_path = Path(translations_dir)
        for filename in os.listdir(dir_path):
            if filename.startswith("page_") and filename.endswith(".txt") and not filename.endswith(".meta.json"):
                translation_files.append(filename)
        
        # Sort files by page number
        translation_files.sort(key=natural_sort_key)
        
        for filename in translation_files:
            page_id = filename.replace(".txt", "")
            with open(dir_path / filename, 'r', encoding='utf-8') as file:
                translation_entries.append((page_id, file.read().strip()))
        
        logger.info(f"Loaded {len(translation_entries)} translation files from {translations_dir}")
        return translation_entries
    
    except Exception as e:
        logger.error(f"Failed to load translation files from {translations_dir}: {str(e)}")
        return []

def escape_latex(text):
    """Escape special LaTeX characters."""
    escapes = {
        '&': r'\&',
        '%': r'\%',
        '$': r'\$',
        '#': r'\#',
        '_': r'\_',
        '{': r'\{',
        '}': r'\}',
        '~': r'\textasciitilde{}',
        '^': r'\^{}',
        '\\': r'\textbackslash{}',
    }
    
    # Only escape in text mode, not in math mode
    # This is a simplified approach - a more robust implementation would need to track math mode
    for k, v in escapes.items():
        text = text.replace(k, v)
    
    return text

def process_arabic_text(text):
    """Process Arabic text for LaTeX formatting."""
    # Remove or replace special characters that might cause issues in LaTeX
    text = text.replace('\ufeff', '')  # Remove BOM
    
    # Handle the case where the entire text is wrapped in backticks
    if text.startswith('```') and text.endswith('```'):
        text = text[3:-3]  # Remove just the beginning and ending backticks
    else:
        # Remove any code block sequences with language specifiers
        text = re.sub(r'```[a-z]*\n(.*?)```', r'\1', text, flags=re.DOTALL)
        # Remove standalone backticks
        text = text.replace('```', '')
    
    # Escape any LaTeX special characters that might appear in non-Arabic parts
    # We don't want to escape the actual Arabic text
    
    # Handle Arabic footnotes
    text = re.sub(r'_+\n(\d+) (.*?)$', r'\\footnote{\\textarabic{\2}}', text, flags=re.MULTILINE)
    
    # Handle page numbers at the bottom
    text = re.sub(r'\n(\d+)$', r'\n\\arabicpagenumber{\1}', text)
    
    return text

def process_english_text(text):
    """Process English text for LaTeX formatting."""
    # Handle the case where the entire text is wrapped in backticks
    if text.startswith('```') and text.endswith('```'):
        text = text[3:-3]  # Remove just the beginning and ending backticks
    else:
        # Remove any code block sequences with language specifiers
        text = re.sub(r'```[a-z]*\n(.*?)```', r'\1', text, flags=re.DOTALL)
        # Remove standalone backticks
        text = text.replace('```', '')
    
    # Escape LaTeX special characters
    text = escape_latex(text)
    
    # Handle footnotes that were preserved in translation
    text = re.sub(r'_+\n(\d+) (.*?)$', r'\\footnote{\2}', text, flags=re.MULTILINE)
    
    # Handle chapter headers with #
    text = re.sub(r'# (.*?)\n', r'\\section*{\1}\n', text)
    
    # Handle subheaders if present
    text = re.sub(r'## (.*?)\n', r'\\subsection*{\1}\n', text)
    
    # Handle italics (markdown-style)
    text = re.sub(r'\*(.*?)\*', r'\\textit{\1}', text)
    
    # Handle bold (markdown-style)
    text = re.sub(r'\*\*(.*?)\*\*', r'\\textbf{\1}', text)
    
    # Handle page numbers at the bottom
    text = re.sub(r'\n(\d+)$', r'\n\\pagenumber{\1}', text)
    
    return text

def create_latex_document(arabic_entries, english_entries, output_file, title="The Meccan Revelations", author="Ibn Arabi", translator="Translated with Claude 3.7"):
    """Create a LaTeX document with facing-page translations."""
    # Make sure we have the same number of entries
    if len(arabic_entries) != len(english_entries):
        logger.warning(f"Number of Arabic entries ({len(arabic_entries)}) does not match English entries ({len(english_entries)})")
    
    # Match entries by page_id
    arabic_dict = {page_id: text for page_id, text in arabic_entries}
    english_dict = {page_id: text for page_id, text in english_entries}
    
    # Debug: Log the page_ids found
    logger.info(f"Arabic page_ids: {list(arabic_dict.keys())}")
    logger.info(f"English page_ids: {list(english_dict.keys())}")
    
    # Get the set of all page_ids
    all_page_ids = sorted(set(arabic_dict.keys()).union(set(english_dict.keys())), key=natural_sort_key)
    logger.info(f"Combined page_ids: {all_page_ids}")
    
    # Create LaTeX preamble
    latex_content = []
    latex_content.append(r"""\documentclass[12pt,twoside,openright]{book}
\usepackage[a4paper,margin=1in]{geometry}
\usepackage{fontspec}
\usepackage{polyglossia}
\usepackage{fancyhdr}
\usepackage{titlesec}
\usepackage{titletoc}
\usepackage{tocloft}
\usepackage{microtype}
\usepackage{graphicx}
\usepackage[hidelinks]{hyperref}
\usepackage{bookmark}
\usepackage{xcolor}

% Set up fonts
\setmainfont{Times New Roman}
\newfontfamily\arabicfont[Script=Arabic]{Amiri}
\setmainlanguage{english}
\setotherlanguage{arabic}

% Custom page style
\pagestyle{fancy}
\fancyhf{}
\renewcommand{\headrulewidth}{0pt}
\fancyfoot[LE,RO]{\thepage}

% For Arabic page numbers
\newcommand{\arabicpagenumber}[1]{{\centering\textarabic{#1}\par}}
\newcommand{\pagenumber}[1]{{\centering#1\par}}

% Title formatting
\titleformat{\chapter}[display]
{\normalfont\huge\bfseries}{\chaptertitlename\ \thechapter}{20pt}{\Huge}
\titlespacing*{\chapter}{0pt}{50pt}{40pt}

% Document info
\title{\Huge\textbf{""" + title + r"""}}
\author{""" + author + r"""\\\medskip\large """ + translator + r"""}
\date{\today}

\begin{document}

% Title page
\begin{titlepage}
\centering
{\huge\textbf{""" + title + r"""}\par}
\vspace{2cm}
{\Large """ + author + r"""\par}
\vspace{1.5cm}
{\large """ + translator + r"""\par}
\vfill
{\large\today\par}
\end{titlepage}

% Copyright page
\newpage
\thispagestyle{empty}
\vspace*{\fill}
\begin{center}
© \the\year

\medskip
This is an academic translation generated with the assistance of Claude 3.7 AI.

\medskip
All rights reserved.
\end{center}
\vspace*{\fill}
\newpage

% Table of contents
\tableofcontents
\newpage

% Introduction
\chapter*{Introduction}
This volume presents a translation of selected passages from Ibn Arabi's {\itshape Futūḥāt al-Makkiyya} (The Meccan Revelations), focusing on Chapter 178 concerning the knowledge of the station of love. The translation aims to render Ibn Arabi's complex mystical thought and poetic expression into accessible yet accurate English, while preserving the original structure and technical terminology.

\noindent The Arabic text appears on the right-hand (odd-numbered) pages with the corresponding English translation on the left-hand (even-numbered) pages, allowing scholars to easily compare the original with the translation.

\newpage
""")
    
    # Main content - create pairs of Arabic and English pages
    latex_content.append(r"\chapter*{Chapter 178: On the Knowledge of the Station of Love}")
    
    for i, page_id in enumerate(all_page_ids):
        arabic_text = arabic_dict.get(page_id, "")
        english_text = english_dict.get(page_id, "")
        
        # Process the texts
        processed_arabic = process_arabic_text(arabic_text)
        processed_english = process_english_text(english_text)
        
        # Add English translation on even (left) pages
        latex_content.append(r"\newpage")
        latex_content.append(r"\begin{english}")
        latex_content.append(processed_english)
        latex_content.append(r"\end{english}")
        
        # Add Arabic original on odd (right) pages
        latex_content.append(r"\newpage")
        latex_content.append(r"\begin{arabic}")
        latex_content.append(r"\textarabic{" + processed_arabic + "}")
        latex_content.append(r"\end{arabic}")
    
    # End of document
    latex_content.append(r"""
\newpage
\chapter*{Notes on the Translation}
This translation was prepared using advanced language processing technology, specifically Claude 3.7 AI by Anthropic. The process involved:

\begin{itemize}
    \item Optical character recognition (OCR) of the original Arabic text from scanned images
    \item Translation from Classical Arabic to English, with careful attention to Ibn Arabi's unique terminology and poetic style
    \item Preservation of the original structure, formatting, and layout
    \item Meticulous review and refinement to ensure accuracy
\end{itemize}

\noindent While every effort has been made to ensure accuracy, readers are encouraged to consult other translations and commentaries on Ibn Arabi's work for a more complete understanding of his complex thought.

\newpage
\chapter*{Bibliography}
\begin{thebibliography}{9}
\bibitem{chittick} Chittick, William C. (1989). \textit{The Sufi Path of Knowledge: Ibn al-Arabi's Metaphysics of Imagination}. Albany: State University of New York Press.

\bibitem{corbin} Corbin, Henry (1969). \textit{Creative Imagination in the Sufism of Ibn Arabi}. Princeton: Princeton University Press.

\bibitem{ibnarabi} Ibn Arabi, Muhyiddin. \textit{Al-Futūḥāt al-Makkiyya (The Meccan Revelations)}. Edited by Osman Yahia. Cairo, 1972.

\bibitem{morris} Morris, James W. (2005). \textit{The Reflective Heart: Discovering Spiritual Intelligence in Ibn 'Arabi's Meccan Illuminations}. Louisville: Fons Vitae.
\end{thebibliography}

\end{document}
""")
    
    # Join all content and write to file
    full_latex = "\n".join(latex_content)
    
    try:
        with open(output_file, 'w', encoding='utf-8') as file:
            file.write(full_latex)
        logger.info(f"LaTeX document successfully written to {output_file}")
        return True
    except Exception as e:
        logger.error(f"Failed to write LaTeX document to {output_file}: {str(e)}")
        return False

def main():
    """Main function to run the LaTeX generator."""
    parser = argparse.ArgumentParser(description="Create a LaTeX document with facing-page translation of Ibn Arabi")
    parser.add_argument("--ocr-file", type=str, help="OCR results file with extracted Arabic text")
    parser.add_argument("--translations-dir", type=str, help="Directory containing translation files")
    parser.add_argument("--output", type=str, help="Output LaTeX file path")
    parser.add_argument("--title", type=str, default="The Meccan Revelations: Chapter 178", 
                        help="Title of the book")
    parser.add_argument("--author", type=str, default="Ibn Arabi", 
                        help="Author name")
    parser.add_argument("--translator", type=str, default="Translated with Claude 3.7", 
                        help="Translator name or note")
    
    args = parser.parse_args()
    
    # Get the script's directory
    script_dir = Path(__file__).parent.parent.absolute()
    
    # Use provided paths or defaults
    ocr_file = args.ocr_file or (script_dir / "output" / "trial_ocr_results.txt")
    translations_dir = args.translations_dir or (script_dir / "output" / "translations")
    output_file = args.output or (script_dir / "output" / "ibn_arabi_translation.tex")
    
    # Convert Path objects to strings
    ocr_file = str(ocr_file)
    translations_dir = str(translations_dir)
    output_file = str(output_file)
    
    # Load Arabic OCR and English translations
    arabic_entries = parse_ocr_file(ocr_file)
    english_entries = load_translations(translations_dir)
    
    if not arabic_entries:
        logger.error(f"No Arabic entries found in {ocr_file}")
        return
    
    if not english_entries:
        logger.error(f"No English translations found in {translations_dir}")
        return
    
    # Create the LaTeX document
    success = create_latex_document(
        arabic_entries, 
        english_entries, 
        output_file,
        title=args.title,
        author=args.author,
        translator=args.translator
    )
    
    if success:
        logger.info("LaTeX document generation completed successfully.")
        logger.info(f"Next steps:")
        logger.info(f"1. Install TeX Live with XeLaTeX and required packages")
        logger.info(f"2. Compile the document with: xelatex '{output_file}'")
        logger.info(f"3. Compile again to resolve references: xelatex '{output_file}'")
    else:
        logger.error("LaTeX document generation failed.")

if __name__ == "__main__":
    main() 