#!/usr/bin/env python3
"""
Air Raid Alerts Analysis Script

This script processes Ukraine's official air raid alert data pulled directly from:
https://raw.githubusercontent.com/Vadimkin/ukrainian-air-raid-sirens-dataset/refs/heads/main/datasets/official_data_en.csv

It extracts alerts for a user-specified number of days (relative to the maximum date in the dataset)
and calculates durations per oblast, saving results to static file paths to avoid cluttering.
"""

import os
import time
import argparse
import pandas as pd
import numpy as np
from datetime import timedelta

# Define paths (now pulling directly from remote URL)
DATA_URL = "https://raw.githubusercontent.com/Vadimkin/ukrainian-air-raid-sirens-dataset/refs/heads/main/datasets/official_data_en.csv"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Permanent alerts configuration (UTC start times)
PERMANENT_ALERTS = {
    'Luhanska oblast': pd.to_datetime('2022-04-04 16:45:00+00:00'),
    'Autonomous Republic of Crimea': pd.to_datetime('2022-12-10 22:22:00+00:00')
}

def merge_intervals(intervals):
    """
    Merges overlapping intervals.
    intervals: list of tuples/lists (start, end)
    Returns: list of merged intervals (start, end)
    
    Note: Adjacent/touching intervals (e.g., 10:00-11:00 and 11:00-12:00) are merged
    into a single continuous interval (10:00-12:00) as they represent a continuous threat.
    """
    if not intervals:
        return []
    
    # Sort intervals by start time
    sorted_intervals = sorted(intervals, key=lambda x: x[0])
    merged = [sorted_intervals[0]]
    
    for current in sorted_intervals[1:]:
        prev_start, prev_end = merged[-1]
        curr_start, curr_end = current
        
        if curr_start <= prev_end:
            # Overlapping or touching intervals, merge them
            merged[-1] = (prev_start, max(prev_end, curr_end))
        else:
            merged.append(current)
            
    return merged

def main():
    parser = argparse.ArgumentParser(description="Analyze Ukraine air raid alert durations by region.")
    parser.add_argument(
        '-d', '--days', 
        type=int, 
        default=30, 
        help="Number of days of historical data to analyze (default: 30)"
    )
    args = parser.parse_args()
    
    days_to_analyze = args.days
    if days_to_analyze <= 0:
        raise ValueError("The number of days must be a positive integer.")
        
    total_start = time.time()
    
    print(f"1. Loading dataset from remote URL:\n   {DATA_URL}")
    t0 = time.time()
    
    # Read the dataset directly from URL
    try:
        df = pd.read_csv(DATA_URL)
    except Exception as e:
        print(f"\n[Error] Failed to download or parse data from remote URL: {e}")
        return
        
    t_load = time.time() - t0
    print(f"   Loaded {len(df)} records in {t_load:.4f} seconds.")
    
    print(f"2. Normalizing timezones and parsing datetime columns (robust)...")
    t0 = time.time()
    
    # Get all unique oblasts in the entire dataset, and ensure Crimea is included
    all_oblasts = set(df['oblast'].dropna().unique())
    all_oblasts.update(PERMANENT_ALERTS.keys())
    all_oblasts = sorted(list(all_oblasts))
    
    # Robustly parse all started_at and finished_at columns as UTC
    df['started_at'] = pd.to_datetime(df['started_at'], utc=True)
    df['finished_at'] = pd.to_datetime(df['finished_at'], utc=True, errors='coerce')
    
    # Drop rows with invalid started_at
    df = df.dropna(subset=['started_at'])
    
    # Robustly determine the true end of the dataset timeline (Issue #8)
    max_started = df['started_at'].max()
    max_finished = df['finished_at'].dropna().max()
    max_date = max(max_started, max_finished) if pd.notna(max_finished) else max_started
    
    # Option A: Fill missing finished_at (unresolved alerts) with the true end of the dataset timeline
    missing_finished = df['finished_at'].isna()
    if missing_finished.any():
        df.loc[missing_finished, 'finished_at'] = max_date
        
    # Calculate the threshold for the requested window
    start_date = max_date - timedelta(days=days_to_analyze)
    
    # Ensure source column exists to prevent KeyError in grouping (Issue #9)
    if 'source' not in df.columns:
        df['source'] = 'official'
    
    # Mathematically correct filter: alert overlaps with the [start_date, max_date] window
    recent_df = df[
        (df['finished_at'] >= start_date) & 
        (df['started_at'] <= max_date)
    ].copy()
    
    # Clip alert intervals to the query window boundaries
    recent_df['started_at'] = recent_df['started_at'].clip(lower=start_date)
    recent_df['finished_at'] = recent_df['finished_at'].clip(upper=max_date)
    
    # Clean negative durations (safety check for malformed data)
    recent_df = recent_df[recent_df['finished_at'] >= recent_df['started_at']].copy()
    
    t_parse = time.time() - t0
    print(f"   Filtered, parsed, and clipped {len(recent_df)} recent records in {t_parse:.4f} seconds.")
    
    print("3. Handling permanent alerts...")
    t0 = time.time()
    
    # Inject permanent alerts if they overlap with the query window
    injected_rows = []
    for oblast, perm_start in PERMANENT_ALERTS.items():
        # Check if the permanent alert started before the end of the query window
        if perm_start < max_date:
            actual_start = max(start_date, perm_start)
            actual_end = max_date
            injected_rows.append({
                'oblast': oblast,
                'started_at': actual_start,
                'finished_at': actual_end,
                'level': 'oblast',
                'source': 'official_permanent'
            })
            
    if injected_rows:
        injected_df = pd.DataFrame(injected_rows)
        # Append permanent alerts (overlaps will be merged, preserving Crimea/Luhansk duplicates)
        recent_df = pd.concat([recent_df, injected_df], ignore_index=True)
        print(f"   Injected {len(injected_rows)} permanent alerts for this query window.")
        
    # Calculate duration for each individual alert
    recent_df['duration'] = recent_df['finished_at'] - recent_df['started_at']
    
    t_perm = time.time() - t0
    
    print("4. Calculating durations...")
    t0 = time.time()
    
    # Create base DataFrame with all unique oblasts
    results = pd.DataFrame({'oblast': all_oblasts})
    
    # A. Method 1: Cumulative Duration (Sum of all alert records)
    cumulative = recent_df.groupby('oblast')['duration'].sum().reset_index()
    cumulative.rename(columns={'duration': 'cumulative_duration'}, inplace=True)
    
    # B. Method 2: Union Duration (Merging overlapping intervals)
    union_durations = {}
    for oblast, group in recent_df.groupby('oblast'):
        intervals = list(zip(group['started_at'], group['finished_at']))
        merged = merge_intervals(intervals)
        total_union = sum((end - start for start, end in merged), timedelta())
        union_durations[oblast] = total_union
        
    union_df = pd.DataFrame(list(union_durations.items()), columns=['oblast', 'union_duration'])
    
    # Merge all metrics onto the base DataFrame
    results = pd.merge(results, cumulative, on='oblast', how='left')
    results = pd.merge(results, union_df, on='oblast', how='left')
    
    # Add count of alerts (excluding injected permanent alert records to prevent count inflation)
    alert_counts = recent_df[recent_df['source'] != 'official_permanent'].groupby('oblast').size().reset_index(name='alert_count')
    results = pd.merge(results, alert_counts, on='oblast', how='left')
    
    # Fill NaN values for oblasts with 0 alerts in the last X days
    results['cumulative_duration'] = results['cumulative_duration'].fillna(timedelta())
    results['union_duration'] = results['union_duration'].fillna(timedelta())
    results['alert_count'] = results['alert_count'].fillna(0).astype(int)
    
    # Convert timedeltas to human-readable hours / days
    results['cumulative_days'] = results['cumulative_duration'].dt.total_seconds() / 86400.0
    results['union_hours'] = results['union_duration'].dt.total_seconds() / 3600.0
    
    # Sort by Union Duration descending, then by alert count, then alphabetically
    results = results.sort_values(by=['union_hours', 'alert_count', 'oblast'], ascending=[False, False, True])
    
    t_calc = time.time() - t0
    print(f"   Calculated durations in {t_calc:.4f} seconds.")
    
    # Display the results
    print("\n" + "="*70)
    print(f"{'Oblast (Region)':<30} | {'Alerts':<6} | {'Union (Hrs)':<12} | {'Cumulative (Days)':<17}")
    print("="*70)
    for _, row in results.iterrows():
        print(f"{row['oblast']:<30} | {row['alert_count']:<6} | {row['union_hours']:11.2f} | {row['cumulative_days']:17.2f}")
    print("="*70)
    
    # Save output to static CSV filename to avoid folder clutter
    output_file = os.path.join(BASE_DIR, 'oblast_duration_analysis.csv')
    results.to_csv(output_file, index=False)
    print(f"\nResults saved to: {output_file}")
    
    # Create simple text summary in static txt filename
    summary_file = os.path.join(BASE_DIR, 'analysis_summary.txt')
    with open(summary_file, 'w') as f:
        f.write(f"Ukraine Air Raid Alerts Duration Analysis (Last {days_to_analyze} Days)\n")
        f.write(f"Reference Period: {start_date} to {max_date} (UTC)\n")
        f.write(f"Total alert records: {len(recent_df)}\n\n")
        f.write(f"{'Oblast':<30} | {'Alerts':<6} | {'Union (Hrs)':<12} | {'Cumulative (Days)':<17}\n")
        f.write("-" * 77 + "\n")
        for _, row in results.iterrows():
            f.write(f"{row['oblast']:<30} | {row['alert_count']:<6} | {row['union_hours']:11.2f} | {row['cumulative_days']:17.2f}\n")
    print(f"Summary written to: {summary_file}")
    
    total_time = time.time() - total_start
    print(f"\nTotal Execution Time: {total_time:.4f} seconds.")

if __name__ == '__main__':
    main()
