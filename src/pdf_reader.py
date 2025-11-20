# src/pdf_reader.py

import os
import glob
from pypdf import PdfReader
from pdf2image import convert_from_path
import pytesseract
from PIL import Image, ImageFilter, ImageOps
from .config import INPUT_DIR


def get_pdf_file_paths(input_dir=INPUT_DIR):
    """
    Finds and returns a list of all PDF file paths in the input directory.
    """
    return glob.glob(os.path.join(input_dir, '**', '*.pdf'), recursive=True)


# -----------------------------
#   OCR PREPROCESSING
# -----------------------------
def preprocess_image(img):
    """
    Preprocess scanned page image:
    - Convert to grayscale
    - Increase contrast
    - Sharpen edges
    - Remove noise
    """
    img = img.convert("L")                    # grayscale
    img = ImageOps.autocontrast(img)          # improve contrast
    img = img.filter(ImageFilter.SHARPEN)     # sharpen text
    return img


def ocr_page_image(image):
    """
    Run OCR (with improved config) on a PIL image.
    """
    try:
        img = preprocess_image(image)

        # HIGH-QUALITY OCR CONFIG
        config = r"--oem 3 --psm 6 -l eng"

        text = pytesseract.image_to_string(img, config=config)
        return text.strip()

    except Exception as e:
        return f"[OCR ERROR] {e}"


def extract_pdf_text(file_path):
    """
    Extracts text from a PDF:
    - Try native text extraction via pypdf.
    - If blank → page-level OCR via Tesseract LSTM.
    Returns the concatenated extracted text.
    """
    full_text = ""

    try:
        reader = PdfReader(file_path)
        num_pages = len(reader.pages)
    except Exception as e:
        print(f"Error opening PDF {file_path}: {e}")
        return None

    print(f" → Converting pages to images (OCR fallback)...")

    try:
        images = convert_from_path(file_path, dpi=300)
    except Exception as e:
        print(f"Warning: PDF-to-image conversion failed: {e}")
        images = [None] * num_pages  # fallback to avoid index errors

    for i in range(num_pages):
        page = reader.pages[i]

        # Step 1: try native text extraction
        try:
            page_text = page.extract_text()
        except:
            page_text = None

        # Step 2: fallback to OCR if page text empty
        if not page_text or page_text.strip() == "":
            img = images[i]
            if img is not None:
                print(f"   → OCR page {i+1}/{num_pages}")
                page_text = ocr_page_image(img)
            else:
                page_text = ""

        full_text += page_text + "\n--- PAGE BREAK ---\n"

    return full_text.strip()
