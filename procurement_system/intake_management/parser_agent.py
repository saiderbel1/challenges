from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.tools import tool
from pydantic import BaseModel, Field

from .types import ExtractedProcurementData, OrderLine


class InternalOrderLine(BaseModel):
    """Internal order line with additional fields for processing."""

    position_description: str = Field(
        description="Full description of the item/service as provided in the document"
    )
    unit: str = Field(
        description="The unit of measure or quantity (e.g., licenses, pieces, hours, kg)"
    )
    unit_price: float = Field(description="Price per unit/item/service")
    amount: float = Field(description="Amount of items/services ordered")
    total_price: float = Field(description="Total price for this line (Unit Price x Amount)")
    is_alternative: bool = Field(
        default=False,
        description="True if this line item is marked as an alternative option, False otherwise"
    )
    reduction: float = Field(
        default=0.0,
        description="Reduction/discount amount applied to this line item (positive value)"
    )


class InternalExtractedData(BaseModel):
    """Internal extraction model with additional fields for processing."""

    title: str = Field(
        description="Brief name or description of the product/service requested (can be inferred)"
    )
    vendor_name: str = Field(description="Name of the vendor")
    vat_id: str = Field(description="Umsatzsteuer-Identifikationsnummer (VAT ID)")
    commodity_group: int = Field(
        description="The commodity group ID (1-50) that best matches the requested items/services"
    )
    order_lines: list[InternalOrderLine] = Field(description="List of order line items")
    additional_costs: float = Field(
        default=0.0,
        description="Sum of additional costs beyond order line totals, that are listed after the order lines"
    )
    total_cost: float = Field(description="Estimated total cost of the request")


@tool
def sum_additional_costs(costs: list[float]) -> float:
    """Sum a list of additional costs that are included in the total cost.

    Use this tool when the document contains additional costs beyond the order line totals.

    Args:
        costs: A list of additional cost values to sum

    Returns:
        The sum of all additional costs
    """
    total = sum(costs)
    print(f"additional costs: {total}")
    return total


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
- In an Oder Line mentions being an alternative, you should add the additional cost to the total_cost

Order Line extraction rules:
- position_description: Include the FULL description of each line item as provided in the document
- unit: Extract the unit of measure (e.g., licenses, pieces, hours, kg, units, etc.)
- amount: Can be a decimal number (float), not just integers
- is_alternative: Set to true if the line item is explicitly marked as an "Alternative" or "Option", otherwise false
- reduction: If a discount or reduction is applied to this line item, extract the reduction amount as a positive value (e.g., if "-50.00" discount, set reduction to 50.0). Set to 0.0 if no reduction

Additional Costs:
- If the document contains additional costs beyond the order line totals, you MUST use the sum_additional_costs tool to calculate their sum
- Pass all additional cost values as a list to the tool
- These additional costs are typically included in the total_cost but are separate from the order line totals
- These additional costs are listed after the order lines, and are NOT part of the order line totals

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


class ParserAgent:
    """Extracts procurement data from PDF text using LLM."""

    def __init__(self, model: str = "gpt-4o", temperature: float = 0):
        self.llm = ChatOpenAI(model=model, temperature=temperature)
        self.tools = [sum_additional_costs]
        self.llm_with_tools = self.llm.bind_tools(self.tools)

    def _get_commodity_groups_text(self) -> str:
        """Convert commodity groups to text format for the prompt."""
        lines = ["Available Commodity Groups:"]
        for category in COMMODITY_GROUPS["categories"]:
            lines.append(f"\n{category['name']}:")
            for group in category["commodityGroups"]:
                lines.append(f"  - {group['id']}: {group['name']}")
        return "\n".join(lines)

    def _execute_tool_calls(self, tool_calls: list) -> tuple[list, float]:
        """Execute tool calls and return results along with additional costs."""
        results = []
        additional_costs = 0.0

        for tool_call in tool_calls:
            tool_name = tool_call["name"]
            tool_args = tool_call["args"]

            if tool_name == "sum_additional_costs":
                result = sum_additional_costs.invoke(tool_args)
                additional_costs += result
                results.append({
                    "tool_call_id": tool_call["id"],
                    "result": result,
                })

        return results, additional_costs

    def extract_procurement_data(self, pdf_text: str) -> InternalExtractedData:
        """Extract structured procurement data from PDF text using LLM."""
        from langchain_core.messages import ToolMessage

        # Format the prompt
        messages = EXTRACTION_PROMPT.format_messages(
            pdf_text=pdf_text,
            commodity_groups=self._get_commodity_groups_text(),
        )

        # Track additional costs from tool calls
        total_additional_costs = 0.0

        # First call - may include tool calls
        response = self.llm_with_tools.invoke(messages)
        messages.append(response)

        # Handle tool calls if any
        while response.tool_calls:
            tool_results, additional_costs = self._execute_tool_calls(response.tool_calls)
            total_additional_costs += additional_costs

            # Add tool results to messages
            for tool_result in tool_results:
                messages.append(ToolMessage(
                    content=str(tool_result["result"]),
                    tool_call_id=tool_result["tool_call_id"],
                ))

            # Continue the conversation
            response = self.llm_with_tools.invoke(messages)
            messages.append(response)

        # Final call with structured output, including the full conversation
        structured_llm = self.llm.with_structured_output(InternalExtractedData)
        result = structured_llm.invoke(messages)

        # Ensure additional_costs from tool is set on the result
        if total_additional_costs > 0 and result.additional_costs == 0:
            result = result.model_copy(update={"additional_costs": total_additional_costs})

        return result


def get_commodity_group_name(group_id: int) -> str:
    """Get the commodity group name by ID."""
    id_str = f"{group_id:03d}"
    for category in COMMODITY_GROUPS["categories"]:
        for group in category["commodityGroups"]:
            if group["id"] == id_str:
                return f"{group['name']} ({category['name']})"
    return "Unknown"
