# src/config.py

import os

# --- Directory Configuration ---
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INPUT_DIR = os.path.join(BASE_DIR, 'data')
OUTPUT_DIR = os.path.join(BASE_DIR, 'output')
OUTPUT_FILE = os.path.join(OUTPUT_DIR, 'consolidated_valuation_data.csv')
DEBUG_MATCHES_FILE = os.path.join(OUTPUT_DIR, 'debug_matches.json')

# --- CSV Header Configuration ---
COLUMN_HEADERS = [
    "FileName",
    "REF_ID",
    "VALUATION_DATE",
    "VALUER_NAME",
    "TITLE_NUMBER",
    "CLIENT_NAME",
    "COUNTY",
    "LOCATION",
    "PROPERTY_TYPE",
    "LATITUDE",
    "LONGITUDE",
    "TENURE",
    "PROPRIETOR",
    "LAND_AREA",
    "LAND_USE",
    "BEDROOMS",
    "BUILTUP_AREA",
    "OCCUPIED",
    "MARKET_VALUE",
    "LAND_VALUE",
]
