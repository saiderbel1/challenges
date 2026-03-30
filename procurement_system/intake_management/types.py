from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class RequestStatus(str, Enum):
    """Status of a procurement request."""

    OPEN = "Open"
    IN_PROGRESS = "In Progress"
    CLOSED = "Closed"


class ValidationIssueType(str, Enum):
    """Types of validation issues that can occur during data extraction."""

    EMPTINESS = "emptiness"
    INVALID_VAT_ID = "invalid_vat_id"
    ORDER_LINE_SUM_INVALID = "order_line_sum_invalid"
    TOTAL_SUM_INVALID = "total_sum_invalid"


OCR_RECOVERABLE_ISSUES = {
    ValidationIssueType.EMPTINESS,
    ValidationIssueType.INVALID_VAT_ID,
}

INSPECTOR_RECOVERABLE_ISSUES = {
    ValidationIssueType.ORDER_LINE_SUM_INVALID,
    ValidationIssueType.TOTAL_SUM_INVALID,
}


class ValidationIssue(BaseModel):
    """A single typed validation issue."""

    issue_type: ValidationIssueType
    message: str
    field: Optional[str] = None
    line_index: Optional[int] = None


class OrderLine(BaseModel):
    """A single line item in the procurement request."""

    position_description: str = Field(
        description="Full description of the item/service as provided in the document"
    )
    unit: str = Field(
        description="The unit of measure or quantity (e.g., licenses, pieces, hours, kg)"
    )
    unit_price: float = Field(description="Price per unit/item/service")
    amount: float = Field(description="Amount of items/services ordered")
    total_price: float = Field(description="Total price for this line (Unit Price x Amount)")


class ExtractedProcurementData(BaseModel):
    """Data extracted from procurement document by LLM (excludes user input fields)."""

    title: str = Field(
        description="Brief name or description of the product/service requested (can be inferred)"
    )
    vendor_name: str = Field(description="Name of the vendor")
    vat_id: str = Field(description="Umsatzsteuer-Identifikationsnummer (VAT ID)")
    commodity_group: int = Field(
        description="The commodity group ID (1-50) that best matches the requested items/services"
    )
    order_lines: list[OrderLine] = Field(description="List of order line items")
    additional_costs: float = Field(
        default=0.0,
        description="Sum of additional costs (VAT, taxes, shipping, fees) beyond order line totals"
    )
    total_cost: float = Field(description="Estimated total cost of the request")


class ProcurementRequest(BaseModel):
    """Complete procurement request including user input and extracted data."""

    requestor_name: str = Field(description="Full name of the person submitting the request")
    requestor_department: str = Field(description="Department of the requestor")
    title: str = Field(description="Brief name or description of the product/service requested")
    vendor_name: str = Field(description="Name of the vendor")
    vat_id: str = Field(description="Umsatzsteuer-Identifikationsnummer (VAT ID)")
    commodity_group: int = Field(description="The commodity group ID (1-50)")
    order_lines: list[OrderLine] = Field(description="List of order line items")
    total_cost: float = Field(description="Estimated total cost of the request")
    status: RequestStatus = Field(default=RequestStatus.OPEN, description="Current status of the request")

    @classmethod
    def from_extracted_data(
        cls,
        extracted: ExtractedProcurementData,
        requestor_name: str,
        requestor_department: str,
    ) -> "ProcurementRequest":
        """Create a ProcurementRequest by combining extracted data with user input."""
        return cls(
            requestor_name=requestor_name,
            requestor_department=requestor_department,
            title=extracted.title,
            vendor_name=extracted.vendor_name,
            vat_id=extracted.vat_id,
            commodity_group=extracted.commodity_group,
            order_lines=extracted.order_lines,
            total_cost=extracted.total_cost,
            status=RequestStatus.OPEN,
        )

COMMODITY_GROUPS = {
    "categories": [
        {
            "name": "General Services",
            "commodityGroups": [
                {"id": "001", "name": "Accommodation Rentals"},
                {"id": "002", "name": "Membership Fees"},
                {"id": "003", "name": "Workplace Safety"},
                {"id": "004", "name": "Consulting"},
                {"id": "005", "name": "Financial Services"},
                {"id": "006", "name": "Fleet Management"},
                {"id": "007", "name": "Recruitment Services"},
                {"id": "008", "name": "Professional Development"},
                {"id": "009", "name": "Miscellaneous Services"},
                {"id": "010", "name": "Insurance"},
            ],
        },
        {
            "name": "Facility Management",
            "commodityGroups": [
                {"id": "011", "name": "Electrical Engineering"},
                {"id": "012", "name": "Facility Management Services"},
                {"id": "013", "name": "Security"},
                {"id": "014", "name": "Renovations"},
                {"id": "015", "name": "Office Equipment"},
                {"id": "016", "name": "Energy Management"},
                {"id": "017", "name": "Maintenance"},
                {"id": "018", "name": "Cafeteria and Kitchenettes"},
                {"id": "019", "name": "Cleaning"},
            ],
        },
        {
            "name": "Publishing Production",
            "commodityGroups": [
                {"id": "020", "name": "Audio and Visual Production"},
                {"id": "021", "name": "Books/Videos/CDs"},
                {"id": "022", "name": "Printing Costs"},
                {"id": "023", "name": "Software Development for Publishing"},
                {"id": "024", "name": "Material Costs"},
                {"id": "025", "name": "Shipping for Production"},
                {"id": "026", "name": "Digital Product Development"},
                {"id": "027", "name": "Pre-production"},
                {"id": "028", "name": "Post-production Costs"},
            ],
        },
        {
            "name": "Information Technology",
            "commodityGroups": [
                {"id": "029", "name": "Hardware"},
                {"id": "030", "name": "IT Services"},
                {"id": "031", "name": "Software"},
            ],
        },
        {
            "name": "Logistics",
            "commodityGroups": [
                {"id": "032", "name": "Courier, Express, and Postal Services"},
                {"id": "033", "name": "Warehousing and Material Handling"},
                {"id": "034", "name": "Transportation Logistics"},
                {"id": "035", "name": "Delivery Services"},
            ],
        },
        {
            "name": "Marketing & Advertising",
            "commodityGroups": [
                {"id": "036", "name": "Advertising"},
                {"id": "037", "name": "Outdoor Advertising"},
                {"id": "038", "name": "Marketing Agencies"},
                {"id": "039", "name": "Direct Mail"},
                {"id": "040", "name": "Customer Communication"},
                {"id": "041", "name": "Online Marketing"},
                {"id": "042", "name": "Events"},
                {"id": "043", "name": "Promotional Materials"},
            ],
        },
        {
            "name": "Production",
            "commodityGroups": [
                {"id": "044", "name": "Warehouse and Operational Equipment"},
                {"id": "045", "name": "Production Machinery"},
                {"id": "046", "name": "Spare Parts"},
                {"id": "047", "name": "Internal Transportation"},
                {"id": "048", "name": "Production Materials"},
                {"id": "049", "name": "Consumables"},
                {"id": "050", "name": "Maintenance and Repairs"},
            ],
        },
    ]
}


def get_commodity_group_name(group_id: int) -> str:
    """Get the commodity group name by ID."""
    id_str = f"{group_id:03d}"
    for category in COMMODITY_GROUPS["categories"]:
        for group in category["commodityGroups"]:
            if group["id"] == id_str:
                return f"{group['name']} ({category['name']})"
    return "Unknown"
