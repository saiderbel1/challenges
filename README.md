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

---

## Header–Lines Matching

A solver that matches order headers to order lines. Each header specifies a `total_price` and a `total_lines` count; the solver finds a subset of exactly `total_lines` order lines whose prices sum to `total_price` using memoized DFS with pruning.

### Usage

The script requires `--mode` (`read` or `generate`).

**Read existing CSVs and solve:**

```bash
python header_lines_matching/run.py --mode read
```

**Generate stress-test data and solve:**

```bash
python header_lines_matching/run.py --mode generate
```

**Generation parameters (all optional, shown with defaults):**

```bash
python header_lines_matching/run.py --mode generate \
  --num-lines 250 \
  --num-headers 30 \
  --min-price 5 \
  --max-price 20 \
  --min-k 6 \
  --max-k 10 \
  --seed 42
```

| Flag | Default | Description |
|------|---------|-------------|
| `--mode` | *(required)* | `read` to load CSVs, `generate` to create random data |
| `--headers-path` | `header_lines_matching/order_headers.csv` | Path to headers CSV |
| `--lines-path` | `header_lines_matching/order_lines.csv` | Path to lines CSV |
| `--print-head` | `5` | Number of preview rows to print |
| `--num-lines` | `250` | Number of order lines to generate |
| `--num-headers` | `30` | Number of order headers to generate |
| `--min-price` | `5` | Minimum line price (cents) |
| `--max-price` | `20` | Maximum line price (cents) |
| `--min-k` | `6` | Minimum lines per header |
| `--max-k` | `10` | Maximum lines per header |
| `--seed` | `42` | Random seed for reproducibility |

---

### Project Structure

```
challenges/
├── .gitignore
├── README.md
├── requirements.txt
├── procurement_system/
│   └── main.py
└── header_lines_matching/
    ├── run.py
    ├── order_headers.csv
    └── order_lines.csv
```
