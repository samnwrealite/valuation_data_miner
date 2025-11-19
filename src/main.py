# src/main.py

import os
import csv
import json
from .config import INPUT_DIR, OUTPUT_DIR, OUTPUT_FILE, COLUMN_HEADERS, DEBUG_MATCHES_FILE
from .pdf_reader import get_pdf_file_paths, extract_pdf_text
from .data_parser import extract_data_points

def ensure_output_directory():
    """Checks if the output directory exists and creates it if not."""
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)
        print(f"Created output directory: {OUTPUT_DIR}")

def run_extraction_pipeline():
    """
    Main function to process all PDF files and write the consolidated CSV.
    Also writes a debug JSON containing per-file extraction mapping for troubleshooting.
    """
    ensure_output_directory()

    pdf_files = get_pdf_file_paths()

    if not pdf_files:
        print(f"❌ No PDF files found in the directory: {INPUT_DIR}. Please check the folder name.")
        return

    print(f"--- Starting Batch Extraction for {len(pdf_files)} files ---")

    all_extracted_data = []
    debug_matches = {}

    for i, file_path in enumerate(pdf_files):
        filename = os.path.basename(file_path)
        print(f"Processing file {i+1}/{len(pdf_files)}: {filename}")

        full_text = extract_pdf_text(file_path)
        if not full_text:
            print(f"Warning: no text extracted for {filename}. Skipping.")
            continue

        extracted = extract_data_points(full_text, file_path)
        # keep a debug snapshot of which keys are N/A for quick triage
        debug_matches[filename] = {k: ("FOUND" if extracted.get(k) not in (None, "", "N/A") else "MISSING") for k in extracted}
        all_extracted_data.append(extracted)

    print("\nExtraction complete. Writing CSV...")

    try:
        with open(OUTPUT_FILE, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=COLUMN_HEADERS)
            writer.writeheader()
            for row in all_extracted_data:
                # ensure row contains all headers (it should, but be safe)
                normalized = {h: row.get(h, "N/A") for h in COLUMN_HEADERS}
                writer.writerow(normalized)

        # write debug matches to JSON for troubleshooting
        with open(DEBUG_MATCHES_FILE, 'w', encoding='utf-8') as jf:
            json.dump(debug_matches, jf, indent=2)

        print(f"Success! All data written to '{OUTPUT_FILE}'")
        print(f"Debug matches written to '{DEBUG_MATCHES_FILE}'")
        print(f"Total records exported: {len(all_extracted_data)}")

    except Exception as e:
        print(f"Error writing CSV file: {e}")

if __name__ == "__main__":
    # ensure directories exist for backwards compatibility
    os.makedirs(os.path.join(os.path.dirname(__file__), 'input'), exist_ok=True)
    os.makedirs(os.path.join(os.path.dirname(__file__), 'output'), exist_ok=True)

    run_extraction_pipeline()
