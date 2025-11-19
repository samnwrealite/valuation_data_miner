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
        # remove trailing common markers ("/=", "/ =", "KShs", "kshs", etc.)
        s = re.sub(r'(?i)kshs\.?', '', s)
        s = re.sub(r'[/=]', '', s)
        # remove any characters except digits, comma and dot
        s = re.sub(r'[^0-9\.,]', '', s)
        # if there are both dots and commas, remove both separators
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
            # Try common formats
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
    text = text.strip()

    # decimal match: -1.30969, 36.92089 or 1.30969 36.92089
    dec_match = re.search(r"(-?\d{1,3}\.\d+)\s*[,;\s]\s*(-?\d{1,3}\.\d+)", text)
    if dec_match:
        return dec_match.group(1), dec_match.group(2)

    # DMS pattern e.g. 1°18'34.9"S 36°55'11.3"E
    dms_pattern = r"(\d{1,3})[°\s]\s*(\d{1,2})['\s]?\s*([\d\.]+)\"?\s*([NS])?.*?(\d{1,3})[°\s]\s*(\d{1,2})['\s]?\s*([\d\.]+)\"?\s*([EW])?"
    m = re.search(dms_pattern, text, FLAGS)
    if m:
        try:
            lat_deg = float(m.group(1)); lat_min = float(m.group(2)); lat_sec = float(m.group(3)); lat_dir = m.group(4) or "S"
            lon_deg = float(m.group(5)); lon_min = float(m.group(6)); lon_sec = float(m.group(7)); lon_dir = m.group(8) or "E"
            lat = lat_deg + lat_min/60.0 + lat_sec/3600.0
            lon = lon_deg + lon_min/60.0 + lon_sec/3600.0
            if lat_dir.upper().startswith("S"): lat = -lat
            if lon_dir.upper().startswith("W"): lon = -lon
            return f"{lat:.6f}", f"{lon:.6f}"
        except Exception:
            return "N/A", "N/A"
    return "N/A", "N/A"

# --------------------------
# Plot area conversion
# --------------------------
def extract_plot_area(text: str) -> Tuple[str, str]:
    """
    Return (ha, acres) if found or convertible, else ("N/A","N/A")
    """
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
    except Exception:
        pass
    return ha, ac

# --------------------------
# Bedrooms, parking, valuer
# --------------------------
def extract_bedrooms(text: str) -> Tuple[str, str]:
    """
    Return (bedrooms_count, master_ensuite_flag)
    """
    if not text:
        return "N/A", "No"
    m = re.search(r"(\b\d{1,2}\b)\s*(?:-)?\s*(?:bedroom|bedrooms|bedroomed)\b", text, FLAGS)
    if m:
        bedrooms = m.group(1)
    else:
        words_to_nums = {"one":"1","two":"2","three":"3","four":"4","five":"5","six":"6","seven":"7","eight":"8","nine":"9","ten":"10"}
        m2 = re.search(r"\b(one|two|three|four|five|six|seven|eight|nine|ten)\b\s*(?:-)?\s*(?:bedroom|bedrooms|bedroomed)\b", text, FLAGS)
        bedrooms = words_to_nums.get(m2.group(1).lower(), "N/A") if m2 else "N/A"
    master = "Yes" if re.search(r"master.*en-?suite|master\s+en[-\s]?suite|en-?suite\s+master", text, FLAGS) else "No"
    return _safe(bedrooms), master

def extract_parking(text: str) -> str:
    """
    Return parking count or "N/A"
    """
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
    """
    Attempts to find valuer name, qualifications and company.
    """
    if not text:
        return "N/A", "N/A", "N/A"
    company = "N/A"; name = "N/A"; quals = "N/A"
    m_comp = re.search(r"For and on behalf of\s*([A-Za-z0-9 &\.\-]+(?:Limited|Ltd|Company))", text, FLAGS)
    if m_comp:
        company = _clean_whitespace(m_comp.group(1))
    # look for a signature block: name on one line and qualifications next line
    m_sign = re.search(r"\n\s*([A-Z][A-Za-z\s\.\-]{3,60})\s*\n\s*([A-Za-z0-9\(\)\.,\s]{2,80}(?:Hon|Hons|BA|BSc|B\.A|B\.Sc|Bachelor|Registered|MIS|GMISK))", text, FLAGS)
    if m_sign:
        name = _clean_whitespace(m_sign.group(1)); quals = _clean_whitespace(m_sign.group(2))
        return _safe(name), _safe(quals), _safe(company)
    # fallback patterns
    m2 = re.search(r"Registered & Practicing Valuer\s*[\r\n]+([A-Z][A-Za-z\s\.\-]{3,60})", text, FLAGS)
    if m2:
        name = _clean_whitespace(m2.group(1))
    mq = re.search(r"([A-Z][A-Za-z\s\.\-]{3,60})\s*[,;\-]?\s*(BA|B\.A|BSc|B\.Sc|Bachelor of Real Estate|Hons|MIS|GMISK|MISK)", text, FLAGS)
    if mq:
        name = _clean_whitespace(mq.group(1)); quals = _clean_whitespace(mq.group(2))
    return _safe(name), _safe(quals), _safe(company)

# --------------------------
# SAFE find_first
# --------------------------
def find_first(patterns: List[str], text: str) -> str:
    """
    Try a list of regex patterns and return the first useful match.
    This function is defensive:
     - ensures patterns is a list
     - if the caller accidentally included `text` inside patterns, we ignore it
     - always returns a cleaned string or "N/A"
    """
    if not text:
        return "N/A"
    if not isinstance(patterns, list):
        patterns = [patterns]

    # sanitize patterns: remove any element equal to the text or non-string
    sanitized = [p for p in patterns if isinstance(p, str) and p != text]

    for p in sanitized:
        try:
            m = re.search(p, text, FLAGS)
        except re.error:
            # skip bad regex
            continue
        if m:
            # prefer first non-empty capturing group, else full match
            if m.groups():
                for g in m.groups():
                    if g and str(g).strip():
                        return _clean_whitespace(str(g))
                # fallback to full match
                return _clean_whitespace(m.group(0))
            return _clean_whitespace(m.group(0))
    return "N/A"

# --------------------------
# Main extraction function
# --------------------------
def extract_data_points(full_text: str, file_path: str) -> Dict[str, str]:
    """
    Extract all fields (Option A) and return a dict mapping field -> value (or "N/A").
    """
    filename = os.path.basename(file_path) if file_path else "N/A"
    text = full_text or ""
    data = {k: "N/A" for k in [
        "FileName","Our_Ref","Valuer_Name","Valuer_Qualifications","Valuer_Company",
        "Market_Value_Kshs","Insurance_Value_Kshs","Forced_Sale_Value_Kshs","Open_Market_Rental_Value_Kshs",
        "Valuation_Date","Inspection_Date","Lease_Start_Date","Transfer_Date","Consent_To_Transfer_Date",
        "LR_No","IR_No","Title_No","Apartment_No","Unit_Type","Block","Floor_Level","Estate_Name",
        "County","Area_Neighborhood","Road_Access_Description","Distance_To_Landmark","Google_Coordinates_Lat","Google_Coordinates_Lon",
        "Built_Up_Area_SqFt","Plot_Area_Ha","Plot_Area_Acres","Bedrooms","Master_EnSuite","Parking_Spaces","Balcony_Present","Accommodation_Summary","Condition","Occupancy_Status","Internal_Finishes",
        "Tenure","Lease_Term_Remaining","Encumbrances","Registered_Proprietor",
        "Page_Count","Notes"
    ]}

    data["FileName"] = filename

    # --- Basic refs ---
    data["Our_Ref"] = _safe(find_first([r"Our Ref[:\s]*([\w\/\-\.\d]+)", r"Reference[:\s]*([\w\/\-\.\d]+)"], text))

    # --- Monetary values ---
    mv_raw = find_first([
        r"(?:Current\s+)?Market\s+Value[^\d\n\r]{0,40}([\d\.,\/=\sKShskshs]+)",
        r"Market Value[^\d\n\r]{0,40}KShs\.?\s*([\d\.,\/=\s]+)"
    ], text)
    data["Market_Value_Kshs"] = normalize_number(mv_raw)

    ins_raw = find_first([r"Insurance Value[^\d\n\r]{0,40}KShs\.?\s*([\d\.,\/=\s]+)", r"Insurance\s*Value[^\d\n\r]{0,40}([\d\.,\/=\s]+)"], text)
    data["Insurance_Value_Kshs"] = normalize_number(ins_raw)

    forced_raw = find_first([r"Forced Sale Value[^\d]{0,40}([\d\.,\/=\sKShs]+)", r"Forced Sale[^\d]{0,40}([\d\.,\/=\sKShs]+)"], text)
    data["Forced_Sale_Value_Kshs"] = normalize_number(forced_raw)

    rent_raw = find_first([r"Open Market Rental Value[^\d]{0,40}([\d\.,\/=\sKShs]+)", r"Rental Value[^\d]{0,40}([\d\.,\/=\sKShs]+)"], text)
    data["Open_Market_Rental_Value_Kshs"] = normalize_number(rent_raw)

    # --- Dates ---
    data["Valuation_Date"] = fuzzy_date_search(text)
    insp_raw = find_first([r"inspected for valuation on\s*([^\n\r]{1,60})", r"DATE OF INSPECTION[:\s]*([^\n\r]{1,60})"], text)
    data["Inspection_Date"] = fuzzy_date_search(insp_raw) if insp_raw != "N/A" else "N/A"

    lease_raw = find_first([r"with effect from\s*([^\n\r]{1,40})", r"with effect from\s*([\d\/\-\s]{6,12})"], text)
    data["Lease_Start_Date"] = fuzzy_date_search(lease_raw) if lease_raw != "N/A" else "N/A"

    transfer_raw = find_first([r"Date of Transfer\s*[:\s]*([^\n\r]{1,60})", r"Date of Transfer[^\n\r]{1,60}([\d\/\-\s\w,]+)"], text)
    data["Transfer_Date"] = fuzzy_date_search(transfer_raw) if transfer_raw != "N/A" else "N/A"

    consent_raw = find_first([r"Consent to Transfer\s*[:\s]*([^\n\r]{1,60})", r"CONSENT TO TRANSFER[^\n\r]{1,60}([\d\/\-\s\w,]+)"], text)
    data["Consent_To_Transfer_Date"] = fuzzy_date_search(consent_raw) if consent_raw != "N/A" else "N/A"

    # --- Identifiers ---
    data["LR_No"] = _safe(find_first([r"(?:L\.?R\.?\s*(?:No|Number|NO|NUMBER)\.?:?)\s*([\d\/\-]+)", r"LR\s*NO\.?\s*([\d\/\-]+)"], text))
    data["IR_No"] = _safe(find_first([r"(?:I\.?R\.?\s*(?:No|Number|NO|NUMBER)\.?:?)\s*([\d\/\-]+)", r"I\.R\. Number[:\s]*([\d\/\-]+)"], text))
    data["Title_No"] = _safe(find_first([r"TITLE\s*NO\.?:?\s*([\d\/\-]+)", r"Title No[:\s]*([\d\/\-]+)"], text))

    data["Apartment_No"] = _safe(find_first([r"APARTMENT\s*NO\.?\s*[:\-]?\s*([A-Z0-9\-\s\(\)]+)", r"Flat No\.?\s*([A-Z0-9\-\s\(\)]+)"], text))
    data["Unit_Type"] = _safe(find_first([r"\b(Apartment|Maisonette|Shop|Flat)\b"], text))

    data["Block"] = _safe(find_first([r"Block\s*([A-Z0-9\-]+)", r"Block\s*([A-Z])\b"], text))
    data["Floor_Level"] = _safe(find_first([r"(Ground|First|Second|Third|Basement|Upper)\s+floor", r"on the\s+(ground|first|second|third)\s+floor"], text))

    # --- Estate / County / Area ---
    data["Estate_Name"] = _safe(find_first([
        r"(SIMBA VILLAS)",
        r"Estate\s*[:\s]*([A-Za-z0-9\s]+(?:VILLAS|ESTATE|COURT|GARDENS)?)",
        r"([\w\s]+(?:VILLAS|ESTATE|COURT|MAISONETTES|COMPLEX))"
    ], text))

    # County detection
    county = find_first([r"([A-Za-z\s]{3,30}County)", r"([A-Za-z\s]{2,30}\s+County)", r"(NAIROBI COUNTY)"], text)
    if county == "N/A":
        mcounty = re.search(r"([A-Za-z]{3,30})\s+COUNTY", text, FLAGS)
        county = (mcounty.group(1).title() + " County") if mcounty else "N/A"
    data["County"] = _safe(county)
    data["Area_Neighborhood"] = _safe(find_first([r"Embakasi Area|([A-Za-z\s]+ Area)", r"Area[:\s]*([A-Za-z\s]+)"], text))

    # --- Road & distances ---
    data["Road_Access_Description"] = _safe(find_first([
        r"approximately\s*[\d,\.]+\s*meters\s*off\s*([A-Za-z0-9\s]+(?:Road|Rd))",
        r"along\s*([A-Za-z0-9\s]+(?:Road|Rd))",
        r"situated along\s*([A-Za-z0-9\s]+(?:Road|Rd))"
    ], text))
    data["Distance_To_Landmark"] = _safe(find_first([
        r"([\d,\.]+\s*meters?\s*to\s*(?:the\s*)?[A-Za-z0-9\s,]+)",
        r"([\d,\.]+\s*m(?:eters?)\s*(?:to|from)\s*[A-Za-z0-9\s,]+)"
    ], text))

    # --- Google coordinates ---
    gblock = find_first([r"Google\s+coordinates[:\s]*([^\n\r]{0,120})", r"Google Map Excerpt[:\s]*([^\n\r]{0,120})", r"Google coordinates[^\n\r]{0,120}"], text)
    lat, lon = extract_coordinates(gblock if gblock != "N/A" else text)
    data["Google_Coordinates_Lat"] = _safe(lat)
    data["Google_Coordinates_Lon"] = _safe(lon)

    # --- Areas & internal features ---
    bmatch = re.search(r"(?:gross plinth area is approximately|built[- ]?up area is approximately|BUILT UP AREA[:\s]*)\s*([\d,\.]+)\s*(?:square feet|sq\. ft|sq ft|square\s*feet)", text, FLAGS)
    if bmatch:
        data["Built_Up_Area_SqFt"] = _clean_whitespace(bmatch.group(1)).replace(",", "")
    else:
        malt = re.search(r"(\d{3,5})\s*(?:sq\.?\s*ft|square\s*feet)", text, FLAGS)
        data["Built_Up_Area_SqFt"] = malt.group(1) if malt else "N/A"

    ha, ac = extract_plot_area(text)
    data["Plot_Area_Ha"] = _safe(ha)
    data["Plot_Area_Acres"] = _safe(ac)

    beds, master = extract_bedrooms(text)
    data["Bedrooms"] = _safe(beds)
    data["Master_EnSuite"] = _safe(master)

    data["Parking_Spaces"] = _safe(extract_parking(text))
    data["Balcony_Present"] = "Yes" if re.search(r"\bbalcony\b", text, FLAGS) else "No"

    data["Accommodation_Summary"] = _safe(find_first([r"Accommodation comprises\s*[:\-]?\s*(.+?)(?:\.\s|$|\n--- PAGE BREAK ---)", r"Accommodation comprises[^\n\r]+([^\n\r]+)"], text))

    # Condition & occupancy
    data["Condition"] = _safe(find_first([r"(?:in a|is in a)\s*(good|fair|poor|excellent)\s*state", r"(?:The apartment is in a|The property is in a)\s*(good|fair|poor|excellent)\s*state"], text))
    data["Occupancy_Status"] = _safe(find_first([r"(owner-occupied|owner occupied|tenant-occupied|tenant occupied|vacant|occupied)"], text))

    # Internal finishes
    finishes = []
    tokens = ["ceramic", "tiles", "wardrobes", "cupboards", "stainless steel sink", "timber", "wooden", "ceramic worktops"]
    lower_text = text.lower()
    for token in tokens:
        if token in lower_text:
            finishes.append(token)
    data["Internal_Finishes"] = _safe(", ".join(finishes)) if finishes else "N/A"

    # --- Tenure & encumbrances & proprietor ---
    data["Tenure"] = _safe(find_first([r"(leasehold interest|freehold interest|leasehold|freehold)"], text))

    mterm = re.search(r"(\d{1,3}\s*years)\s*with effect from\s*([^\n\r]{1,30})", text, FLAGS)
    if mterm:
        years = mterm.group(1).strip()
        start = fuzzy_date_search(mterm.group(2))
        data["Lease_Term_Remaining"] = f"{years} from {start}"
    else:
        data["Lease_Term_Remaining"] = "N/A"

    data["Encumbrances"] = _safe(find_first([r"Encumbrances\s*[:\s]*([^\n\r]{1,200})", r"Encumbrances\s*([^\n\r]{1,200})"], text))
    data["Registered_Proprietor"] = _safe(find_first([r"registered in the names? of\s*([A-Za-z0-9\s,\.&\-]+)\.", r"The subject lease is registered in the names? of\s*([A-Za-z0-9\s,\.&\-]+)\."], text))

    # Valuer
    v_name, v_quals, v_company = extract_valuer(text)
    data["Valuer_Name"] = _safe(v_name)
    data["Valuer_Qualifications"] = _safe(v_quals)
    data["Valuer_Company"] = _safe(v_company)

    # Page count (based on page breaker added by pdf_reader)
    data["Page_Count"] = str(text.count("--- PAGE BREAK ---") + 1 if text.strip() else 0)

    # Notes: quick debug summary
    missing = [k for k, v in data.items() if v in (None, "", "N/A") and k not in ("Notes", "FileName")]
    data["Notes"] = f"Missing fields count: {len(missing)}"

    return data
