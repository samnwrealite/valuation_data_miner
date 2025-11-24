"""
Small-scale CPU-based document processing pipeline using Docling
for extracting structured data from property valuation reports.
"""

from docling.document_converter import DocumentConverter, PdfFormatOption
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions, TableFormerMode
from docling.backend.pypdfium2_backend import PyPdfiumDocumentBackend
import json
from pathlib import Path
from typing import Dict, List, Any
import re
from datetime import datetime


class PropertyValuationExtractor:
    """Extract structured data from property valuation reports."""
    
    def __init__(self):
        # Configure Docling for CPU-only processing
        pipeline_options = PdfPipelineOptions()
        pipeline_options.do_ocr = True  # Enable OCR for scanned documents
        pipeline_options.do_table_structure = True  # Extract tables
        pipeline_options.table_structure_options.mode = TableFormerMode.FAST  # CPU-optimized
        
        # Initialize converter with CPU backend
        self.converter = DocumentConverter(
            format_options={
                InputFormat.PDF: PdfFormatOption(
                    pipeline_options=pipeline_options,
                    backend=PyPdfiumDocumentBackend  # CPU-based PDF backend
                )
            }
        )
    
    def process_document(self, pdf_path: str) -> Dict[str, Any]:
        """
        Process PDF and extract structured data.
        
        Args:
            pdf_path: Path to the PDF file
            
        Returns:
            Structured dictionary with extracted data
        """
        # Convert document
        result = self.converter.convert(pdf_path)
        
        # Extract text content
        full_text = result.document.export_to_markdown()
        
        # Extract structured data
        structured_data = {
            "metadata": self._extract_metadata(result, full_text),
            "property_details": self._extract_property_details(full_text),
            "title_information": self._extract_title_info(full_text),
            "valuation": self._extract_valuation(full_text),
            "improvements": self._extract_improvements(full_text),
            "location": self._extract_location(full_text),
            "tables": self._extract_tables(result),
            "raw_sections": self._extract_sections(full_text)
        }
        
        return structured_data
    
    def _extract_metadata(self, result, text: str) -> Dict[str, Any]:
        """Extract document metadata."""
        metadata = {
            "document_type": "Property Valuation Report",
            "extraction_date": datetime.now().isoformat(),
            "page_count": len(result.document.pages),
            "valuer_company": self._find_pattern(text, r"(NW Realite|N'W Realite)"),
            "report_number": self._find_pattern(text, r"(\d{3,}/\w+/\d+/\d+/\d+)")
        }
        
        # Extract inspection date
        date_match = re.search(r"(?:inspected|inspection).*?(\d{1,2}\s+\w+\s+\d{4})", text, re.IGNORECASE)
        if date_match:
            metadata["inspection_date"] = date_match.group(1)
        
        return metadata
    
    def _extract_property_details(self, text: str) -> Dict[str, Any]:
        """Extract core property details."""
        details = {}
        
        # Property reference
        lr_numbers = re.findall(r"L\.?R\.?\s*(?:No\.?|Number)?\s*(\d+/\d+(?:-\d+)?)", text)
        if lr_numbers:
            details["lr_numbers"] = list(set(lr_numbers))
        
        # Area measurements
        area_match = re.search(r"(\d+\.?\d*)\s*hectares.*?(\d+\.?\d*)\s*acres", text, re.IGNORECASE)
        if area_match:
            details["area"] = {
                "hectares": float(area_match.group(1)),
                "acres": float(area_match.group(2))
            }
        
        # Tenure
        tenure_match = re.search(r"(Leasehold|Freehold).*?(\d+)\s*years", text, re.IGNORECASE)
        if tenure_match:
            details["tenure"] = {
                "type": tenure_match.group(1),
                "term_years": int(tenure_match.group(2))
            }
        
        # Owner
        owner_match = re.search(r"registered.*?name.*?([A-Z][A-Z\s&]+(?:MINISTRIES|LIMITED|LTD|INC))", text)
        if owner_match:
            details["registered_owner"] = owner_match.group(1).strip()
        
        return details
    
    def _extract_title_info(self, text: str) -> List[Dict[str, Any]]:
        """Extract individual title information."""
        titles = []
        
        # Look for title tables or structured title info
        title_pattern = r"(\d+/\d+).*?Leasehold.*?(\d+)\s*years.*?KShs?\.\s*([\d,]+)"
        matches = re.finditer(title_pattern, text, re.IGNORECASE)
        
        for match in matches:
            titles.append({
                "lr_number": match.group(1),
                "tenure_years": int(match.group(2)),
                "ground_rent": match.group(3).replace(",", "")
            })
        
        return titles
    
    def _extract_valuation(self, text: str) -> Dict[str, Any]:
        """Extract valuation figures."""
        valuation = {}
        
        # Current market value
        market_value = re.search(r"Market\s*Value.*?KShs?\.?\s*([\d,]+)", text, re.IGNORECASE)
        if market_value:
            valuation["current_market_value"] = int(market_value.group(1).replace(",", ""))
        
        # Breakdown
        land_value = re.search(r"Land.*?KShs?\.?\s*([\d,]+)", text)
        if land_value:
            valuation["land_value"] = int(land_value.group(1).replace(",", ""))
        
        developments_value = re.search(r"Developments.*?KShs?\.?\s*([\d,]+)", text)
        if developments_value:
            valuation["developments_value"] = int(developments_value.group(1).replace(",", ""))
        
        return valuation
    
    def _extract_improvements(self, text: str) -> Dict[str, Any]:
        """Extract building and improvement details."""
        improvements = {
            "buildings": [],
            "other_structures": []
        }
        
        # Look for building descriptions
        if "townhouse" in text.lower():
            # Extract townhouse details
            bedrooms = re.search(r"(\d+)\s*(?:No\.|Number)?\s*bedroom", text, re.IGNORECASE)
            built_up = re.search(r"(\d+,?\d*)\s*sq\.?\s*ft", text, re.IGNORECASE)
            
            improvements["buildings"].append({
                "type": "Townhouse",
                "quantity": self._find_pattern(text, r"(\d+)\s*(?:No\.).*?[Tt]ownhouse", default="2"),
                "bedrooms": bedrooms.group(1) if bedrooms else None,
                "built_up_area_sqft": built_up.group(1).replace(",", "") if built_up else None,
                "condition": self._find_pattern(text, r"(good|fair|poor)\s*condition", default="Not specified")
            })
        
        return improvements
    
    def _extract_location(self, text: str) -> Dict[str, Any]:
        """Extract location information."""
        location = {}
        
        # County and area
        county_match = re.search(r"(\w+)\s*County", text)
        if county_match:
            location["county"] = county_match.group(1)
        
        # Township/area
        area_match = re.search(r"(Kikuyu|Ondiri|[\w\s]+)\s*(?:Township|Area)", text)
        if area_match:
            location["area"] = area_match.group(1).strip()
        
        # GPS coordinates
        coords_match = re.search(r"(\d+°\d+'[\d.]+\"[SN])\s*(\d+°\d+'[\d.]+\"[EW])", text)
        if coords_match:
            location["coordinates"] = {
                "latitude": coords_match.group(1),
                "longitude": coords_match.group(2)
            }
        
        return location
    
    def _extract_tables(self, result) -> List[Dict[str, Any]]:
        """Extract tables from document, safely skipping non-page entries."""
        tables = []

        for page in result.document.pages:

            # 🔥 Fix: Docling sometimes returns integers inside pages[]
            if not hasattr(page, "tables"):
                continue

            if not page.tables:
                continue

            for table in page.tables:

                table_data = {
                    "page": getattr(page, "page_no", None),
                    "headers": [],
                    "rows": [],
                    "raw_content": str(table)
                }

                # If table supports structured cells, extract them
                if hasattr(table, "cells"):
                    rows = []
                    for row in table.cells:
                        rows.append([cell.text for cell in row])
                    table_data["rows"] = rows

                tables.append(table_data)

        return tables

    
    def _extract_sections(self, text: str) -> Dict[str, str]:
        """Extract major document sections."""
        sections = {}
        
        # Define section patterns
        section_patterns = [
            "TERMS OF REFERENCE",
            "LIMITING CONDITIONS",
            "REPORT AND VALUATION",
            "SITUATION",
            "TITLE DETAILS",
            "PLOT AREA",
            "IMPROVEMENTS",
            "CONDITION",
            "GENERAL REMARKS",
            "VALUATION"
        ]
        
        for section in section_patterns:
            pattern = f"{section}:?(.*?)(?={'|'.join(section_patterns)}|$)"
            match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
            if match:
                sections[section.lower().replace(" ", "_")] = match.group(1).strip()[:500]  # Limit length
        
        return sections
    
    def _find_pattern(self, text: str, pattern: str, default: str = None) -> str:
        """Helper to find regex pattern."""
        match = re.search(pattern, text, re.IGNORECASE)
        return match.group(1) if match else default
    
    def save_json(self, data: Dict[str, Any], output_path: str):
        """Save extracted data to JSON file."""
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"Data saved to {output_path}")


def main():
    """Example usage - processes first PDF found in data directory."""
    
    # Path to data directory
    data_dir = Path(r"C:\Users\samue\Documents\Work\Code\valuation_data_miner\data")
    
    # Find first PDF in directory
    pdf_files = list(data_dir.glob("*.pdf"))
    
    if not pdf_files:
        print(f"No PDF files found in {data_dir}")
        return
    
    pdf_path = pdf_files[0]
    print(f"Found {len(pdf_files)} PDF file(s) in directory")
    print(f"Processing: {pdf_path.name}\n")
    
    # Initialize extractor
    extractor = PropertyValuationExtractor()
    
    try:
        structured_data = extractor.process_document(str(pdf_path))
        
        # Save to JSON in same directory
        output_path = data_dir / f"{pdf_path.stem}_extracted.json"
        extractor.save_json(structured_data, str(output_path))
        
        # Print summary
        print("\n" + "="*60)
        print("EXTRACTION SUMMARY")
        print("="*60)
        print(f"Source File: {pdf_path.name}")
        print(f"Output File: {output_path.name}")
        print(f"\nProperty LR Numbers: {structured_data['property_details'].get('lr_numbers', 'N/A')}")
        print(f"Registered Owner: {structured_data['property_details'].get('registered_owner', 'N/A')}")
        
        if 'current_market_value' in structured_data['valuation']:
            val = structured_data['valuation']['current_market_value']
            print(f"Current Market Value: KShs {val:,}")
        else:
            print("Current Market Value: Not found")
        
        print(f"Location: {structured_data['location'].get('area', 'N/A')}, {structured_data['location'].get('county', 'N/A')}")
        print(f"Page Count: {structured_data['metadata'].get('page_count', 'N/A')}")
        print(f"Inspection Date: {structured_data['metadata'].get('inspection_date', 'N/A')}")
        print("="*60)
        
    except Exception as e:
        print(f"\n Error processing document: {e}")
        import traceback
        traceback.print_exc()
        raise


if __name__ == "__main__":
    main()