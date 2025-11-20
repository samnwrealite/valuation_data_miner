# src/data_parser.py

import re
import os
from datetime import datetime
from typing import Tuple, Dict, List

FLAGS = re.IGNORECASE | re.DOTALL | re.MULTILINE

COUNTIES = [
    "Mombasa", "Kwale", "Kilifi", "Tana River", "Lamu", "Taita Taveta", "Garissa", "Wajir",
    "Mandera", "Marsabit", "Isiolo", "Meru", "Tharaka-Nithi", "Embu", "Kitui", "Machakos",
    "Makueni", "Nyandarua", "Nyeri", "Kirinyaga", "Murang'a", "Kiambu", "Turkana", "West Pokot",
    "Samburu", "Trans Nzoia", "Uasin Gishu", "Elgeyo Marakwet", "Nandi", "Baringo", "Laikipia",
    "Nakuru", "Narok", "Kajiado", "Kericho", "Bomet", "Kakamega", "Vihiga", "Bungoma", "Busia",
    "Siaya", "Kisumu", "Homa Bay", "Migori", "Kisii", "Nyamira", "Nairobi County"
]

PROPERTY_TYPES = ["Residential", "Commercial", "Industrial", "Agricultural", "Mixed Use"]
LAND_USES = ["Mixed-use", "Agricultural", "Commercial", "Residential", "Industrial"]
VALUERS = ["Simon Oruka Orwa", "Danish Onyango Orech"]
OCCUPANCY_OPTIONS = ["Yes", "No"]
TENURE_OPTIONS = ["Leasehold Interest", "Freehold Interest"]

def _clean_whitespace(s: str) -> str:
    return " ".join(s.split()) if s and isinstance(s, str) else None

def _safe(value):
    return value if value is not None and value != "" else None

def normalize_number(raw: str, min_digits=6) -> str:
    if not raw:
        return None
    s = re.sub(r'[^0-9]', '', str(raw))
    if s == "" or len(s) < min_digits:
        return None
    return s

def convert_sqft_to_sqm(value: str) -> str:
    try:
        val = float(re.sub(r'[^\d\.]', '', value))
        return f"{val*0.092903:.2f}"
    except:
        return None

def convert_acres_to_hectares(value: str) -> str:
    try:
        val = float(re.sub(r'[^\d\.]', '', value))
        return f"{val*0.404686:.3f}"
    except:
        return None

def fuzzy_date_search(text: str) -> str:
    if not text:
        return None
    patterns = [
        r"(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4})",
        r"(\d{1,2}\s*(?:st|nd|rd|th)?\s*[A-Za-z]{3,9}\s*\d{4})",
        r"([A-Za-z]{3,9}\s*\d{1,2}[,\s]*\d{4})"
    ]
    for p in patterns:
        m = re.search(p, text, FLAGS)
        if m:
            candidate = m.group(1)
            for fmt in ["%d/%m/%Y","%d-%m-%Y","%d %B %Y","%d %b %Y","%B %d %Y","%b %d %Y"]:
                try:
                    dt = datetime.strptime(candidate.strip(), fmt)
                    return dt.strftime("%d/%m/%Y")
                except:
                    continue
            return _clean_whitespace(candidate)
    return None

def decimal_to_dms(value: float, is_lat=True) -> str:
    """Convert decimal to DMS string format: 1°28'12.2"S"""
    degrees = int(abs(value))
    minutes = int((abs(value) - degrees) * 60)
    seconds = round((abs(value) - degrees - minutes/60) * 3600, 1)
    direction = ''
    if is_lat:
        direction = 'N' if value >=0 else 'S'
    else:
        direction = 'E' if value >=0 else 'W'
    return f"{degrees}°{minutes}'{seconds}\"{direction}"

def extract_coordinates(text: str) -> Tuple[str, str]:
    matches = re.findall(r"(-?\d{1,3}\.\d+)", text)
    if len(matches) >= 2:
        lat, lon = float(matches[0]), float(matches[1])
        return decimal_to_dms(lat, True), decimal_to_dms(lon, False)
    return None, None

def extract_valuer(text: str) -> str:
    for n in VALUERS:
        if n.lower() in text.lower():
            return n
    return None

def extract_property_type(text: str) -> str:
    for p in PROPERTY_TYPES:
        if p.lower() in text.lower():
            return p
    return None

def extract_county(text: str) -> str:
    for c in COUNTIES:
        if c.lower() in text.lower():
            return c
    return None

def extract_land_area(text: str) -> str:
    ha_match = re.search(r'([\d\.]+)\s*(hectares|ha)', text, FLAGS)
    ac_match = re.search(r'([\d\.]+)\s*(acres|acre)', text, FLAGS)
    if ha_match:
        return f"{float(ha_match.group(1)):.3f}"
    if ac_match:
        return convert_acres_to_hectares(ac_match.group(1))
    return None

def extract_builtup_area(text: str) -> str:
    sqft_match = re.search(r'([\d,\.]+)\s*(sq\.? ft|sqft)', text, FLAGS)
    if sqft_match:
        return convert_sqft_to_sqm(sqft_match.group(1))
    sqm_match = re.search(r'([\d,\.]+)\s*(sq\.? m|sqm)', text, FLAGS)
    if sqm_match:
        return f"{float(re.sub(r'[^\d\.]', '', sqm_match.group(1))):.2f}"
    return None

def extract_occupancy(text: str) -> str:
    if re.search(r"occupied|yes", text, FLAGS):
        return "Yes"
    elif re.search(r"vacant|no", text, FLAGS):
        return "No"
    return None

def extract_land_use(text: str) -> str:
    for o in LAND_USES:
        if o.lower() in text.lower():
            return o
    return None

def extract_bedrooms(text: str) -> str:
    m = re.search(r'(\d{1,2})\s*bedroom', text, FLAGS)
    if m:
        val = int(m.group(1))
        return str(val if 0 <= val <= 7 else None)
    return None

def extract_tenure(text: str) -> str:
    if re.search(r"leasehold", text, FLAGS):
        return "Leasehold Interest"
    elif re.search(r"freehold", text, FLAGS):
        return "Freehold Interest"
    return None

def extract_data_points(full_text: str, file_path: str) -> Dict[str,str]:
    text = full_text or ""
    data = {}
    data["FileName"] = os.path.basename(file_path) if file_path else None
    data["REF_ID"] = _safe(find_first([r"Our Ref[:\s]*([\w\/\-\.\d]+)", r"Reference[:\s]*([\w\/\-\.\d]+)"], text))
    data["VALUATION_DATE"] = fuzzy_date_search(text)
    data["VALUER_NAME"] = extract_valuer(text)
    data["TITLE_NUMBER"] = _safe(find_first([r"LR\s*No[:\s]*([\w\d\/\-]+)", r"Title\s*No[:\s]*([\w\d\/\-]+)"], text))
    data["CLIENT_NAME"] = _safe(find_first([r"Client[:\s]*([\w\s]{1,50})"], text))
    data["COUNTY"] = extract_county(text)
    data["LOCATION"] = _safe(find_first([r"Area[:\s]*([\w\s]+)", r"Location[:\s]*([\w\s]+)"], text))
    data["PROPERTY_TYPE"] = extract_property_type(text)
    lat, lon = extract_coordinates(text)
    data["LATITUDE"], data["LONGITUDE"] = lat, lon
    data["TENURE"] = extract_tenure(text)
    data["PROPRIETOR"] = data["CLIENT_NAME"]
    data["LAND_AREA"] = extract_land_area(text)
    data["LAND_USE"] = extract_land_use(text)
    data["BEDROOMS"] = extract_bedrooms(text)
    data["BUILTUP_AREA"] = extract_builtup_area(text)
    data["OCCUPIED"] = extract_occupancy(text)
    data["MARKET_VALUE"] = normalize_number(find_first([r"(?:Market\s+Value)[^\d\n\r]{0,40}([\d\.,/=\sKShs]+)"], text))
    data["LAND_VALUE"] = normalize_number(find_first([r"(?:Land\s+Value)[^\d\n\r]{0,40}([\d\.,/=\sKShs]+)"], text))
    return data

def find_first(patterns: List[str], text: str) -> str:
    for p in patterns:
        m = re.search(p, text, FLAGS)
        if m:
            if m.groups():
                for g in m.groups():
                    if g and str(g).strip():
                        return _clean_whitespace(str(g))
                return _clean_whitespace(m.group(0))
            return _clean_whitespace(m.group(0))
    return None
