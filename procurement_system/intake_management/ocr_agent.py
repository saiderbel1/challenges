import base64
from io import BytesIO

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage
import pypdfium2 as pdfium


OCR_PROMPT = """You are an OCR specialist. You are given images of PDF pages.
Your task is to produce a faithful plain-text transcription of every page,
preserving the original layout as closely as possible (columns, indentation,
spacing, line breaks).

Rules:
- NEVER translate any text — reproduce everything in the original language of the document
- Reproduce ALL visible text exactly as printed — do not summarise, reorder, or omit anything
- Maintain the spatial relationship between columns (use spaces to align them)
- Keep headers, footers, and page numbers
- Separate pages with a "--- Page N ---" header

Return ONLY the transcribed text, nothing else."""


class OCRAgent:
    """Extracts a layout-preserving text representation from PDF images using GPT-4 Vision."""

    def __init__(self, model: str = "gpt-4o", temperature: float = 0):
        self.llm = ChatOpenAI(model=model, temperature=temperature)

    def _convert_pdf_to_images(self, pdf_path: str) -> list[bytes]:
        """Convert PDF file to list of PNG image bytes."""
        pdf = pdfium.PdfDocument(pdf_path)
        image_bytes_list = []
        for page in pdf:
            bitmap = page.render(scale=2)
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
            bitmap = page.render(scale=2)
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
        """Build a vision message requesting layout-preserving text transcription."""
        content: list[dict] = [{"type": "text", "text": OCR_PROMPT}]

        for img_bytes in image_bytes_list:
            base64_image = self._encode_image(img_bytes)
            content.append({
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/png;base64,{base64_image}",
                    "detail": "high",
                },
            })

        return HumanMessage(content=content)

    def extract_text_from_pdf_path(self, pdf_path: str) -> str:
        """Return a layout-preserving text transcription of a PDF file."""
        image_bytes_list = self._convert_pdf_to_images(pdf_path)
        message = self._build_vision_message(image_bytes_list)
        response = self.llm.invoke([message])
        return response.content

    def extract_text_from_pdf_bytes(self, pdf_bytes: bytes) -> str:
        """Return a layout-preserving text transcription of PDF bytes."""
        image_bytes_list = self._convert_pdf_bytes_to_images(pdf_bytes)
        message = self._build_vision_message(image_bytes_list)
        response = self.llm.invoke([message])
        return response.content
