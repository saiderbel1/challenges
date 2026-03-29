import os

from intake_management import IntakeManager, ProcurementRequest
from data import DatabaseManager, RequestRepository


def display_request(request: ProcurementRequest, intake_manager: IntakeManager, request_id: int | None = None) -> None:
    """Display a procurement request."""
    print("\n" + "=" * 60)
    if request_id is not None:
        print(f"PROCUREMENT REQUEST (ID: {request_id})")
    else:
        print("EXTRACTED PROCUREMENT REQUEST")
    print("=" * 60)
    print(f"Requestor Name: {request.requestor_name}")
    print(f"Requestor Department: {request.requestor_department}")
    print(f"Title/Description: {request.title}")
    print(f"Vendor Name: {request.vendor_name}")
    print(f"VAT ID: {request.vat_id}")
    commodity_name = intake_manager.get_commodity_group_name(request.commodity_group)
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


def display_saved_requests(repository: RequestRepository, intake_manager: IntakeManager) -> None:
    """Display all saved procurement requests."""
    requests = repository.load_all_requests()

    if not requests:
        print("\nNo saved requests found.")
        return

    print(f"\nFound {len(requests)} saved request(s):")

    for request_id, request in requests:
        display_request(request, intake_manager, request_id)


def enter_new_request(repository: RequestRepository, intake_manager: IntakeManager) -> None:
    """Handle entering a new procurement request (with automatic OCR fallback)."""
    # Check for API key
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("Error: OPENAI_API_KEY environment variable is not set.")
        print("Please set it with: export OPENAI_API_KEY='your-api-key'")
        return

    # Get user input
    requestor_name = input("Enter your name: ").strip()
    if not requestor_name:
        print("Error: Name cannot be empty.")
        return

    department_name = input("Enter your department name: ").strip()
    if not department_name:
        print("Error: Department name cannot be empty.")
        return

    pdf_path = input("Enter the path to the PDF file: ").strip()
    if not pdf_path:
        print("Error: PDF path cannot be empty.")
        return

    if not os.path.exists(pdf_path):
        print(f"Error: PDF file not found: {pdf_path}")
        return

    # Extract procurement data (with automatic validation and OCR fallback)
    print("\nAnalyzing document with AI (will use OCR if text extraction fails validation)...")
    try:
        extracted_data = intake_manager.extract_from_pdf_path(pdf_path)
    except Exception as e:
        print(f"Error during AI analysis: {e}")
        return

    # Combine extracted data with user input
    request = ProcurementRequest.from_extracted_data(
        extracted=extracted_data,
        requestor_name=requestor_name,
        requestor_department=department_name,
    )

    # Save the request
    try:
        request_id = repository.save_request(request)
        print(f"\nRequest saved successfully with ID: {request_id}")
    except Exception as e:
        print(f"Error saving request: {e}")
        return

    # Display the result
    display_request(request, intake_manager, request_id)


def main():
    print("=" * 60)
    print("PROCUREMENT REQUEST SYSTEM")
    print("=" * 60)

    # Initialize database and repository
    db_manager = DatabaseManager()
    db_manager.initialize_schema()
    repository = RequestRepository(db_manager)
    intake_manager = IntakeManager()

    try:
        while True:
            print("\nWhat would you like to do?")
            print("1. Display saved requests")
            print("2. Enter a new request")
            print("3. Exit")

            choice = input("\nEnter your choice (1-3): ").strip()

            if choice == "1":
                display_saved_requests(repository, intake_manager)
            elif choice == "2":
                enter_new_request(repository, intake_manager)
            elif choice == "3":
                print("Goodbye!")
                break
            else:
                print("Invalid choice. Please enter 1, 2, or 3.")
    finally:
        db_manager.close()


if __name__ == "__main__":
    main()
