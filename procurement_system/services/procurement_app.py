import os

import fitz  # PyMuPDF

from data import DatabaseManager, RequestRepository
from intake_management import ExtractedProcurementData, IntakeManager, OCRAgent, ProcurementRequest, RequestStatus


class ProcurementApp:
    """Central application class that orchestrates procurement services."""

    def __init__(self):
        self.db_manager = DatabaseManager()
        self.db_manager.initialize_schema()
        self.repository = RequestRepository(self.db_manager)
        self.intake_manager = IntakeManager()
        self.ocr_agent = OCRAgent()

    def extract_text_from_pdf(self, pdf_path: str) -> str:
        """Extract text from a PDF file."""
        if not os.path.exists(pdf_path):
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")

        doc = fitz.open(pdf_path)
        text_parts = []

        for page_num in range(len(doc)):
            page = doc[page_num]
            text_parts.append(f"--- Page {page_num + 1} ---")
            text_parts.append(page.get_text())

        doc.close()
        return "\n".join(text_parts)

    def extract_text_from_pdf_bytes(self, pdf_bytes: bytes) -> str:
        """Extract text from PDF bytes (for file uploads)."""
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        text_parts = []

        for page_num in range(len(doc)):
            page = doc[page_num]
            text_parts.append(f"--- Page {page_num + 1} ---")
            text_parts.append(page.get_text())

        doc.close()
        return "\n".join(text_parts)

    def extract_procurement_data(self, pdf_text: str) -> ExtractedProcurementData:
        """Extract structured procurement data from PDF text using LLM."""
        return self.intake_manager.extract_procurement_data(pdf_text)

    def extract_procurement_data_ocr(self, pdf_path: str) -> ExtractedProcurementData:
        """Extract structured procurement data from PDF using OCR (Vision)."""
        return self.ocr_agent.extract_from_pdf_path(pdf_path)

    def extract_procurement_data_ocr_bytes(self, pdf_bytes: bytes) -> ExtractedProcurementData:
        """Extract structured procurement data from PDF bytes using OCR (Vision)."""
        return self.ocr_agent.extract_from_pdf_bytes(pdf_bytes)

    def create_request(
        self,
        extracted_data: ExtractedProcurementData,
        requestor_name: str,
        requestor_department: str,
    ) -> ProcurementRequest:
        """Create a ProcurementRequest from extracted data and user input."""
        return ProcurementRequest.from_extracted_data(
            extracted=extracted_data,
            requestor_name=requestor_name,
            requestor_department=requestor_department,
        )

    def save_request(self, request: ProcurementRequest) -> int:
        """Save a procurement request to the database. Returns the request ID."""
        return self.repository.save_request(request)

    def get_user_requests(self, requestor_name: str) -> list[tuple[int, ProcurementRequest]]:
        """Get all requests for a specific user. Returns list of (id, request) tuples."""
        return self.repository.load_requests_by_user(requestor_name)

    def get_commodity_group_name(self, group_id: int) -> str:
        """Get the commodity group name by ID."""
        return self.intake_manager.get_commodity_group_name(group_id)

    def get_commodity_groups(self) -> list[tuple[int, str]]:
        """Get all commodity groups as list of (id, name) tuples."""
        from intake_management.intake_manager import COMMODITY_GROUPS

        groups = []
        for category in COMMODITY_GROUPS["categories"]:
            for group in category["commodityGroups"]:
                group_id = int(group["id"])
                name = f"{group['name']} ({category['name']})"
                groups.append((group_id, name))
        return groups

    def get_all_requests(self) -> list[tuple[int, ProcurementRequest]]:
        """Get all requests (for management). Returns list of (id, request) tuples."""
        return self.repository.load_all_requests()

    def update_request_status(self, request_id: int, status: RequestStatus) -> bool:
        """Update the status of a request. Returns True if updated."""
        return self.repository.update_status(request_id, status)

    def close(self) -> None:
        """Close database connection."""
        self.db_manager.close()
