import re

import fitz  # PyMuPDF

from .types import ExtractedProcurementData
from .parser_agent import ParserAgent, COMMODITY_GROUPS, get_commodity_group_name
from .ocr_agent import OCRAgent


# VAT ID regex: DE followed by exactly 9 digits
VAT_REGEX = re.compile(r"^DE\d{9}$")


class ValidationResult:
    """Result of validating extracted procurement data."""

    def __init__(self, is_valid: bool, errors: list[str]):
        self.is_valid = is_valid
        self.errors = errors


class IntakeManager:
    """Orchestrates procurement data extraction with validation and fallback."""

    def __init__(self, model: str = "gpt-4o", temperature: float = 0):
        self.parser_agent = ParserAgent(model=model, temperature=temperature)
        self.ocr_agent = OCRAgent(model=model, temperature=temperature)

    def validate_extraction(self, data: ExtractedProcurementData) -> ValidationResult:
        """Validate extracted procurement data."""
        errors = []

        # Check for empty required fields
        if not data.title or not data.title.strip():
            errors.append("Title is empty")

        if not data.vendor_name or not data.vendor_name.strip():
            errors.append("Vendor name is empty")

        if not data.vat_id or not data.vat_id.strip():
            errors.append("VAT ID is empty")
        elif not VAT_REGEX.match(data.vat_id.strip()):
            errors.append(f"VAT ID '{data.vat_id}' does not match expected format (DE + 9 digits)")

        if not data.order_lines:
            errors.append("No order lines found")
        else:
            for i, line in enumerate(data.order_lines, 1):
                if not line.position_description or not line.position_description.strip():
                    errors.append(f"Order line {i}: position description is empty")
                if not line.unit or not line.unit.strip():
                    errors.append(f"Order line {i}: unit is empty")

        if data.commodity_group == 0:
            errors.append("Commodity group not identified")

        if data.total_cost == 0:
            errors.append("Total cost is zero")

        return ValidationResult(is_valid=len(errors) == 0, errors=errors)

    def _extract_text_from_pdf_path(self, pdf_path: str) -> str:
        """Extract text from a PDF file."""
        doc = fitz.open(pdf_path)
        text_parts = []
        for page_num in range(len(doc)):
            page = doc[page_num]
            text_parts.append(f"--- Page {page_num + 1} ---")
            text_parts.append(page.get_text())
        doc.close()
        return "\n".join(text_parts)

    def _extract_text_from_pdf_bytes(self, pdf_bytes: bytes) -> str:
        """Extract text from PDF bytes."""
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        text_parts = []
        for page_num in range(len(doc)):
            page = doc[page_num]
            text_parts.append(f"--- Page {page_num + 1} ---")
            text_parts.append(page.get_text())
        doc.close()
        return "\n".join(text_parts)

    def extract_from_pdf_path(self, pdf_path: str) -> ExtractedProcurementData:
        """Extract procurement data from PDF path with validation and OCR fallback."""
        # Step 1: Extract text and try ParserAgent
        pdf_text = self._extract_text_from_pdf_path(pdf_path)
        extracted = self.parser_agent.extract_procurement_data(pdf_text)

        # Step 2: Validate
        validation = self.validate_extraction(extracted)

        if validation.is_valid:
            return extracted

        print(f"Validation errors: {validation.errors}")

        # Step 3: Fallback to OCR
        return self.ocr_agent.extract_from_pdf_path(pdf_path)

    def extract_from_pdf_bytes(self, pdf_bytes: bytes) -> ExtractedProcurementData:
        """Extract procurement data from PDF bytes with validation and OCR fallback."""
        # Step 1: Extract text and try ParserAgent
        pdf_text = self._extract_text_from_pdf_bytes(pdf_bytes)
        extracted = self.parser_agent.extract_procurement_data(pdf_text)

        # Step 2: Validate
        validation = self.validate_extraction(extracted)

        if validation.is_valid:
            return extracted

        # Step 3: Fallback to OCR
        return self.ocr_agent.extract_from_pdf_bytes(pdf_bytes)

    def extract_procurement_data(self, pdf_text: str) -> ExtractedProcurementData:
        """Extract procurement data from PDF text (no OCR fallback available)."""
        return self.parser_agent.extract_procurement_data(pdf_text)

    def get_commodity_group_name(self, group_id: int) -> str:
        """Get the commodity group name by ID."""
        return get_commodity_group_name(group_id)
