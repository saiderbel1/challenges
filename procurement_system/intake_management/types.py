from pydantic import BaseModel, Field


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
        )
