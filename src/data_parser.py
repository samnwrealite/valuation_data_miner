# src/data_parser.py

import re
import os
from datetime import datetime
from typing import Tuple, Dict, List

# Regex flags used everywhere
FLAGS = re.IGNORECASE | re.DOTALL | re.MULTILINE

# --------------------------
# Utilities / Normalization
# --------------------------
def _clean_whitespace(s: str) -> str:
    return " ".join(s.split()) if s and isinstance(s, str) else s

def _safe(value):
    return value if value is not None and value != "" else "N/A"

def normalize_number(raw: str) -> str:
    """
    Normalize number strings like '8,500,000/ =' or '8,500,000/=' to digits-only string '8500000'.
    Returns "N/A" on failure.
    """
    if not raw or raw == "N/A":
        return "N/A"
    try:
        s = str(raw)
        s = re.sub(r'(?i)kshs\.?', '', s)
        s = re.sub(r'[/=]', '', s)
        s = re.sub(r'[^0-9\.,]', '', s)
        s = s.replace(",", "").replace(".", "")
        if s == "":
            return "N/A"
        s = s.lstrip("0") or "0"
        if not s.isdigit():
            return "N/A"
        return s
    except Exception:
        return "N/A"

def fuzzy_date_search(text: str) -> str:
    """
    Attempts to find a date in text. Returns ISO format YYYY-MM-DD if parseable,
    else returns the matched cleaned string or "N/A".
    Handles odd OCR artifacts like '17% April 2025'.
    """
    if not text:
        return "N/A"
    patterns = [
        r"(\d{1,2}\s*(?:st|nd|rd|th|%|º|o)?\s*[,\s\-\/\.]?\s*[A-Za-z]{3,9}\s*[,\s\-\/\.]?\s*\d{4})",
        r"(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4})",
        r"([A-Za-z]{3,9}\s*\d{1,2}[,\s\-\/\.]?\s*\d{4})"
    ]
    for p in patterns:
        m = re.search(p, text, FLAGS)
        if m:
            candidate = m.group(1)
            candidate_clean = candidate.replace('%', 'th').replace('º', 'th')
            candidate_clean = re.sub(r'(?<=\d)(?:st|nd|rd|th)', '', candidate_clean, flags=re.IGNORECASE)
            fmts = ["%d %B %Y", "%d %b %Y", "%d/%m/%Y", "%d-%m-%Y", "%d/%m/%y", "%B %d %Y", "%b %d %Y"]
            for f in fmts:
                try:
                    dt = datetime.strptime(candidate_clean.strip(), f)
                    return dt.strftime("%Y-%m-%d")
                except Exception:
                    continue
            return _clean_whitespace(candidate_clean)
    return "N/A"

# --------------------------
# Coordinates extraction
# --------------------------
def extract_coordinates(text: str) -> Tuple[str, str]:
    """
    Extract lat/lon either in decimal or DMS format.
    Returns (lat, lon) as strings or ("N/A","N/A").
    """
    if not text:
        return "N/A", "N/A"
    text = text.strip().replace(";", ",").replace("  ", " ")

    # decimal numbers
    matches = re.findall(r"(-?\d{1,3}\.\d+)", text)
    if len(matches) >= 2:
        lat, lon = matches[0], matches[1]
        try:
            lat_f, lon_f = float(lat), float(lon)
            if abs(lat_f) > 90 and abs(lon_f) <= 90:  # likely swapped
                lat_f, lon_f = lon_f, lat_f
            if not (-90 <= lat_f <= 90 and -180 <= lon_f <= 180):
                return "N/A", "N/A"
            return f"{lat_f:.6f}", f"{lon_f:.6f}"
        except:
            return "N/A", "N/A"

    # DMS fallback
    dms_pattern = r"(\d{1,3})[°\s]\s*(\d{1,2})['\s]?\s*([\d\.]+)\"?\s*([NS])?.*?(\d{1,3})[°\s]\s*(\d{1,2})['\s]?\s*([\d\.]+)\"?\s*([EW])?"
    m = re.search(dms_pattern, text, FLAGS)
    if m:
        try:
            lat_deg, lat_min, lat_sec, lat_dir = float(m.group(1)), float(m.group(2)), float(m.group(3)), m.group(4) or "S"
            lon_deg, lon_min, lon_sec, lon_dir = float(m.group(5)), float(m.group(6)), float(m.group(7)), m.group(8) or "E"
            lat = lat_deg + lat_min/60.0 + lat_sec/3600.0
            lon = lon_deg + lon_min/60.0 + lon_sec/3600.0
            if lat_dir.upper().startswith("S"): lat = -lat
            if lon_dir.upper().startswith("W"): lon = -lon
            return f"{lat:.6f}", f"{lon:.6f}"
        except:
            return "N/A", "N/A"

    return "N/A", "N/A"

# --------------------------
# Plot area conversion
# --------------------------
def extract_plot_area(text: str) -> Tuple[str, str]:
    if not text:
        return "N/A", "N/A"
    m_ha = re.search(r"([\d\.]+)\s*(?:hectares|hectare|ha)\b", text, FLAGS)
    m_ac = re.search(r"([\d\.]+)\s*(?:acres|acre)\b", text, FLAGS)
    ha = m_ha.group(1) if m_ha else "N/A"
    ac = m_ac.group(1) if m_ac else "N/A"
    try:
        if ha == "N/A" and ac != "N/A":
            ha_val = float(ac) * 0.404686
            ha = f"{ha_val:.6f}"
        if ac == "N/A" and ha != "N/A":
            ac_val = float(ha) / 0.404686
            ac = f"{ac_val:.6f}"
    except:
        pass
    return ha, ac

# --------------------------
# Bedrooms, parking, valuer
# --------------------------
def extract_bedrooms(text: str) -> Tuple[str, str]:
    if not text:
        return "N/A", "No"
    m = re.search(r"(\d{1,2})[-\s]?bedroom\b", text, FLAGS)
    bedrooms = m.group(1) if m else None
    if not bedrooms:
        words_to_nums = {"one":"1","two":"2","three":"3","four":"4","five":"5","six":"6","seven":"7","eight":"8","nine":"9","ten":"10"}
        m2 = re.search(r"\b(one|two|three|four|five|six|seven|eight|nine|ten)\b[-\s]?bedroom\b", text, FLAGS)
        bedrooms = words_to_nums.get(m2.group(1).lower(), "N/A") if m2 else "N/A"
    master = "Yes" if re.search(r"master.*en-?suite|en-?suite.*master", text, FLAGS) else "No"
    return _safe(bedrooms), _safe(master)

def extract_parking(text: str) -> str:
    if not text:
        return "N/A"
    m = re.search(r"(\d{1,2})\s*(?:No\.?|nos\.?|parking|parking lots|parking spaces|car spaces|car park)\b", text, FLAGS)
    if m:
        return m.group(1)
    m2 = re.search(r"\b(one|two|three|four|five)\b\s*(?:parking|car space|car spaces|parking lots)\b", text, FLAGS)
    if m2:
        words = {"one":"1","two":"2","three":"3","four":"4","five":"5"}
        return words.get(m2.group(1).lower(), "N/A")
    return "N/A"

def extract_valuer(text: str) -> Tuple[str, str, str]:
    name = quals = company = "N/A"
    m_comp = re.search(r"(?:NW Realite Limited|[A-Z][A-Za-z\s\.\-&]+(?:Ltd|Limited|Company))", text)
    if m_comp:
        company = _clean_whitespace(m_comp.group(0))
    m_sign = re.search(r"([A-Z][A-Za-z\s\.\-]{3,60})\s*[,;\-]?\s*(BA|B\.A|BSc|B\.Sc|Hons|MIS|GMISK|MISK)", text, FLAGS)
    if m_sign:
        name, quals = _clean_whitespace(m_sign.group(1)), _clean_whitespace(m_sign.group(2))
    if name == "N/A":
        m2 = re.search(r"Registered & Practicing Valuer\s*([A-Z][A-Za-z\s\.\-]{3,60})", text, FLAGS)
        if m2:
            name = _clean_whitespace(m2.group(1))
    return _safe(name), _safe(quals), _safe(company)

# --------------------------
# Internal finishes
# --------------------------
FINISH_TOKENS = [
    "ceramic", "tiles", "wardrobes", "cupboards", "stainless steel sink",
    "timber", "wooden", "ceramic worktops", "marble", "granite", "glass", "steel"
]

def extract_internal_finishes(text: str) -> str:
    if not text:
        return "N/A"
    text_lower = text.lower()
    found = [t for t in FINISH_TOKENS if t in text_lower]
    return ", ".join(found) if found else "N/A"

# --------------------------
# Safe first match utility
# --------------------------
def find_first(patterns: List[str], text: str) -> str:
    if not text:
        return "N/A"
    if not isinstance(patterns, list):
        patterns = [patterns]
    sanitized = [p for p in patterns if isinstance(p, str) and p != text]
    for p in sanitized:
        try:
            m = re.search(p, text, FLAGS)
        except re.error:
            continue
        if m:
            if m.groups():
                for g in m.groups():
                    if g and str(g).strip():
                        return _clean_whitespace(str(g))
                return _clean_whitespace(m.group(0))
            return _clean_whitespace(m.group(0))
    return "N/A"

# --------------------------
# Main extraction function
# --------------------------
def extract_data_points(full_text: str, file_path: str) -> Dict[str, str]:
    filename = os.path.basename(file_path) if file_path else "N/A"
    text = full_text or ""
    data = {k: "N/A" for k in [
        "FileName","Our_Ref","Valuer_Name","Valuer_Qualifications","Valuer_Company",
        "Market_Value_Kshs","Insurance_Value_Kshs","Forced_Sale_Value_Kshs","Open_Market_Rental_Value_Kshs",
        "Valuation_Date","Inspection_Date","Lease_Start_Date","Transfer_Date","Consent_To_Transfer_Date",
        "LR_No","IR_No","Title_No","Apartment_No","Unit_Type","Block","Floor_Level","Estate_Name",
        "County","Area_Neighborhood","Road_Access_Description","Distance_To_Landmark","Google_Coordinates_Lat","Google_Coordinates_Lon",
        "Built_Up_Area_SqFt","Plot_Area_Ha","Plot_Area_Acres","Bedrooms","Master_EnSuite","Parking_Spaces","Balcony_Present","Accommodation_Summary","Condition","Occupancy_Status","Internal_Finishes",
        "Tenure","Lease_Term_Remaining","Encumbrances","Registered_Proprietor","Page_Count","Notes"
    ]}
    data["FileName"] = filename
    data["Our_Ref"] = _safe(find_first([r"Our Ref[:\s]*([\w\/\-\.\d]+)", r"Reference[:\s]*([\w\/\-\.\d]+)"], text))
    
    # Monetary
    data["Market_Value_Kshs"] = normalize_number(find_first([r"(?:Current\s+)?Market\s+Value[^\d\n\r]{0,40}([\d\.,\/=\sKShskshs]+)", r"Market Value[^\d\n\r]{0,40}KShs\.?\s*([\d\.,\/=\s]+)"], text))
    data["Insurance_Value_Kshs"] = normalize_number(find_first([r"Insurance Value[^\d\n\r]{0,40}KShs\.?\s*([\d\.,\/=\s]+)", r"Insurance\s*Value[^\d\n\r]{0,40}([\d\.,\/=\s]+)"], text))
    data["Forced_Sale_Value_Kshs"] = normalize_number(find_first([r"Forced Sale Value[^\d]{0,40}([\d\.,\/=\sKShs]+)", r"Forced Sale[^\d]{0,40}([\d\.,\/=\sKShs]+)"], text))
    data["Open_Market_Rental_Value_Kshs"] = normalize_number(find_first([r"Open Market Rental Value[^\d]{0,40}([\d\.,\/=\sKShs]+)", r"Rental Value[^\d]{0,40}([\d\.,\/=\sKShs]+)"], text))

    # Dates
    data["Valuation_Date"] = fuzzy_date_search(text)
    data["Inspection_Date"] = fuzzy_date_search(find_first([r"inspected for valuation on\s*([^\n\r]{1,60})", r"DATE OF INSPECTION[:\s]*([^\n\r]{1,60})"], text))
    data["Lease_Start_Date"] = fuzzy_date_search(find_first([r"with effect from\s*([^\n\r]{1,40})", r"with effect from\s*([\d\/\-\s]{6,12})"], text))
    data["Transfer_Date"] = fuzzy_date_search(find_first([r"Date of Transfer\s*[:\s]*([^\n\r]{1,60})", r"Date of Transfer[^\n\r]{1,60}([\d\/\-\s\w,]+)"], text))
    data["Consent_To_Transfer_Date"] = fuzzy_date_search(find_first([r"Consent to Transfer\s*[:\s]*([^\n\r]{1,60})", r"CONSENT TO TRANSFER[^\n\r]{1,60}([\d\/\-\s\w,]+)"], text))

    # Identifiers
    data["LR_No"] = _safe(find_first([r"(?:L\.?R\.?\s*(?:No|Number|NO|NUMBER)\.?:?)\s*([\d\/\-]+)", r"LR\s*NO\.?\s*([\d\/\-]+)"], text))
    data["IR_No"] = _safe(find_first([r"(?:I\.?R\.?\s*(?:No|Number|NO|NUMBER)\.?:?)\s*([\d\/\-]+)", r"I\.R\. Number[:\s]*([\d\/\-]+)"], text))
    data["Title_No"] = _safe(find_first([r"TITLE\s*NO\.?:?\s*([\d\/\-]+)", r"Title No[:\s]*([\d\/\-]+)"], text))
    data["Apartment_No"] = _safe(find_first([r"APARTMENT\s*NO\.?\s*[:\-]?\s*([A-Z0-9\-\s\(\)]+)", r"Flat No\.?\s*([A-Z0-9\-\s\(\)]+)"], text))
    data["Unit_Type"] = _safe(find_first([r"\b(Apartment|Maisonette|Shop|Flat)\b"], text))
    data["Block"] = _safe(find_first([r"Block\s*([A-Z0-9\-]+)", r"Block\s*([A-Z])\b"], text))
    data["Floor_Level"] = _safe(find_first([r"(Ground|First|Second|Third|Basement|Upper)\s+floor", r"on the\s+(ground|first|second|third)\s+floor"], text))

    # Estate / County / Area
    data["Estate_Name"] = _safe(find_first([r"(SIMBA VILLAS)", r"Estate\s*[:\s]*([A-Za-z0-9\s]+(?:VILLAS|ESTATE|COURT|GARDENS)?)", r"([\w\s]+(?:VILLAS|ESTATE|COURT|MAISONETTES|COMPLEX))"], text))
    county = find_first([r"([A-Za-z\s]{3,30}County)", r"([A-Za-z\s]{2,30}\s+County)", r"(NAIROBI COUNTY)"], text)
    if county == "N/A":
        mcounty = re.search(r"([A-Za-z]{3,30})\s+COUNTY", text, FLAGS)
        county = (mcounty.group(1).title() + " County") if mcounty else "N/A"
    data["County"] = _safe(county)
    data["Area_Neighborhood"] = _safe(find_first([r"Embakasi Area|([A-Za-z\s]+ Area)", r"Area[:\s]*([A-Za-z\s]+)"], text))

    # Road & distances
    data["Road_Access_Description"] = _safe(find_first([r"approximately\s*[\d,\.]+\s*meters\s*off\s*([A-Za-z0-9\s]+(?:Road|Rd))", r"along\s*([A-Za-z0-9\s]+(?:Road|Rd))"], text))
    data["Distance_To_Landmark"] = _safe(find_first([r"approximately\s*([\d,\.]+)\s*(meters|km)", r"distance[:\s]*([\d,\.]+)\s*(meters|km)"], text))

    # Google coordinates
    lat, lon = extract_coordinates(text)
    data["Google_Coordinates_Lat"], data["Google_Coordinates_Lon"] = lat, lon

    # Areas
    data["Built_Up_Area_SqFt"] = _safe(find_first([r"Built[-\s]?up\s*Area[:\s]*([\d\.,]+)\s*sq(?:\.|uare)?\s*ft", r"Floor area[:\s]*([\d\.,]+)\s*sq(?:\.|uare)?\s*ft"], text))
    ha, ac = extract_plot_area(text)
    data["Plot_Area_Ha"], data["Plot_Area_Acres"] = ha, ac

    # Bedrooms, Parking
    bedrooms, master = extract_bedrooms(text)
    data["Bedrooms"], data["Master_EnSuite"] = bedrooms, master
    data["Parking_Spaces"] = extract_parking(text)

    # Internal finishes
    data["Internal_Finishes"] = extract_internal_finishes(text)

    # Valuer
    valuer_name, valuer_qual, valuer_comp = extract_valuer(text)
    data["Valuer_Name"], data["Valuer_Qualifications"], data["Valuer_Company"] = valuer_name, valuer_qual, valuer_comp

    # Notes: missing critical fields
    required_fields = [
        "Our_Ref","Valuer_Name","Valuer_Company","Market_Value_Kshs","Valuation_Date","LR_No","Title_No"
    ]
    missing = [f for f in required_fields if data[f] in ("N/A","")]
    data["Notes"] = f"Missing important fields: {', '.join(missing)}; Total missing: {len(missing)}" if missing else "All key fields present"

    return data
