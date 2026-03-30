import re
import tempfile

import pdftotext

from .types import (
    ExtractedProcurementData,
    OrderLine,
    ValidationIssue,
    ValidationIssueType,
    OCR_RECOVERABLE_ISSUES,
    INSPECTOR_RECOVERABLE_ISSUES,
)
from .types import COMMODITY_GROUPS, get_commodity_group_name
from .parser_agent import ParserAgent, InternalExtractedData, InternalOrderLine
from .ocr_agent import OCRAgent
from .inspector_agent import InspectorAgent
from .merger_agent import MergerAgent
from .classifier_agent import ClassifierAgent
from utils import display_extracted_data


VAT_REGEX = re.compile(r"^DE\d{9}$")


class ValidationResult:
    """Result of validating extracted procurement data."""

    def __init__(self, is_valid: bool, issues: list[ValidationIssue]):
        self.is_valid = is_valid
        self.issues = issues

    @property
    def errors(self) -> list[str]:
        """Backward-compatible list of error message strings."""
        return [issue.message for issue in self.issues]

    @property
    def issue_types(self) -> set[ValidationIssueType]:
        return {issue.issue_type for issue in self.issues}

    @property
    def needs_ocr(self) -> bool:
        return bool(self.issue_types & OCR_RECOVERABLE_ISSUES)

    @property
    def needs_inspector(self) -> bool:
        return bool(self.issue_types & INSPECTOR_RECOVERABLE_ISSUES)


class IntakeManager:
    """Orchestrates procurement data extraction with validation and fallback."""

    def __init__(self, model: str = "gpt-4o", temperature: float = 0):
        self.parser_agent = ParserAgent(model=model, temperature=temperature)
        self.ocr_agent = OCRAgent(model=model, temperature=temperature)
        self.merger_agent = MergerAgent(model=model, temperature=temperature)
        self.inspector_agent = InspectorAgent(model=model, temperature=temperature)
        self.classifier_agent = ClassifierAgent(model=model, temperature=temperature)

    def _display_internal_data(self, data: InternalExtractedData) -> None:
        """Display internal extracted data including is_alternative and reduction fields."""
        print("\n" + "=" * 60)
        print("INTERNAL EXTRACTED DATA (before filtering)")
        print("=" * 60)
        print(f"Vendor Name: {data.vendor_name}")
        print(f"VAT ID: {data.vat_id}")
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
        """Convert internal data to public ExtractedProcurementData, filtering out alternatives.
        Title and commodity_group are left as placeholders — filled by ClassifierAgent."""
        filtered_lines = [
            OrderLine(
                position_description=line.position_description,
                unit=line.unit,
                unit_price=line.unit_price,
                amount=line.amount,
                total_price=line.total_price,
            )
            for line in internal_data.order_lines
            if not line.is_alternative and line.amount > 0
        ]

        return ExtractedProcurementData(
            title="",
            vendor_name=internal_data.vendor_name,
            vat_id=internal_data.vat_id,
            commodity_group=0,
            order_lines=filtered_lines,
            additional_costs=internal_data.additional_costs,
            total_cost=internal_data.total_cost,
        )

    def validate_internal_extraction(self, data: InternalExtractedData, tolerance: float = 0.5) -> ValidationResult:
        """Validate internal extracted data, filtering alternatives and considering reductions.
        Title and commodity_group are not validated here — they are set by ClassifierAgent."""
        issues: list[ValidationIssue] = []

        if not data.vendor_name or not data.vendor_name.strip():
            issues.append(ValidationIssue(
                issue_type=ValidationIssueType.EMPTINESS,
                message="Vendor name is empty",
                field="vendor_name",
            ))

        if not data.vat_id or not data.vat_id.strip():
            issues.append(ValidationIssue(
                issue_type=ValidationIssueType.EMPTINESS,
                message="VAT ID is empty",
                field="vat_id",
            ))
        elif not VAT_REGEX.match(data.vat_id.strip()):
            issues.append(ValidationIssue(
                issue_type=ValidationIssueType.INVALID_VAT_ID,
                message=f"VAT ID '{data.vat_id}' does not match expected format (DE + 9 digits)",
                field="vat_id",
            ))

        non_alternative_lines = [line for line in data.order_lines if not line.is_alternative]

        if not non_alternative_lines:
            issues.append(ValidationIssue(
                issue_type=ValidationIssueType.EMPTINESS,
                message="No order lines found (excluding alternatives)",
                field="order_lines",
            ))
        else:
            order_lines_total = 0.0

            for i, line in enumerate(non_alternative_lines, 1):
                if not line.position_description or not line.position_description.strip():
                    issues.append(ValidationIssue(
                        issue_type=ValidationIssueType.EMPTINESS,
                        message=f"Order line {i}: position description is empty",
                        field="position_description",
                        line_index=i,
                    ))
                if line.amount > 0 and (not line.unit or not line.unit.strip()):
                    issues.append(ValidationIssue(
                        issue_type=ValidationIssueType.EMPTINESS,
                        message=f"Order line {i}: unit is empty",
                        field="unit",
                        line_index=i,
                    ))

                expected_total = line.unit_price * line.amount - line.reduction
                if abs(line.total_price - expected_total) > tolerance:
                    issues.append(ValidationIssue(
                        issue_type=ValidationIssueType.ORDER_LINE_SUM_INVALID,
                        message=(
                            f"Order line {i}: total_price ({line.total_price:.2f}) does not match "
                            f"unit_price * amount ({expected_total:.2f})"
                        ),
                        field="total_price",
                        line_index=i,
                    ))

                order_lines_total += line.total_price

            expected_total_cost = order_lines_total + data.additional_costs
            if abs(data.total_cost - expected_total_cost) > tolerance:
                issues.append(ValidationIssue(
                    issue_type=ValidationIssueType.TOTAL_SUM_INVALID,
                    message=(
                        f"Total cost ({data.total_cost:.2f}) does not match "
                        f"order lines total ({order_lines_total:.2f}) + additional costs ({data.additional_costs:.2f}) "
                        f"= {expected_total_cost:.2f}"
                    ),
                    field="total_cost",
                ))

        if data.total_cost == 0:
            issues.append(ValidationIssue(
                issue_type=ValidationIssueType.EMPTINESS,
                message="Total cost is zero",
                field="total_cost",
            ))

        return ValidationResult(is_valid=len(issues) == 0, issues=issues)

    def validate_public_data(self, data: ExtractedProcurementData, tolerance: float = 0.5) -> ValidationResult:
        """Validate public extracted data (after merge). Only checks sum calculations."""
        issues: list[ValidationIssue] = []

        if not data.order_lines:
            issues.append(ValidationIssue(
                issue_type=ValidationIssueType.EMPTINESS,
                message="No order lines found",
                field="order_lines",
            ))
        else:
            order_lines_total = 0.0

            for i, line in enumerate(data.order_lines, 1):
                expected_total = line.unit_price * line.amount
                if abs(line.total_price - expected_total) > tolerance:
                    issues.append(ValidationIssue(
                        issue_type=ValidationIssueType.ORDER_LINE_SUM_INVALID,
                        message=(
                            f"Order line {i}: total_price ({line.total_price:.2f}) does not match "
                            f"unit_price * amount ({expected_total:.2f})"
                        ),
                        field="total_price",
                        line_index=i,
                    ))

                order_lines_total += line.total_price

            expected_total_cost = order_lines_total + data.additional_costs
            if abs(data.total_cost - expected_total_cost) > tolerance:
                issues.append(ValidationIssue(
                    issue_type=ValidationIssueType.TOTAL_SUM_INVALID,
                    message=(
                        f"Total cost ({data.total_cost:.2f}) does not match "
                        f"order lines total ({order_lines_total:.2f}) + additional costs ({data.additional_costs:.2f}) "
                        f"= {expected_total_cost:.2f}"
                    ),
                    field="total_cost",
                ))

        return ValidationResult(is_valid=len(issues) == 0, issues=issues)

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

    def _run_inspector(
        self, pdf_text: str, validation: ValidationResult, data: ExtractedProcurementData,
    ) -> ExtractedProcurementData:
        """Run InspectorAgent for sum-related validation issues."""
        print("\nSum errors detected. Invoking InspectorAgent...")
        inspection_result = self.inspector_agent.inspect(
            pdf_text=pdf_text,
            errors=validation.errors,
            extracted_data=data,
        )

        print("\n[InspectorAgent Result]")
        print(f"Was corrected: {inspection_result.was_corrected}")
        print(f"Confidence: {inspection_result.confidence:.2f}")
        print(f"Rationale: {inspection_result.rationale}")

        if inspection_result.was_corrected:
            print("\nUsing corrected data from InspectorAgent")
            display_extracted_data(inspection_result.corrected_data)
            return inspection_result.corrected_data

        return data

    def _classify_and_return(self, data: ExtractedProcurementData) -> ExtractedProcurementData:
        """Final step: run ClassifierAgent to fill in title and commodity_group."""
        print("\nClassifying procurement request...")
        classified = self.classifier_agent.classify(data)
        display_extracted_data(classified)
        return classified

    def extract_from_pdf_path(self, pdf_path: str) -> ExtractedProcurementData:
        """Extract procurement data from PDF path with validation, merge, and inspection."""
        pdf_text = self._extract_text_from_pdf_path(pdf_path)
        internal_data = self.parser_agent.extract_procurement_data(pdf_text)

        print("\n[ParserAgent Result]")
        self._display_internal_data(internal_data)

        validation = self.validate_internal_extraction(internal_data)

        if validation.is_valid:
            print("\nValidation: PASSED")
            return self._classify_and_return(self._convert_to_public_data(internal_data))

        print("\nValidation: FAILED")
        for issue in validation.issues:
            print(f"  [{issue.issue_type.value}] {issue.message}")

        parsed_public_data = self._convert_to_public_data(internal_data)

        if not validation.needs_ocr:
            if validation.needs_inspector:
                return self._classify_and_return(
                    self._run_inspector(pdf_text, validation, parsed_public_data),
                )
            print("\nReturning parsed data (best effort)")
            return self._classify_and_return(parsed_public_data)

        print("\nRunning OCR (missing data / VAT issues detected)...")
        ocr_text = self.ocr_agent.extract_text_from_pdf_path(pdf_path)
        print("\n[OCR Text]")
        print(ocr_text)

        print("\nParsing OCR text...")
        ocr_internal = self.parser_agent.extract_procurement_data(ocr_text)
        print("\n[OCR → ParserAgent Result]")
        self._display_internal_data(ocr_internal)

        ocr_public = self._convert_to_public_data(ocr_internal)

        print("\nInvoking MergerAgent...")
        merge_result = self.merger_agent.merge(
            issues=validation.issues,
            parsed_data=parsed_public_data,
            ocr_data=ocr_public,
        )

        print("\n[MergerAgent Result]")
        print(f"Fields from OCR: {merge_result.fields_from_ocr}")
        print(f"Rationale: {merge_result.rationale}")
        print("\nMerged Data:")
        display_extracted_data(merge_result.merged_data)

        merged_validation = self.validate_public_data(merge_result.merged_data)

        if merged_validation.is_valid:
            print("\nMerged Validation: PASSED")
            return self._classify_and_return(merge_result.merged_data)

        print("\nMerged Validation: FAILED")
        for issue in merged_validation.issues:
            print(f"  [{issue.issue_type.value}] {issue.message}")

        if merged_validation.needs_inspector:
            return self._classify_and_return(
                self._run_inspector(pdf_text, merged_validation, merge_result.merged_data),
            )

        print("\nReturning merged data (best effort)")
        return self._classify_and_return(merge_result.merged_data)

    def extract_from_pdf_bytes(self, pdf_bytes: bytes) -> ExtractedProcurementData:
        """Extract procurement data from PDF bytes with validation, merge, and inspection."""
        pdf_text = self._extract_text_from_pdf_bytes(pdf_bytes)
        internal_data = self.parser_agent.extract_procurement_data(pdf_text)

        print("\n[ParserAgent Result]")
        self._display_internal_data(internal_data)

        validation = self.validate_internal_extraction(internal_data)

        if validation.is_valid:
            print("\nValidation: PASSED")
            return self._classify_and_return(self._convert_to_public_data(internal_data))

        print("\nValidation: FAILED")
        for issue in validation.issues:
            print(f"  [{issue.issue_type.value}] {issue.message}")

        parsed_public_data = self._convert_to_public_data(internal_data)

        if not validation.needs_ocr:
            if validation.needs_inspector:
                return self._classify_and_return(
                    self._run_inspector(pdf_text, validation, parsed_public_data),
                )
            print("\nReturning parsed data (best effort)")
            return self._classify_and_return(parsed_public_data)

        print("\nRunning OCR (missing data / VAT issues detected)...")
        ocr_text = self.ocr_agent.extract_text_from_pdf_bytes(pdf_bytes)
        print("\n[OCR Text]")
        print(ocr_text)

        print("\nParsing OCR text...")
        ocr_internal = self.parser_agent.extract_procurement_data(ocr_text)
        print("\n[OCR → ParserAgent Result]")
        self._display_internal_data(ocr_internal)

        ocr_public = self._convert_to_public_data(ocr_internal)

        print("\nInvoking MergerAgent...")
        merge_result = self.merger_agent.merge(
            issues=validation.issues,
            parsed_data=parsed_public_data,
            ocr_data=ocr_public,
        )

        print("\n[MergerAgent Result]")
        print(f"Fields from OCR: {merge_result.fields_from_ocr}")
        print(f"Rationale: {merge_result.rationale}")
        print("\nMerged Data:")
        display_extracted_data(merge_result.merged_data)

        merged_validation = self.validate_public_data(merge_result.merged_data)

        if merged_validation.is_valid:
            print("\nMerged Validation: PASSED")
            return self._classify_and_return(merge_result.merged_data)

        print("\nMerged Validation: FAILED")
        for issue in merged_validation.issues:
            print(f"  [{issue.issue_type.value}] {issue.message}")

        if merged_validation.needs_inspector:
            return self._classify_and_return(
                self._run_inspector(pdf_text, merged_validation, merge_result.merged_data),
            )

        print("\nReturning merged data (best effort)")
        return self._classify_and_return(merge_result.merged_data)

    def extract_procurement_data(self, pdf_text: str) -> ExtractedProcurementData:
        """Extract procurement data from PDF text (no OCR fallback available)."""
        internal_data = self.parser_agent.extract_procurement_data(pdf_text)
        return self._classify_and_return(self._convert_to_public_data(internal_data))

    def get_commodity_group_name(self, group_id: int) -> str:
        """Get the commodity group name by ID."""
        return get_commodity_group_name(group_id)
