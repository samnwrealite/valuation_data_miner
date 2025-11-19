# src/pdf_reader.py

import os
import glob
from pypdf import PdfReader
from pdf2image import convert_from_path
import pytesseract
from .config import INPUT_DIR


def get_pdf_file_paths(input_dir=INPUT_DIR):
    """
    Finds and returns a list of all PDF file paths in the input directory.
    """
    return glob.glob(os.path.join(input_dir, '**', '*.pdf'), recursive=True)


def ocr_page_image(image):
    """
    Run OCR on a PIL image and return the recognized text.
    """
    try:
        text = pytesseract.image_to_string(image)
        return text.strip()
    except Exception as e:
        return f"[OCR ERROR] {e}"


def extract_pdf_text(file_path):
    """
    Extracts text from a PDF.
    - If the PDF contains selectable text, use PdfReader.
    - If the PDF page is scanned (extract_text() = None), run OCR.
    Returns full text + page break markers.
    """
    full_text = ""

    try:
        reader = PdfReader(file_path)
        pages = reader.pages
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
        return None

    # Convert full PDF to images ONCE 
    try:
        images = convert_from_path(file_path, dpi=300)
    except Exception as e:
        print(f"Warning: Could not convert PDF pages to images for OCR: {e}")
        images = []

    for i, page in enumerate(pages):
        # First try native text extraction
        extracted = None
        try:
            extracted = page.extract_text()
        except:
            extracted = None

        # If native text is empty, fall back to OCR
        if not extracted or extracted.strip() == "":
            if images:
                ocr_text = ocr_page_image(images[i])
                extracted = ocr_text
            else:
                extracted = ""

        full_text += (extracted or "") + "\n--- PAGE BREAK ---\n"

    return full_text.strip()
