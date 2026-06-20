# Air Raid Analysis: Ukraine Air Alert Durations

This repository contains a Python utility to analyze the durations of official air raid alerts in Ukraine. It retrieves and parses raw dataset records from the community-maintained Vadimkin dataset repository.

## How the Project Works

The analysis pipeline processes the data in several steps:
1. Fetching: Downloads raw air raid alert records from the Vadimkin dataset repository on GitHub.
2. Cleaning: Filters out permanent alerts, processes timezone-aware UTC timestamps, and shifts the analysis window to exclude the current incomplete day to ensure data integrity.
3. Resampling and Merging: Resolves overlapping alert periods at the regional level (using union intervals) to compute the exact cumulative hours under active air threat for each region. Luhanska oblast and the Autonomous Republic of Crimea are handled programmatically as they have been under permanent alerts since early 2022.
4. Calculations: Computes regional summary statistics, seasonality profiles (hourly and weekly active indicators), monthly trends (for periods longer than 60 days), and daily sparkline trend indicators.
5. Output Generation: Saves report outputs in both raw text and markdown formats inside the output directory, and generates a single-page interactive HTML dashboard.

## Running Locally

Follow these steps to set up and run the project on your machine:

1. Clone this repository:
   ```bash
   git clone https://github.com/tui2019/Air-Raid-Analysis.git
   cd Air-Raid-Analysis
   ```

2. Set up a Python virtual environment:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

3. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Run the generator script:
   ```bash
   python generate_report.py --days 90
   ```
   * Use the `-d` or `--days` flag to specify the history window length in days (default is 30).

## Optional Gemini API Integration

You can optionally integrate the Gemini API to generate AI summaries and insights for the regional threat analysis.

To enable this:
1. Create a `.env` file in the project root directory.
2. Add your Gemini API key (you can obtain one from Google AI Studio) to the `.env` file:
   ```env
   GEMINI_API_KEY=your_api_key_here
   ```

If the key is present and the google-genai library is installed, the generation script will automatically contact the API and generate text/markdown AI reports (output/txt/ai_overview.txt and output/md/ai_overview.md), as well as inject these insights into the interactive HTML dashboard. If the API key is not configured, the script will gracefully skip the AI overview generation and complete all other reports and metrics normally.
