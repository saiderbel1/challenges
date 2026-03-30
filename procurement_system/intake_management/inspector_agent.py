from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field

from .types import ExtractedProcurementData, OrderLine


class InspectionResult(BaseModel):
    """Result of the inspector agent's analysis."""

    corrected_data: ExtractedProcurementData = Field(
        description="The corrected procurement data. If no correction was made, return the original data unchanged."
    )
    was_corrected: bool = Field(
        description="True if any corrections were made, False if returned as-is"
    )
    rationale: str = Field(
        description="Explanation of what was found and why corrections were or were not made"
    )
    confidence: float = Field(
        description="Confidence level in the correction (0.0 to 1.0). Below 0.7 means not confident enough to correct."
    )


INSPECTION_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """You are a data validation inspector specialized in procurement requests.
You have been given extracted procurement data that failed validation due to sum/calculation errors.

Your task is to:
1. Analyze the original PDF text and the extracted data
2. Identify the cause of the calculation errors
3. If you can confidently fix the errors, provide corrected data
4. If you are NOT confident about the fix (confidence < 0.7), return the data unchanged

IMPORTANT: NEVER translate any data — all values must remain in the original language of the document.

Common error causes:
- Incorrect unit_price or amount values
- Missing or incorrectly calculated order line totals
- Additional costs not properly accounted for
- Reductions/discounts not properly applied
- Alternative items incorrectly included in totals
- Rounding errors or typos in extracted numbers

Rules:
- Only make corrections if you are confident (confidence >= 0.7)
- If not confident, set was_corrected to false and return original data
- Always provide a clear rationale explaining your analysis
- Compare extracted values against the original PDF text
- The total_cost should equal: sum of order line total_prices + additional_costs

Validation errors found:
{errors}
""",
        ),
        (
            "human",
            """Please inspect and potentially correct this extraction.

ORIGINAL PDF TEXT:
{pdf_text}

EXTRACTED DATA (after filtering alternatives):
Title: {title}
Vendor: {vendor_name}
VAT ID: {vat_id}
Commodity Group: {commodity_group}

Order Lines:
{order_lines_text}

Additional Costs: {additional_costs}
Total Cost: {total_cost}

Please analyze and provide corrected data if confident, or return as-is with explanation.""",
        ),
    ]
)


class InspectorAgent:
    """Inspects and corrects extraction errors when sum validation fails."""

    def __init__(self, model: str = "gpt-4o", temperature: float = 0):
        self.llm = ChatOpenAI(model=model, temperature=temperature)
        self.structured_llm = self.llm.with_structured_output(InspectionResult)

    def _format_order_lines(self, order_lines: list[OrderLine]) -> str:
        """Format order lines for display in prompt."""
        lines = []
        for i, line in enumerate(order_lines, 1):
            lines.append(f"  {i}. {line.position_description}")
            lines.append(f"     Unit: {line.unit}")
            lines.append(f"     Unit Price: {line.unit_price:.2f}")
            lines.append(f"     Amount: {line.amount:.2f}")
            lines.append(f"     Total Price: {line.total_price:.2f}")
        return "\n".join(lines)

    def inspect(
        self,
        pdf_text: str,
        errors: list[str],
        extracted_data: ExtractedProcurementData,
    ) -> InspectionResult:
        """Inspect extracted data and attempt to correct sum errors."""
        # Format the prompt
        messages = INSPECTION_PROMPT.format_messages(
            pdf_text=pdf_text,
            errors="\n".join(f"- {e}" for e in errors),
            title=extracted_data.title,
            vendor_name=extracted_data.vendor_name,
            vat_id=extracted_data.vat_id,
            commodity_group=extracted_data.commodity_group,
            order_lines_text=self._format_order_lines(extracted_data.order_lines),
            additional_costs=extracted_data.additional_costs,
            total_cost=extracted_data.total_cost,
        )

        # Get inspection result
        result = self.structured_llm.invoke(messages)

        # If confidence is below threshold, ensure we return original data
        if result.confidence < 0.7:
            result = InspectionResult(
                corrected_data=extracted_data,
                was_corrected=False,
                rationale=f"Confidence too low ({result.confidence:.2f}). {result.rationale}",
                confidence=result.confidence,
            )

        return result
