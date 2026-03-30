from difflib import SequenceMatcher

from langchain_openai import ChatOpenAI
from langchain_core.messages import ToolMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.tools import tool
from pydantic import BaseModel, Field

from .classifier_agent import web_search
from .types import ExtractedProcurementData, OrderLine, ValidationIssue, OCR_RECOVERABLE_ISSUES


class FieldComparison(BaseModel):
    field: str = Field(description="Field name (vendor_name or vat_id)")
    parsed_value: str = Field(description="Value from the parsed extraction")
    ocr_value: str = Field(description="Value from the OCR extraction")
    similarity: float = Field(description="Similarity ratio between 0.0 and 1.0")
    parsed_empty: bool = Field(description="Whether the parsed value is empty")
    ocr_empty: bool = Field(description="Whether the OCR value is empty")


class ComparisonResult(BaseModel):
    comparisons: list[FieldComparison]


@tool
def compare_text_fields(
    parsed_vendor_name: str,
    ocr_vendor_name: str,
    parsed_vat_id: str,
    ocr_vat_id: str,
) -> str:
    """Compare how much the Vendor Name and VAT ID differ between
    parsed and OCR extractions. Returns similarity scores (0.0 = completely
    different, 1.0 = identical) and flags empty values.

    Use this tool BEFORE deciding which source to pick for each field.

    Args:
        parsed_vendor_name: Vendor name from the parsed extraction
        ocr_vendor_name: Vendor name from the OCR extraction
        parsed_vat_id: VAT ID from the parsed extraction
        ocr_vat_id: VAT ID from the OCR extraction
    """
    pairs = [
        ("vendor_name", parsed_vendor_name, ocr_vendor_name),
        ("vat_id", parsed_vat_id, ocr_vat_id),
    ]

    lines = []
    for name, parsed, ocr in pairs:
        p_empty = not parsed or not parsed.strip()
        o_empty = not ocr or not ocr.strip()
        ratio = SequenceMatcher(None, parsed.strip(), ocr.strip()).ratio() if not (p_empty and o_empty) else 0.0
        lines.append(
            f"  {name}:\n"
            f"    parsed : {parsed!r} {'(EMPTY)' if p_empty else ''}\n"
            f"    ocr    : {ocr!r} {'(EMPTY)' if o_empty else ''}\n"
            f"    similarity: {ratio:.2%}"
        )

    return "Field comparison results:\n" + "\n".join(lines)


class FieldDecision(BaseModel):
    """Reasoning trace for a single field merge decision."""

    field: str = Field(description="Field name (e.g. vendor_name, vat_id)")
    chosen_source: str = Field(description="'parsed' or 'ocr'")
    parsed_value: str = Field(description="The value from parsed data")
    ocr_value: str = Field(description="The value from OCR data")
    similarity_pct: float = Field(description="Similarity percentage from the comparison tool (0-100)")
    reasoning: str = Field(
        description=(
            "Step-by-step reasoning: (1) Is the parsed value empty or flagged? "
            "(2) How similar are the two values? "
            "(3) Which value looks more plausible given the document context? "
            "(4) Final decision and why."
        )
    )


class MergeResult(BaseModel):
    """Result of the merger agent's fusion of parsed and OCR data."""

    field_decisions: list[FieldDecision] = Field(
        description="Per-field reasoning trace for vendor_name and vat_id"
    )
    merged_data: ExtractedProcurementData = Field(
        description="The merged procurement data combining parsed and OCR outputs"
    )
    fields_from_ocr: list[str] = Field(
        description="List of field names that were taken from OCR output instead of parsed output"
    )
    rationale: str = Field(
        description="High-level summary of the merge decisions, referencing the per-field reasoning"
    )


MERGER_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """You are a data fusion specialist for procurement requests.
You have been given two extractions of the same document:
1. PARSED DATA: Extracted using text parsing (generally more reliable for structured text)
2. OCR DATA: Extracted using visual OCR (better for layout-dependent or poorly formatted documents)

The parsed data failed validation because certain fields are missing or malformed.
Your task is to fill in those fields using the OCR data.

Issues to resolve:
{errors}

Workflow:
1. FIRST call the compare_text_fields tool to measure how much the Vendor Name and VAT ID differ between parsed and OCR data
2. If a vendor name or VAT ID is ambiguous, or the two sources disagree significantly (< 80% similarity), use the web_search tool to verify — e.g. search for the vendor name to confirm their real VAT ID or official company name
3. For EACH of the two text fields (vendor_name, vat_id), reason step-by-step:
   a. Is the parsed value empty or flagged in the issues?
   b. What is the similarity score between parsed and OCR?
   c. If both are non-empty, which looks more plausible given the rest of the document?
      - Does one contain obvious OCR artefacts (misread characters, broken words)?
      - Does the VAT ID match the expected DE+9-digit format in one source but not the other?
      - Does the vendor name appear elsewhere in the data (e.g. in order line descriptions) that can confirm one version?
   d. State your final choice and why
4. Produce the merged output with a field_decisions entry for each field

Decision guidelines:
- If the parsed value is empty / missing → take the OCR value
- If both values are non-empty and highly similar (>= 80%) → prefer the parsed value unless it is flagged in the issues
- If both values are non-empty and significantly different (< 80%) → carefully reason which is more accurate using the context clues above
- For numeric values (prices, amounts, totals, additional costs): keep the parsed data values as-is. Only use OCR values if the parsed value is missing
- Do NOT recalculate or adjust any sums — that is handled separately
""",
        ),
        (
            "human",
            """Please merge these two extractions, resolving only the issues listed above.

PARSED DATA:
Vendor: {parsed_vendor_name}
VAT ID: {parsed_vat_id}

Order Lines:
{parsed_order_lines_text}

Additional Costs: {parsed_additional_costs}
Total Cost: {parsed_total_cost}

---

OCR DATA:
Vendor: {ocr_vendor_name}
VAT ID: {ocr_vat_id}

Order Lines:
{ocr_order_lines_text}

Additional Costs: {ocr_additional_costs}
Total Cost: {ocr_total_cost}

---

Start by calling compare_text_fields.
After reviewing the results, reason through vendor_name and vat_id step-by-step before producing the final merge.
Keep all numeric fields and order lines from the parsed data unchanged unless their value is missing.""",
        ),
    ]
)


class MergerAgent:
    """Merges parsed and OCR extraction outputs to resolve validation errors."""

    def __init__(self, model: str = "gpt-4o", temperature: float = 0):
        self.llm = ChatOpenAI(model=model, temperature=temperature)
        self.tools = [compare_text_fields, web_search]
        self.tool_map = {t.name: t for t in self.tools}
        self.llm_with_tools = self.llm.bind_tools(self.tools)

    def _format_order_lines(self, order_lines: list[OrderLine]) -> str:
        """Format order lines for display in prompt."""
        if not order_lines:
            return "  (no order lines)"
        lines = []
        for i, line in enumerate(order_lines, 1):
            lines.append(f"  {i}. {line.position_description}")
            lines.append(f"     Unit: {line.unit}")
            lines.append(f"     Unit Price: {line.unit_price:.2f}")
            lines.append(f"     Amount: {line.amount:.2f}")
            lines.append(f"     Total Price: {line.total_price:.2f}")
        return "\n".join(lines)

    def merge(
        self,
        issues: list[ValidationIssue],
        parsed_data: ExtractedProcurementData,
        ocr_data: ExtractedProcurementData,
    ) -> MergeResult:
        """Merge parsed and OCR data to resolve missing-data and VAT validation issues."""
        relevant_issues = [i for i in issues if i.issue_type in OCR_RECOVERABLE_ISSUES]
        messages = MERGER_PROMPT.format_messages(
            errors="\n".join(f"- [{i.issue_type.value}] {i.message}" for i in relevant_issues),
            parsed_vendor_name=parsed_data.vendor_name,
            parsed_vat_id=parsed_data.vat_id,
            parsed_order_lines_text=self._format_order_lines(parsed_data.order_lines),
            parsed_additional_costs=parsed_data.additional_costs,
            parsed_total_cost=parsed_data.total_cost,
            ocr_vendor_name=ocr_data.vendor_name,
            ocr_vat_id=ocr_data.vat_id,
            ocr_order_lines_text=self._format_order_lines(ocr_data.order_lines),
            ocr_additional_costs=ocr_data.additional_costs,
            ocr_total_cost=ocr_data.total_cost,
        )

        response = self.llm_with_tools.invoke(messages)
        messages.append(response)

        while response.tool_calls:
            for tc in response.tool_calls:
                tool_fn = self.tool_map.get(tc["name"])
                if tool_fn:
                    result = tool_fn.invoke(tc["args"])
                    print(f"\n[{tc['name']}]\n{result}")
                    messages.append(ToolMessage(content=result, tool_call_id=tc["id"]))

            response = self.llm_with_tools.invoke(messages)
            messages.append(response)

        messages.append(("human",
            "Now, for each of vendor_name and vat_id: "
            "state the similarity score, whether the parsed value is flagged, "
            "which source you choose, and why. "
            "Then produce the final merged output with your field_decisions."
        ))

        structured_llm = self.llm.with_structured_output(MergeResult)
        return structured_llm.invoke(messages)
