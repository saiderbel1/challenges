from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.tools import tool
from pydantic import BaseModel, Field

from .types import OrderLine


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
    """Internal extraction model — focuses on vendor, line items, and costs.
    Title and commodity group are inferred later by the ClassifierAgent."""

    vendor_name: str = Field(description="Name of the vendor")
    vat_id: str = Field(description="Umsatzsteuer-Identifikationsnummer (VAT ID)")
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
    return total


EXTRACTION_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """You are a document parser specialized in procurement requests.
You are provided with extracted text data from a PDF of procurement requests.
Your task is to parse this text and extract structured information.

You do NOT need to determine a title/description or commodity group — those are handled by a separate step.

Rules:
- NEVER translate any data — extract everything in the original language of the document
- Extract information exactly as it appears in the document
- If a field is not found in the document, use an empty string for text fields or 0 for numeric fields
- Calculate total_price for each order line as unit_price * amount
- VAT ID (Umsatzsteuer-Identifikationsnummer) format is typically: DE followed by 9 digits
- If an Order Line mentions being an alternative, you should add the additional cost to the total_cost

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

        messages = EXTRACTION_PROMPT.format_messages(pdf_text=pdf_text)

        total_additional_costs = 0.0

        response = self.llm_with_tools.invoke(messages)
        messages.append(response)

        while response.tool_calls:
            tool_results, additional_costs = self._execute_tool_calls(response.tool_calls)
            total_additional_costs += additional_costs

            for tool_result in tool_results:
                messages.append(ToolMessage(
                    content=str(tool_result["result"]),
                    tool_call_id=tool_result["tool_call_id"],
                ))

            response = self.llm_with_tools.invoke(messages)
            messages.append(response)

        structured_llm = self.llm.with_structured_output(InternalExtractedData)
        result = structured_llm.invoke(messages)

        if total_additional_costs > 0 and result.additional_costs == 0:
            result = result.model_copy(update={"additional_costs": total_additional_costs})

        return result
