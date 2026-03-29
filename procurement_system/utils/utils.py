from intake_management.types import ExtractedProcurementData, ProcurementRequest
from intake_management.parser_agent import get_commodity_group_name


def display_extracted_data(data: ExtractedProcurementData) -> None:
    """Display extracted procurement data."""
    print("\n" + "=" * 60)
    print("EXTRACTED PROCUREMENT DATA")
    print("=" * 60)
    print(f"Title/Description: {data.title}")
    print(f"Vendor Name: {data.vendor_name}")
    print(f"VAT ID: {data.vat_id}")
    commodity_name = get_commodity_group_name(data.commodity_group)
    print(f"Commodity Group: {data.commodity_group:03d} - {commodity_name}")
    print("-" * 60)
    print("ORDER LINES:")
    for i, line in enumerate(data.order_lines, 1):
        print(f"  {i}. {line.position_description}")
        print(f"     Unit: {line.unit}")
        print(f"     Unit Price: {line.unit_price:.2f}")
        print(f"     Amount: {line.amount:.2f}")
        print(f"     Total: {line.total_price:.2f}")
    print("-" * 60)
    print(f"ADDITIONAL COSTS: {data.additional_costs:.2f}")
    print(f"TOTAL COST: {data.total_cost:.2f}")
    print("=" * 60)


def display_request(request: ProcurementRequest, request_id: int | None = None) -> None:
    """Display a procurement request."""
    print("\n" + "=" * 60)
    if request_id is not None:
        print(f"PROCUREMENT REQUEST (ID: {request_id})")
    else:
        print("PROCUREMENT REQUEST")
    print("=" * 60)
    print(f"Requestor Name: {request.requestor_name}")
    print(f"Requestor Department: {request.requestor_department}")
    print(f"Title/Description: {request.title}")
    print(f"Vendor Name: {request.vendor_name}")
    print(f"VAT ID: {request.vat_id}")
    commodity_name = get_commodity_group_name(request.commodity_group)
    print(f"Commodity Group: {request.commodity_group:03d} - {commodity_name}")
    print("-" * 60)
    print("ORDER LINES:")
    for i, line in enumerate(request.order_lines, 1):
        print(f"  {i}. {line.position_description}")
        print(f"     Unit: {line.unit}")
        print(f"     Unit Price: {line.unit_price:.2f}")
        print(f"     Amount: {line.amount:.2f}")
        print(f"     Total: {line.total_price:.2f}")
    print("-" * 60)
    print(f"TOTAL COST: {request.total_cost:.2f}")
    print("=" * 60)
