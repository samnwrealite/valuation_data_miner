## NW Realite Valuation Reports 2025 Data Pipeline

### Project Summary

This pipeline automates the extraction of structured property valuation report data data for 2025 . Many property reports are scanned or digital PDFs containing critical information such as property IDs, report references, owner details, valuation data, and land characteristics.  

The pipeline combines **OCR**, **AI-based extraction**, and **database storage** to convert these PDFs into structured JSON records and store them in **Supabase**, enabling downstream analytics, reporting, or integration with other systems.

Key features:
- Handles scanned and native PDFs.
- Uses **Tesseract OCR** for image-based PDFs.
- Uses **Google Gemini** for structured data extraction from raw text.
- Cleans, validates, and saves extracted data in JSON format.
- Automatically uploads results to a **Supabase** database.

---

## Workflow

The workflow is a **multi-step pipeline**:

1. **PDF Discovery**
   - Scan a designated directory for PDF files to process.

2. **Text Extraction**
   - Attempt **pdfplumber** extraction first for digital PDFs.
   - Fall back to **Tesseract OCR** for scanned PDFs.
   - Save intermediate OCR text for debugging and auditing.

3. **AI-based Data Extraction**
   - Feed the cleaned text to **Google Gemini** in a structured prompt.
   - Extract:
     - Property IDs: `property_id`, `title_number`, `lr_number`, `ir_number`.
     - Client and valuer details: `client_name`, `valuer_name`.
     - Dates: `inspection_date`, `report_date`.
     - Location and land details.
     - Market valuation.
   - Merge the outputs into a single structured JSON object.

4. **Metadata Enrichment**
   - Add processing metadata:
     - Source filename, page count, OCR usage, processing time, and timestamp.

5. **Data Storage**
   - Save each extracted JSON to a local folder.
   - Optionally, upload to **Supabase** table `property_valuations`.

6. **Summary Report**
   - Generate a `summary.json` containing all processed files, timing, and extraction results.

---

## System Architecture

```
                          +----------------------+
                          |      PDF Files       |
                          |  (Kenyan Valuation   |
                          |       Reports)       |
                          +----------+-----------+
                                     |
                                     v
                     +----------------------------------+
                     |   OCR Layer (Docling / Tesseract)|
                     |  - Extract text per page         |
                     |  - Handle scanned PDFs           |
                     +------------------+---------------+
                                     |
                                     v
                        +------------------------------+
                        |   Pre-processing Engine      |
                        |  - Clean headers/footers     |
                        |  - Normalize whitespace      |
                        |  - Detect report references  |
                        +---------------+--------------+
                                        |
                                        v
              -----------------------------------------------
              |                                              |
              |                                              |
     +-------------------------+                 +---------------------------+
     |   Gemini Pass 1         |                 |   Gemini Pass 2           |
     |  Core Identifiers       |                 |  Land & Valuation Data    |
     |-------------------------|                 |---------------------------|
     | - title number          |                 | - plot area               |
     | - LR / IR number        |                 | - soil / vegetation       |
     | - report reference      |                 | - coordinates             |
     | - valuer / client name  |                 | - valuation amount        |
     | - inspection/report date|                 | - tenure / proprietor     |
     +-----------+-------------+                 +-------------+-------------+
                 \                                   /
                  \                                 /
                   \                               /
                    v                             v
                 +-----------------------------------+
                 |      Deep JSON Merge Engine       |
                 |  - Combine Pass 1 & Pass 2 data    |
                 |  - Normalize missing fields        |
                 |  - Add metadata                    |
                 +------------------+-----------------+
                                    |
                                    v
                      +------------------------------+
                      |      Final JSON Output       |
                      |   (Clean Structured Record)  |
                      +--------------+---------------+
                                     |
                                     v
               +-------------------------------------------+
               |        Supabase Ingestion Layer           |
               |-------------------------------------------|
               | - REST / RPC insert into schema           |
               | - Store JSON in table (e.g., properties)  |
               | - Save metadata & processing logs         |
               +------------------+------------------------+
                                     |
                                     v
                       +-------------------------------+
                       |     Supabase Database         |
                       |  (Postgres + Row Level Sec)   |
                       |-------------------------------|
                       | - nrb properties table        |
                       | - other counties table        |
                       +-------------------------------+

```

### Summary of architecture
```
PDF → OCR → Text Cleaning → Gemini (2-Pass Extraction) → Deep Merge → Clean JSON → Supabase Postgres

```