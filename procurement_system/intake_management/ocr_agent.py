import base64
from io import BytesIO

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage
import pypdfium2 as pdfium
from PIL import Image

from .types import ExtractedProcurementData
from .intake_manager import COMMODITY_GROUPS


class OCRAgent:
    """Extracts procurement data from PDF images using GPT-4 Vision."""

    def __init__(self, model: str = "gpt-4o", temperature: float = 0):
        self.llm = ChatOpenAI(model=model, temperature=temperature)
        self.structured_llm = self.llm.with_structured_output(ExtractedProcurementData)

    def _get_commodity_groups_text(self) -> str:
        """Convert commodity groups to text format for the prompt."""
        lines = ["Available Commodity Groups:"]
        for category in COMMODITY_GROUPS["categories"]:
            lines.append(f"\n{category['name']}:")
            for group in category["commodityGroups"]:
                lines.append(f"  - {group['id']}: {group['name']}")
        return "\n".join(lines)

    def _convert_pdf_to_images(self, pdf_path: str) -> list[bytes]:
        """Convert PDF file to list of PNG image bytes."""
        pdf = pdfium.PdfDocument(pdf_path)
        image_bytes_list = []
        for page in pdf:
            bitmap = page.render(scale=2)  # 2x scale for better quality
            pil_image = bitmap.to_pil()
            buffer = BytesIO()
            pil_image.save(buffer, format="PNG")
            image_bytes_list.append(buffer.getvalue())
        pdf.close()
        return image_bytes_list

    def _convert_pdf_bytes_to_images(self, pdf_bytes: bytes) -> list[bytes]:
        """Convert PDF bytes to list of PNG image bytes."""
        pdf = pdfium.PdfDocument(pdf_bytes)
        image_bytes_list = []
        for page in pdf:
            bitmap = page.render(scale=2)  # 2x scale for better quality
            pil_image = bitmap.to_pil()
            buffer = BytesIO()
            pil_image.save(buffer, format="PNG")
            image_bytes_list.append(buffer.getvalue())
        pdf.close()
        return image_bytes_list

    def _encode_image(self, image_bytes: bytes) -> str:
        """Encode image bytes to base64 string."""
        return base64.b64encode(image_bytes).decode("utf-8")

    def _build_vision_message(self, image_bytes_list: list[bytes]) -> HumanMessage:
        """Build a message with all PDF page images for GPT-4 Vision."""
        system_prompt = f"""You are a document parser specialized in procurement requests.
You are provided with images of PDF pages containing procurement request information.
Your task is to analyze these images and extract structured information.

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

{self._get_commodity_groups_text()}

Please extract the procurement request information from the following PDF page images:"""

        # Build content list with text prompt and all images
        content = [{"type": "text", "text": system_prompt}]

        for i, img_bytes in enumerate(image_bytes_list, 1):
            base64_image = self._encode_image(img_bytes)
            content.append({
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/png;base64,{base64_image}",
                    "detail": "high"
                }
            })

        return HumanMessage(content=content)

    def extract_from_pdf_path(self, pdf_path: str) -> ExtractedProcurementData:
        """Extract structured procurement data from a PDF file path using OCR."""
        image_bytes_list = self._convert_pdf_to_images(pdf_path)
        message = self._build_vision_message(image_bytes_list)
        return self.structured_llm.invoke([message])

    def extract_from_pdf_bytes(self, pdf_bytes: bytes) -> ExtractedProcurementData:
        """Extract structured procurement data from PDF bytes using OCR."""
        image_bytes_list = self._convert_pdf_bytes_to_images(pdf_bytes)
        message = self._build_vision_message(image_bytes_list)
        return self.structured_llm.invoke([message])
