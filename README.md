# 🚨 Air Raid Analysis: Ukraine Air Alert Durations

This repository contains a Python utility to analyze the durations of official air raid alerts in Ukraine. It pulls the latest official records in real-time from the community-maintained [Vadimkin/ukrainian-air-raid-sirens-dataset](https://github.com/Vadimkin/ukrainian-air-raid-sirens-dataset) repository.

---

## ⚡ Features
*   **Live Data Fetching:** Downloads and processes the latest official alerts directly from the raw GitHub dataset source.
*   **Interval Merging (Union Duration):** Since warnings are now sounded at the local `raion` (district) or `hromada` level rather than oblast-wide, alerts frequently overlap. The script merges overlapping warning periods to calculate the true duration under threat (active warning uptime) for each of the 26 Ukrainian regions.
*   **Permanent Alerts Injection:** Programmatically accounts for Luhanska oblast and the Autonomous Republic of Crimea, which have been under permanent alert since early 2022.
*   **Highly Optimized:** Parses timezone-aware UTC timestamps and processes over 270,000 alert rows in under 1 second locally.

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
python3 analyze_alerts.py --days 30
```

### Options:
*   `-d`, `--days`: The number of days of history to analyze (default: `30` days).

---

## 📊 Outputs
The script generates two files in the repository root:
1.  **`oblast_duration_analysis.csv`**: Contains the regional stats (siren count, union threat hours, cumulative warning hours).
2.  **`analysis_summary.txt`**: A clean, human-readable table summarizing the active threat hours for all 26 Ukrainian regions.
