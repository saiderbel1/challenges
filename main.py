import json
import os

import fitz  # PyMuPDF
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field


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


def get_commodity_groups_text() -> str:
    """Convert commodity groups to text format for the prompt."""
    lines = ["Available Commodity Groups:"]
    for category in COMMODITY_GROUPS["categories"]:
        lines.append(f"\n{category['name']}:")
        for group in category["commodityGroups"]:
            lines.append(f"  - {group['id']}: {group['name']}")
    return "\n".join(lines)


def get_commodity_group_name(group_id: int) -> str:
    """Get the commodity group name by ID."""
    id_str = f"{group_id:03d}"
    for category in COMMODITY_GROUPS["categories"]:
        for group in category["commodityGroups"]:
            if group["id"] == id_str:
                return f"{group['name']} ({category['name']})"
    return "Unknown"

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


class ProcurementRequest(BaseModel):
    """Structured output for a procurement request."""

    requestor_name: str = Field(description="Full name of the person submitting the request")
    title: str = Field(
        description="Brief name or description of the product/service requested (can be inferred)"
    )
    vendor_name: str = Field(description="Name of the vendor")
    vat_id: str = Field(description="Umsatzsteuer-Identifikationsnummer (VAT ID)")
    requestor_department: str = Field(description="Department of the requestor from user input")
    commodity_group: int = Field(
        description="The commodity group ID (1-50) that best matches the requested items/services"
    )
    order_lines: list[OrderLine] = Field(description="List of order line items")
    total_cost: float = Field(description="Estimated total cost of the request")
    department: str = Field(
        description="The department of the requestor if mentioned in the document, empty string otherwise"
    )


EXTRACTION_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """You are a document parser specialized in procurement requests.
You are provided with extracted text data from a PDF of procurement requests.
Your task is to parse this text and extract structured information.

Rules:
- Extract information exactly as it appears in the document
- Only infer data when explicitly mentioned in the field description (e.g., title/short description)
- If a field is not found in the document, use an empty string for text fields or 0 for numeric fields
- For the 'department' field, only fill it if the department is mentioned IN THE DOCUMENT, otherwise leave empty
- The 'requestor_department' field should be filled with the department provided by the user
- Calculate total_price for each order line as unit_price * amount
- VAT ID (Umsatzsteuer-Identifikationsnummer) format is typically: DE followed by 9 digits

Order Line extraction rules:
- position_description: Include the FULL description of each line item as provided in the document
- unit: Extract the unit of measure (e.g., licenses, pieces, hours, kg, units, etc.)
- amount: Can be a decimal number (float), not just integers

Commodity Group selection:
- You MUST select the most appropriate commodity group from the list below
- Analyze the items/services in the procurement request and choose the best matching group
- Return the commodity group ID as an integer (e.g., 31 for Software, 29 for Hardware)

{commodity_groups}

User provided information:
- Requestor Name: {requestor_name}
- Requestor Department: {requestor_department}
""",
        ),
        ("human", "Please extract the procurement request information from the following PDF text:\n\n{pdf_text}"),
    ]
)


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


def extract_procurement_data(
    pdf_text: str, requestor_name: str, requestor_department: str
) -> ProcurementRequest:
    """Use LangChain with OpenAI to extract structured procurement data."""
    llm = ChatOpenAI(model="gpt-4o", temperature=0)
    structured_llm = llm.with_structured_output(ProcurementRequest)

    chain = EXTRACTION_PROMPT | structured_llm

    result = chain.invoke(
        {
            "pdf_text": pdf_text,
            "requestor_name": requestor_name,
            "requestor_department": requestor_department,
            "commodity_groups": get_commodity_groups_text(),
        }
    )

    return result


def display_result(result: ProcurementRequest) -> None:
    """Display the extracted procurement request data."""
    print("\n" + "=" * 60)
    print("EXTRACTED PROCUREMENT REQUEST")
    print("=" * 60)
    print(f"Requestor Name: {result.requestor_name}")
    print(f"Requestor Department: {result.requestor_department}")
    print(f"Department (from document): {result.department or 'Not specified'}")
    print(f"Title/Description: {result.title}")
    print(f"Vendor Name: {result.vendor_name}")
    print(f"VAT ID: {result.vat_id}")
    print(f"Commodity Group: {result.commodity_group:03d} - {get_commodity_group_name(result.commodity_group)}")
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

    # Extract procurement data using LLM
    print("Analyzing document with AI...")
    try:
        result = extract_procurement_data(pdf_text, requestor_name, department_name)
    except Exception as e:
        print(f"Error during AI analysis: {e}")
        return

    # Display results
    display_result(result)


if __name__ == "__main__":
    main()
