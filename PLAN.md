# 📋 Implementation Plan: Time Series Data Extraction & Report

To implement your requested visualizations and data analysis, we developed the analytical script [generate_report.py](file:///Users/tui/Documents/Projects/time_series_analysis/generate_report.py) which processes the raw alerts dataset and generates comprehensive, modular reports inside the `output/` directory.

---

## 1. Output Directory Structure

The generated results are organized as follows to prevent clutter:

```
output/
├── csv/
│   ├── daily_regional_trends.csv     # Daily union threat hours per region (0.0 to 24.0)
│   └── oblast_duration_analysis.csv  # Combined stats (threat hours, alarm counts, active %)
└── txt/
    ├── daily_trends_sparklines.txt   # ASCII timeline trend indicators for all regions
    ├── historical_monthly.txt        # Month-by-month pivot totals (for queries > 60 days)
    ├── regional_summary.txt          # Macro-level threat comparison table
    ├── seasonality_nationwide.txt    # Nationwide hourly & weekly active heat indicators
    └── seasonality_regional.txt      # Region-specific hourly & weekly threat profiles
```

---

## 2. Implemented Calculations & Resampling Logic

### A. Daily Resampling (Union Uptime)
*   **Methodology:** Alerts are segmented into calendar-day blocks. For each region on each calendar day, overlapping intervals are merged and summed to compute the **Union threat hours** (0.0 to 24.0).
*   *Output:* Saved to `output/csv/daily_regional_trends.csv`.

### B. Monthly Aggregation
*   **Methodology:** Groups the daily union hours by calendar month (e.g., `2026-05`, `2026-06`) for each region.
*   *Output:* Displayed as a pivot table in `output/txt/historical_monthly.txt`.

### C. Diurnal (Hourly) Seasonality Bins
*   **Methodology:** Every alert's active duration is distributed across 24 hourly UTC bins (0 to 23). For example, an alert from 02:30 to 04:15 UTC adds 30 minutes to hour 2, 60 minutes to hour 3, and 15 minutes to hour 4. Normalization calculates the average active percentage for each bin.
*   *Output:* Displayed as ASCII bar heat charts in `output/txt/seasonality_nationwide.txt` and `output/txt/seasonality_regional.txt`.

### D. Weekly (Day of Week) Seasonality
*   **Methodology:** Allocates active duration to the day of the week (Monday-Sunday) and normalizes it based on the number of weekdays present in the query window.
*   *Output:* Formatted as tables with ASCII indicators in the seasonality reports.

### E. Daily Sparklines
*   **Methodology:** Generates an ASCII sparkline representation of daily threat hours (Key: `.` = 0-3h, `_` = 3-6h, `-` = 6-12h, `=` = 12-18h, `#` = 18-24h active threat per day).
*   *Output:* Written to `output/txt/daily_trends_sparklines.txt`.

---

## 3. Status & Execution

*   **Status:** **Completed and Pushed to GitHub**
*   **Script:** [generate_report.py](file:///Users/tui/Documents/Projects/time_series_analysis/generate_report.py)
*   **Execution Command:**
    ```bash
    python3 generate_report.py --days 30
    # or for historical month-by-month aggregation:
    python3 generate_report.py --days 90
    ```
