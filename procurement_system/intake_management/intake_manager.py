from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate

from .types import ExtractedProcurementData


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
""",
        ),
        ("human", "Please extract the procurement request information from the following PDF text:\n\n{pdf_text}"),
    ]
)


class IntakeManager:
    """Manages the intake and processing of procurement requests using LLM."""

    def __init__(self, model: str = "gpt-4o", temperature: float = 0):
        self.llm = ChatOpenAI(model=model, temperature=temperature)
        self.structured_llm = self.llm.with_structured_output(ExtractedProcurementData)
        self.chain = EXTRACTION_PROMPT | self.structured_llm

    def _get_commodity_groups_text(self) -> str:
        """Convert commodity groups to text format for the prompt."""
        lines = ["Available Commodity Groups:"]
        for category in COMMODITY_GROUPS["categories"]:
            lines.append(f"\n{category['name']}:")
            for group in category["commodityGroups"]:
                lines.append(f"  - {group['id']}: {group['name']}")
        return "\n".join(lines)

    def get_commodity_group_name(self, group_id: int) -> str:
        """Get the commodity group name by ID."""
        id_str = f"{group_id:03d}"
        for category in COMMODITY_GROUPS["categories"]:
            for group in category["commodityGroups"]:
                if group["id"] == id_str:
                    return f"{group['name']} ({category['name']})"
        return "Unknown"

    def extract_procurement_data(self, pdf_text: str) -> ExtractedProcurementData:
        """Extract structured procurement data from PDF text using LLM."""
        result = self.chain.invoke(
            {
                "pdf_text": pdf_text,
                "commodity_groups": self._get_commodity_groups_text(),
            }
        )
        return result
