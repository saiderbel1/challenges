import os

import fitz  # PyMuPDF

from intake_management import IntakeManager, ProcurementRequest


def extract_text_from_pdf(pdf_path: str) -> str:
    """Extract text from a PDF file using PyMuPDF."""
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


def display_result(result: ProcurementRequest, intake_manager: IntakeManager) -> None:
    """Display the extracted procurement request data."""
    print("\n" + "=" * 60)
    print("EXTRACTED PROCUREMENT REQUEST")
    print("=" * 60)
    print(f"Requestor Name: {result.requestor_name}")
    print(f"Requestor Department: {result.requestor_department}")
    print(f"Title/Description: {result.title}")
    print(f"Vendor Name: {result.vendor_name}")
    print(f"VAT ID: {result.vat_id}")
    commodity_name = intake_manager.get_commodity_group_name(result.commodity_group)
    print(f"Commodity Group: {result.commodity_group:03d} - {commodity_name}")
    print("-" * 60)
    print("ORDER LINES:")
    for i, line in enumerate(result.order_lines, 1):
        print(f"  {i}. {line.position_description}")
        print(f"     Unit: {line.unit}")
        print(f"     Unit Price: {line.unit_price:.2f}")
        print(f"     Amount: {line.amount:.2f}")
        print(f"     Total: {line.total_price:.2f}")
    print("-" * 60)
    print(f"TOTAL COST: {result.total_cost:.2f}")
    print("=" * 60)


def main():
    # Check for API key
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("Error: OPENAI_API_KEY environment variable is not set.")
        print("Please set it with: export OPENAI_API_KEY='your-api-key'")
        return

    print("=" * 60)
    print("PROCUREMENT REQUEST PARSER")
    print("=" * 60)

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

    # Extract text from PDF
    print("\nExtracting text from PDF...")
    try:
        pdf_text = extract_text_from_pdf(pdf_path)
    except FileNotFoundError as e:
        print(f"Error: {e}")
        return
    except Exception as e:
        print(f"Error reading PDF: {e}")
        return

    if not pdf_text.strip():
        print("Error: No text could be extracted from the PDF.")
        return

    # Initialize IntakeManager and extract procurement data
    print("Analyzing document with AI...")
    try:
        intake_manager = IntakeManager()
        extracted_data = intake_manager.extract_procurement_data(pdf_text)
    except Exception as e:
        print(f"Error during AI analysis: {e}")
        return

    # Combine extracted data with user input
    result = ProcurementRequest.from_extracted_data(
        extracted=extracted_data,
        requestor_name=requestor_name,
        requestor_department=department_name,
    )

    # Display results
    display_result(result, intake_manager)


if __name__ == "__main__":
    main()
