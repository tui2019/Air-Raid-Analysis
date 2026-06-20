# 🚨 Air Raid Analysis: Ukraine Air Alert Durations

This repository contains a Python utility to analyze the durations of official air raid alerts in Ukraine. It pulls the latest official records in real-time from the community-maintained [Vadimkin/ukrainian-air-raid-sirens-dataset](https://github.com/Vadimkin/ukrainian-air-raid-sirens-dataset) repository.

---

## ⚡ Features
*   **Live Data Fetching:** Downloads and processes the latest official alerts directly from the raw GitHub dataset source.
*   **Interval Merging (Union Duration):** Warnings can be sounded at the local `raion` (district) or `hromada` level rather than oblast-wide, so alerts frequently overlap. The script merges overlapping warning periods to calculate the true duration under threat (active warning uptime) for each of the 26 Ukrainian regions.
*   **Permanent Alerts Injection:** Programmatically accounts for Luhanska oblast and the Autonomous Republic of Crimea, which have been under permanent alert since early 2022.
*   **Highly Optimized:** Parses timezone-aware UTC timestamps and processes over 270,000 alert rows in under 2 seconds.

---

## 🛠️ Setup & Installation

1.  **Clone this repository:**
    ```bash
    git clone https://github.com/tui2019/Air-Raid-Analysis.git
    cd Air-Raid-Analysis
    ```

2.  **Create and activate a virtual environment:**
    ```bash
    python3 -m venv venv
    source venv/bin/activate
    ```

3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

---

## 🚀 Usage

Run the analysis script using:
```bash
python3 generate_report.py --days 30
# Or analyze a wider window (e.g., 90 days) to see historical monthly pivots
python3 generate_report.py --days 90
```

### Options:
*   `-d`, `--days`: The number of days of history to analyze (default: `30` days).

---

## 📊 Outputs
The script generates a single-page interactive dashboard and structured text/markdown reports under the `output/` directory:

```
output/
├── dashboard.html                  # Single-page interactive HTML dashboard
├── txt/
│   ├── ai_overview.txt             # AI overview general and region-specific summaries (if API key provided)
│   ├── daily_trends_sparklines.txt # ASCII timeline trend indicators for all regions
│   ├── historical_monthly.txt      # Month-by-month pivot totals (for queries > 60 days)
│   ├── regional_summary.txt        # Macro-level threat comparison table
│   ├── seasonality_nationwide.txt  # Nationwide hourly & weekly active heat indicators
│   └── seasonality_regional.txt    # Region-specific hourly & weekly threat profiles
└── md/
    ├── ai_overview.md              # Markdown version of AI overview summaries (if API key provided)
    ├── daily_trends_sparklines.md  # Markdown version of daily sparkline timelines
    ├── historical_monthly.md       # Markdown version of historical monthly pivots
    ├── regional_summary.md         # Markdown version of regional summary table
    ├── seasonality_nationwide.md   # Markdown version of nationwide seasonality
    └── seasonality_regional.md     # Markdown version of regional seasonality profiles
```
