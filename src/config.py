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
    # Basic file/refs
    "FileName",
    "Our_Ref",
    "Valuer_Name",
    "Valuer_Qualifications",
    "Valuer_Company",

    # Core values
    "Market_Value_Kshs",
    "Insurance_Value_Kshs",
    "Forced_Sale_Value_Kshs",
    "Open_Market_Rental_Value_Kshs",

    # Dates
    "Valuation_Date",
    "Inspection_Date",
    "Lease_Start_Date",
    "Transfer_Date",
    "Consent_To_Transfer_Date",

    # Title / identifiers
    "LR_No",
    "IR_No",
    "Title_No",
    "Apartment_No",
    "Unit_Type",
    "Block",
    "Floor_Level",
    "Estate_Name",

    # Location & coords
    "County",
    "Area_Neighborhood",
    "Road_Access_Description",
    "Distance_To_Landmark",
    "Google_Coordinates_Lat",
    "Google_Coordinates_Lon",

    # Physical features
    "Built_Up_Area_SqFt",
    "Plot_Area_Ha",
    "Plot_Area_Acres",
    "Bedrooms",
    "Master_EnSuite",
    "Parking_Spaces",
    "Balcony_Present",
    "Accommodation_Summary",
    "Condition",
    "Occupancy_Status",
    "Internal_Finishes",

    # Legal / tenure
    "Tenure",
    "Lease_Term_Remaining",
    "Encumbrances",
    "Registered_Proprietor",

    # Administrative
    "Page_Count",
    "Notes"
]
