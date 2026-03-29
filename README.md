# Challenges

## Procurement System

A Python application for parsing procurement request PDFs using PyMuPDF and LangChain with OpenAI.

### Features

- Extract text from PDF files containing procurement requests
- Use AI to parse tabular data and extract structured information
- Auto-classify items into commodity groups (50 categories)
- Output includes: requestor details, vendor info, VAT ID, order lines, and total cost

### Requirements

- Python 3.10+
- OpenAI API key

### Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd challenges
```

2. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set your OpenAI API key:
```bash
export OPENAI_API_KEY='your-api-key'
```

### Running

```bash
python procurement_system/main.py
```

The program will prompt you for:
- Your name
- Your department name
- Path to a PDF file containing a procurement request

### Output Structure

The extracted data includes:
- **Requestor Name**: Full name of the person submitting the request
- **Title/Description**: Brief name or description of the product/service
- **Vendor Name**: Name of the vendor
- **VAT ID**: Umsatzsteuer-Identifikationsnummer
- **Requestor Department**: Department provided by user
- **Commodity Group**: Auto-classified category (1-50) based on item type
- **Order Lines**: List of items with:
  - Position Description (full description)
  - Unit (unit of measure, e.g., licenses, pieces, hours)
  - Unit Price
  - Amount (can be decimal)
  - Total Price
- **Total Cost**: Estimated total cost of the request
- **Department**: Department mentioned in the document (if any)

### Project Structure

```
challenges/
├── .gitignore
├── README.md
├── requirements.txt
└── procurement_system/
    └── main.py
```
