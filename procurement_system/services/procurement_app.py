import os

from data import DatabaseManager, RequestRepository
from intake_management import (
    COMMODITY_GROUPS,
    ExtractedProcurementData,
    IntakeManager,
    ProcurementRequest,
    RequestStatus,
)


class ProcurementApp:
    """Central application class that orchestrates procurement services."""

    def __init__(self):
        self.db_manager = DatabaseManager()
        self.db_manager.initialize_schema()
        self.repository = RequestRepository(self.db_manager)
        self.intake_manager = IntakeManager()

    def extract_from_pdf_path(self, pdf_path: str) -> ExtractedProcurementData:
        """Extract procurement data from PDF path (with validation and OCR fallback)."""
        if not os.path.exists(pdf_path):
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")
        return self.intake_manager.extract_from_pdf_path(pdf_path)

    def extract_from_pdf_bytes(self, pdf_bytes: bytes) -> ExtractedProcurementData:
        """Extract procurement data from PDF bytes (with validation and OCR fallback)."""
        return self.intake_manager.extract_from_pdf_bytes(pdf_bytes)

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
