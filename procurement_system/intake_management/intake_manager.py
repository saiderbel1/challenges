import re
import tempfile

import pdftotext

from .types import ExtractedProcurementData, OrderLine
from .parser_agent import ParserAgent, COMMODITY_GROUPS, get_commodity_group_name, InternalExtractedData, InternalOrderLine
from .ocr_agent import OCRAgent
from utils import display_extracted_data


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

    def _display_internal_data(self, data: InternalExtractedData) -> None:
        """Display internal extracted data including is_alternative and reduction fields."""
        print("\n" + "=" * 60)
        print("INTERNAL EXTRACTED DATA (before filtering)")
        print("=" * 60)
        print(f"Title/Description: {data.title}")
        print(f"Vendor Name: {data.vendor_name}")
        print(f"VAT ID: {data.vat_id}")
        commodity_name = get_commodity_group_name(data.commodity_group)
        print(f"Commodity Group: {data.commodity_group:03d} - {commodity_name}")
        print("-" * 60)
        print("ORDER LINES:")
        for i, line in enumerate(data.order_lines, 1):
            alt_marker = " [ALTERNATIVE]" if line.is_alternative else ""
            print(f"  {i}. {line.position_description}{alt_marker}")
            print(f"     Unit: {line.unit}")
            print(f"     Unit Price: {line.unit_price:.2f}")
            print(f"     Amount: {line.amount:.2f}")
            print(f"     Total: {line.total_price:.2f}")
            if line.reduction > 0:
                print(f"     Reduction: -{line.reduction:.2f}")
            print(f"     Is Alternative: {line.is_alternative}")
        print("-" * 60)
        print(f"ADDITIONAL COSTS: {data.additional_costs:.2f}")
        print(f"TOTAL COST: {data.total_cost:.2f}")
        print("=" * 60)

    def _convert_to_public_data(self, internal_data: InternalExtractedData) -> ExtractedProcurementData:
        """Convert internal data to public ExtractedProcurementData, filtering out alternatives."""
        # Filter out alternative order lines
        filtered_lines = [
            OrderLine(
                position_description=line.position_description,
                unit=line.unit,
                unit_price=line.unit_price,
                amount=line.amount,
                total_price=line.total_price,
            )
            for line in internal_data.order_lines
            if not line.is_alternative
        ]

        return ExtractedProcurementData(
            title=internal_data.title,
            vendor_name=internal_data.vendor_name,
            vat_id=internal_data.vat_id,
            commodity_group=internal_data.commodity_group,
            order_lines=filtered_lines,
            additional_costs=internal_data.additional_costs,
            total_cost=internal_data.total_cost,
        )

    def validate_internal_extraction(self, data: InternalExtractedData, tolerance: float = 0.5) -> ValidationResult:
        """Validate internal extracted data, filtering alternatives and considering reductions."""
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

        # Filter out alternatives for validation
        non_alternative_lines = [line for line in data.order_lines if not line.is_alternative]

        if not non_alternative_lines:
            errors.append("No order lines found (excluding alternatives)")
        else:
            order_lines_total = 0.0
            total_reductions = 0.0

            for i, line in enumerate(non_alternative_lines, 1):
                if not line.position_description or not line.position_description.strip():
                    errors.append(f"Order line {i}: position description is empty")
                if not line.unit or not line.unit.strip():
                    errors.append(f"Order line {i}: unit is empty")

                # Validate order line total calculation
                expected_total = line.unit_price * line.amount - line.reduction
                if abs(line.total_price - expected_total) > tolerance:
                    errors.append(
                        f"Order line {i}: total_price ({line.total_price:.2f}) does not match "
                        f"unit_price * amount ({expected_total:.2f})"
                    )

                order_lines_total += line.total_price

            # Validate overall total sum (considering reductions)
            expected_total_cost = order_lines_total + data.additional_costs
            if abs(data.total_cost - expected_total_cost) > tolerance:
                errors.append(
                    f"Total cost ({data.total_cost:.2f}) does not match "
                    f"order lines total ({order_lines_total:.2f}) + additional costs ({data.additional_costs:.2f}) "
                    f"- reductions ({total_reductions:.2f}) = {expected_total_cost:.2f}"
                )

        if data.commodity_group == 0:
            errors.append("Commodity group not identified")

        if data.total_cost == 0:
            errors.append("Total cost is zero")

        return ValidationResult(is_valid=len(errors) == 0, errors=errors)

    def _extract_text_from_pdf_path(self, pdf_path: str) -> str:
        """Extract text from a PDF file using pdftotext."""
        with open(pdf_path, "rb") as f:
            pdf = pdftotext.PDF(f, physical=True)

        text_parts = []
        for page_num, page_text in enumerate(pdf, 1):
            text_parts.append(f"--- Page {page_num} ---")
            text_parts.append(page_text)

        result = "\n".join(text_parts)
        print(result)
        return result

    def _extract_text_from_pdf_bytes(self, pdf_bytes: bytes) -> str:
        """Extract text from PDF bytes using pdftotext."""
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp.write(pdf_bytes)
            tmp_path = tmp.name

        try:
            with open(tmp_path, "rb") as f:
                pdf = pdftotext.PDF(f, physical=True)

            text_parts = []
            for page_num, page_text in enumerate(pdf, 1):
                text_parts.append(f"--- Page {page_num} ---")
                text_parts.append(page_text)

            return "\n".join(text_parts)
        finally:
            import os
            os.unlink(tmp_path)

    def extract_from_pdf_path(self, pdf_path: str) -> ExtractedProcurementData:
        """Extract procurement data from PDF path with validation and OCR fallback."""
        # Step 1: Extract text and try ParserAgent
        pdf_text = self._extract_text_from_pdf_path(pdf_path)
        internal_data = self.parser_agent.extract_procurement_data(pdf_text)

        # Display internal parser results before validation
        print("\n[ParserAgent Result]")
        self._display_internal_data(internal_data)

        # Step 2: Validate internal data
        validation = self.validate_internal_extraction(internal_data)

        if validation.is_valid:
            print("\nValidation: PASSED")
            # Convert to public data (filters out alternatives)
            return self._convert_to_public_data(internal_data)

        print(f"\nValidation: FAILED")
        print(f"Errors: {validation.errors}")
        print("\nFalling back to OCR...")

        # Step 3: Fallback to OCR
        return self.ocr_agent.extract_from_pdf_path(pdf_path)

    def extract_from_pdf_bytes(self, pdf_bytes: bytes) -> ExtractedProcurementData:
        """Extract procurement data from PDF bytes with validation and OCR fallback."""
        # Step 1: Extract text and try ParserAgent
        pdf_text = self._extract_text_from_pdf_bytes(pdf_bytes)
        internal_data = self.parser_agent.extract_procurement_data(pdf_text)

        # Display internal parser results before validation
        print("\n[ParserAgent Result]")
        self._display_internal_data(internal_data)

        # Step 2: Validate internal data
        validation = self.validate_internal_extraction(internal_data)

        if validation.is_valid:
            print("\nValidation: PASSED")
            # Convert to public data (filters out alternatives)
            return self._convert_to_public_data(internal_data)

        print(f"\nValidation: FAILED")
        print(f"Errors: {validation.errors}")
        print("\nFalling back to OCR...")

        # Step 3: Fallback to OCR
        return self.ocr_agent.extract_from_pdf_bytes(pdf_bytes)

    def extract_procurement_data(self, pdf_text: str) -> ExtractedProcurementData:
        """Extract procurement data from PDF text (no OCR fallback available)."""
        internal_data = self.parser_agent.extract_procurement_data(pdf_text)
        return self._convert_to_public_data(internal_data)

    def get_commodity_group_name(self, group_id: int) -> str:
        """Get the commodity group name by ID."""
        return get_commodity_group_name(group_id)
