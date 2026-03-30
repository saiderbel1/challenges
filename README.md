# Challenges

## Procurement System

A Python application for fast procurement request submission.

### Requirements

- Python 3.10+
- OpenAI API key

### OS Dependencies

These instructions assume you're on a recent OS. Package names may differ for older versions.

#### Debian, Ubuntu, and friends

```bash
sudo apt install build-essential libpoppler-cpp-dev pkg-config python3-dev
```

#### Fedora, Red Hat, and friends

```bash
sudo yum install gcc-c++ pkgconfig poppler-cpp-devel python3-devel
```

#### macOS

```bash
brew install pkg-config poppler python
```

### Installation

1. Clone the repository:

```bash
git clone https://github.com/saiderbel1/challenges
cd challenges
```

2. Create a virtual environment:

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install Python dependencies:

```bash
pip install -r requirements.txt
```

4. Set your OpenAI API key:

```bash
export OPENAI_API_KEY='your-api-key'
```

### Running

```bash
streamlit run procurement_system/streamlit_app.py 
```

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

| Flag             | Default                                   | Description                                           |
| ---------------- | ----------------------------------------- | ----------------------------------------------------- |
| `--mode`         | *(required)*                              | `read` to load CSVs, `generate` to create random data |
| `--headers-path` | `header_lines_matching/order_headers.csv` | Path to headers CSV                                   |
| `--lines-path`   | `header_lines_matching/order_lines.csv`   | Path to lines CSV                                     |
| `--print-head`   | `5`                                       | Number of preview rows to print                       |
| `--num-lines`    | `250`                                     | Number of order lines to generate                     |
| `--num-headers`  | `30`                                      | Number of order headers to generate                   |
| `--min-price`    | `5`                                       | Minimum line price (cents)                            |
| `--max-price`    | `20`                                      | Maximum line price (cents)                            |
| `--min-k`        | `6`                                       | Minimum lines per header                              |
| `--max-k`        | `10`                                      | Maximum lines per header                              |
| `--seed`         | `42`                                      | Random seed for reproducibility                       |

---


