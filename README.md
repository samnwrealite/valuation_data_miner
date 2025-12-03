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

### Link supabase to power bi
```
let
    Source = Web.Contents(
        "https://vtsjmfrfvmqrcjheubyn.supabase.co/rest/v1/YOUR_TABLE_NAME?select=*&apikey=YOUR_ANON_KEY"
    ),
    Json = Json.Document(Source),
    ToTable = Table.FromRecords(Json)
in
    ToTable
```

### Create table
```
-- Create the new table
CREATE TABLE public.table_name_year_raw/clean (
    id bigserial PRIMARY KEY,
    property_id text NOT NULL,
    report_reference text,
    title_number text,
    lr_number text,
    ir_number text,
    client_name text,
    valuer_name text,
    inspection_date text,
    valuation_date text,
    location_county text,
    location_description text,
    location_coordinates text,
    plot_area_hectares numeric,
    plot_area_acres numeric,
    land_use text,
    plot_shape text,
    soil_type text,
    gradient text,
    drainage text,
    vegetation text,
    tenure_type text,
    registered_proprietor text,
    ownership_type text,
    encumbrances text,
    market_value_amount numeric,
    market_value_currency text,
    metadata jsonb,
    created_at timestamp with time zone DEFAULT now()
);

```
