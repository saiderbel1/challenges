from langchain_openai import ChatOpenAI
from langchain_community.tools import DuckDuckGoSearchRun
from langchain_core.messages import ToolMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.tools import tool
from pydantic import BaseModel, Field

from .types import ExtractedProcurementData, COMMODITY_GROUPS


class ClassificationResult(BaseModel):
    """Output of the classifier: a short title and a commodity group ID."""

    title: str = Field(
        description="Brief name or description of the product/service requested."
    )
    commodity_group: int = Field(
        description="The numeric commodity group ID that best matches the procurement"
    )
    rationale: str = Field(
        description="Brief explanation: which category was chosen, which commodity group "
        "was selected, and why — referencing web search and tool findings"
    )


@tool
def web_search(query: str) -> str:
    """Search the web to learn more about a vendor, product, or service.

    Use this to find out:
    - What a vendor/company sells or specialises in
    - What category a specific product or material belongs to
    - Industry terminology that helps map items to commodity groups

    Pass a concise search query (e.g. "Haberkorn GmbH products" or
    "polyethylene film packaging commodity category").
    """
    search = DuckDuckGoSearchRun()
    return search.invoke(query)


@tool
def get_commodity_groups(category_name: str) -> str:
    """Retrieve the available commodity groups for a given category.

    Call this AFTER you have decided which category best fits the procurement.
    Valid category names:
      General Services, Facility Management, Publishing Production,
      Information Technology, Logistics, Marketing & Advertising, Production

    Args:
        category_name: Exact name of the category (case-sensitive)
    """
    for category in COMMODITY_GROUPS["categories"]:
        if category["name"] == category_name:
            lines = [f"Commodity groups in '{category_name}':"]
            for g in category["commodityGroups"]:
                lines.append(f"  - ID {g['id']}: {g['name']}")
            return "\n".join(lines)

    available = [c["name"] for c in COMMODITY_GROUPS["categories"]]
    return (
        f"Category '{category_name}' not found. "
        f"Available categories: {', '.join(available)}"
    )


CATEGORY_NAMES = [c["name"] for c in COMMODITY_GROUPS["categories"]]

CLASSIFIER_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """You are a procurement classification specialist.
You receive structured data that was extracted from a procurement request document.
Your job is to:
1. determine a brief name or description of the product/service requested.
2. Classify the procurement into a category, then select the specific commodity group.

Step-by-step workflow (follow this order):
1. Use web_search to research the vendor and/or the products/services in the order lines.
1. Determine procurement purpose
2. Determine business owner/function
3. Match category definitions
4. Call get_commodity_groups with your chosen category name to see the specific groups available.
5. Pick the single best commodity group from the returned list, again using the business owner/function and procurement purpose as context clues
   - If none of the groups in that category fit well, you may call get_commodity_groups again
     with a different category.


When selecting the commodity group:
- Consider ALL order line descriptions, not just the first one
- If items span multiple groups, pick the group that covers the majority of the total cost
- Use the vendor name, line descriptions, AND your web search findings as context clues
- Use the business owner/function as context clues
- Use the procurement purpose as context clues
""",
        ),
        (
            "human",
            """Please classify the following procurement request.

Vendor: {vendor_name}
VAT ID: {vat_id}

Order Lines:
{order_lines_text}

Additional Costs: {additional_costs:.2f}
Total Cost: {total_cost:.2f}
""",
        ),
    ]
)


class ClassifierAgent:
    """Infers title and commodity group from extracted procurement data."""

    def __init__(self, model: str = "gpt-4o", temperature: float = 0):
        self.llm = ChatOpenAI(model=model, temperature=temperature)
        self.tools = [web_search, get_commodity_groups]
        self.tool_map = {t.name: t for t in self.tools}
        self.llm_with_tools = self.llm.bind_tools(self.tools)

    def _format_order_lines(self, data: ExtractedProcurementData) -> str:
        if not data.order_lines:
            return "  (no order lines)"
        lines = []
        for i, line in enumerate(data.order_lines, 1):
            lines.append(f"  {i}. {line.position_description}")
            lines.append(f"     Unit: {line.unit}")
            lines.append(f"     Unit Price: {line.unit_price:.2f}")
            lines.append(f"     Amount: {line.amount:.2f}")
            lines.append(f"     Total Price: {line.total_price:.2f}")
        return "\n".join(lines)

    def classify(self, data: ExtractedProcurementData) -> ExtractedProcurementData:
        """Predict title and commodity_group, returning an updated copy of the data."""
        messages = CLASSIFIER_PROMPT.format_messages(
            categories=", ".join(CATEGORY_NAMES),
            vendor_name=data.vendor_name,
            vat_id=data.vat_id,
            order_lines_text=self._format_order_lines(data),
            additional_costs=data.additional_costs,
            total_cost=data.total_cost,
        )

        response = self.llm_with_tools.invoke(messages)
        messages.append(response)

        while response.tool_calls:
            for tc in response.tool_calls:
                tool_fn = self.tool_map.get(tc["name"])
                if tool_fn:
                    result = tool_fn.invoke(tc["args"])
                    print(f"\n[{tc['name']}] args={tc['args']}")
                    snippet = result[:300] if len(result) > 300 else result
                    print(f"[{tc['name']}] result: {snippet}")
                    messages.append(ToolMessage(content=result, tool_call_id=tc["id"]))

            response = self.llm_with_tools.invoke(messages)
            messages.append(response)

        messages.append((
            "human",
            "Now produce your final classification. "
            "State which category you chose, which commodity group you selected, "
            "and reference your web search and tool findings in the rationale."
        ))

        structured_llm = self.llm.with_structured_output(ClassificationResult)
        result: ClassificationResult = structured_llm.invoke(messages)

        print("\n[ClassifierAgent Result]")
        print(f"Title: {result.title}")
        print(f"Commodity Group: {result.commodity_group:03d}")
        print(f"Rationale: {result.rationale}")

        return data.model_copy(update={
            "title": result.title,
            "commodity_group": result.commodity_group,
        })
