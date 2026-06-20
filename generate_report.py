#!/usr/bin/env python3
"""
Ukraine Air Raid Alerts: Time Series Data Generator and Reporter

This script processes the official air raid alert data from:
https://raw.githubusercontent.com/Vadimkin/ukrainian-air-raid-sirens-dataset/refs/heads/main/datasets/official_data_en.csv

It calculates:
1. Regional threat comparisons (siren counts, union threat durations).
2. Daily union threat timelines for all 26 regions (saved to CSV).
3. Monthly aggregated threat timelines (if query period > 60 days).
4. Nationwide and region-specific diurnal (hourly) and weekly seasonality profiles.
5. ASCII sparklines for visual trend inspection.

Outputs are written in a modular structure to:
- output/txt/
- output/csv/
"""

import os
import time
import argparse
import pandas as pd
import numpy as np
from datetime import timedelta, datetime

# Define remote data URL
DATA_URL = "https://raw.githubusercontent.com/Vadimkin/ukrainian-air-raid-sirens-dataset/refs/heads/main/datasets/official_data_en.csv"

# Output directories
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TXT_OUT_DIR = os.path.join(BASE_DIR, 'output', 'txt')
CSV_OUT_DIR = os.path.join(BASE_DIR, 'output', 'csv')

# Permanent alerts configuration (UTC start times)
PERMANENT_ALERTS = {
    'Luhanska oblast': pd.to_datetime('2022-04-04 16:45:00+00:00'),
    'Autonomous Republic of Crimea': pd.to_datetime('2022-12-10 22:22:00+00:00')
}

def merge_intervals(intervals):
    """
    Merges overlapping or touching intervals.
    intervals: list of tuples (start, end)
    """
    if not intervals:
        return []
    sorted_intervals = sorted(intervals, key=lambda x: x[0])
    merged = [sorted_intervals[0]]
    for current in sorted_intervals[1:]:
        prev_start, prev_end = merged[-1]
        curr_start, curr_end = current
        if curr_start <= prev_end:
            merged[-1] = (prev_start, max(prev_end, curr_end))
        else:
            merged.append(current)
    return merged

def split_to_daily_segments(oblast, start, end):
    """
    Splits a single alert interval spanning multiple days into segments for each day.
    Yields tuples of (oblast, date, segment_start, segment_end)
    """
    curr = start
    while curr < end:
        # Determine the end of the current day in UTC
        day_end = datetime(curr.year, curr.month, curr.day, 23, 59, 59, 999999, tzinfo=curr.tzinfo)
        seg_end = min(end, day_end)
        yield (oblast, curr.date(), curr, seg_end)
        # Advance to the start of the next day
        curr = datetime(curr.year, curr.month, curr.day, 0, 0, 0, 0, tzinfo=curr.tzinfo) + timedelta(days=1)

def split_to_hourly_segments(oblast, start, end):
    """
    Splits an alert interval into segments aligned with hourly bins of the day (0-23).
    Yields tuples of (oblast, weekday, hour, duration_seconds)
    """
    curr = start
    while curr < end:
        # Find the next hour boundary
        next_hour = datetime(curr.year, curr.month, curr.day, curr.hour, 0, 0, 0, tzinfo=curr.tzinfo) + timedelta(hours=1)
        seg_end = min(end, next_hour)
        dur = (seg_end - curr).total_seconds()
        yield (oblast, curr.weekday(), curr.hour, dur)
        curr = next_hour

def get_ascii_sparkline(daily_hours):
    """
    Converts a daily hours list/series into an ASCII sparkline.
    Key:  . = 0-3h, _ = 3-6h, - = 6-12h, = = 12-18h, # = 18-24h
    """
    sparkline = []
    for h in daily_hours:
        if h <= 3.0:
            sparkline.append('.')
        elif h <= 6.0:
            sparkline.append('_')
        elif h <= 12.0:
            sparkline.append('-')
        elif h <= 18.0:
            sparkline.append('=')
        else:
            sparkline.append('#')
    return "".join(sparkline)

def get_ascii_indicator(pct):
    """
    Generates a horizontal ASCII bar representing percentage.
    """
    bar_len = int(round(pct * 50))  # Max 50 characters
    return "█" * bar_len if bar_len > 0 else "."

def main():
    parser = argparse.ArgumentParser(description="Generate Ukraine air raid alerts reports.")
    parser.add_argument(
        '-d', '--days', 
        type=int, 
        default=30, 
        help="Number of days of history to analyze (default: 30)"
    )
    args = parser.parse_args()
    
    days_to_analyze = args.days
    if days_to_analyze <= 0:
        raise ValueError("Days parameter must be a positive integer.")
        
    # Delete old output directory if it exists to avoid mixing results
    output_parent_dir = os.path.join(BASE_DIR, 'output')
    if os.path.exists(output_parent_dir):
        import shutil
        shutil.rmtree(output_parent_dir)
        
    os.makedirs(TXT_OUT_DIR, exist_ok=True)
    os.makedirs(CSV_OUT_DIR, exist_ok=True)
    
    total_start = time.time()
    
    print(f"1. Fetching dataset from URL:\n   {DATA_URL}")
    t0 = time.time()
    try:
        df = pd.read_csv(DATA_URL)
    except Exception as e:
        print(f"\n[Error] Failed to load data from URL: {e}")
        return
    print(f"   Loaded {len(df)} rows in {time.time()-t0:.4f} seconds.")
    
    print("2. Parsing datetimes and cleaning data...")
    t0 = time.time()
    
    # Ensure source column exists
    if 'source' not in df.columns:
        df['source'] = 'official'
        
    # Get all unique oblasts including Crime
    all_oblasts = set(df['oblast'].dropna().unique())
    all_oblasts.update(PERMANENT_ALERTS.keys())
    all_oblasts = sorted(list(all_oblasts))
    
    df['started_at'] = pd.to_datetime(df['started_at'], utc=True)
    df['finished_at'] = pd.to_datetime(df['finished_at'], utc=True, errors='coerce')
    df = df.dropna(subset=['started_at'])
    
    # Find dataset max date robustly
    max_started = df['started_at'].max()
    max_finished = df['finished_at'].dropna().max()
    max_date = max(max_started, max_finished) if pd.notna(max_finished) else max_started
    
    # Fill unresolved alerts with max_date
    missing_finished = df['finished_at'].isna()
    if missing_finished.any():
        df.loc[missing_finished, 'finished_at'] = max_date
        
    start_date = max_date - timedelta(days=days_to_analyze)
    
    # Precise overlap filter
    recent_df = df[
        (df['finished_at'] >= start_date) & 
        (df['started_at'] <= max_date)
    ].copy()
    
    # Clip alert boundaries
    recent_df['started_at'] = recent_df['started_at'].clip(lower=start_date)
    recent_df['finished_at'] = recent_df['finished_at'].clip(upper=max_date)
    recent_df = recent_df[recent_df['finished_at'] >= recent_df['started_at']].copy()
    
    # Inject permanent alerts
    injected_rows = []
    for oblast, perm_start in PERMANENT_ALERTS.items():
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
        recent_df = pd.concat([recent_df, injected_df], ignore_index=True)
        
    # Calculate duration
    recent_df['duration'] = recent_df['finished_at'] - recent_df['started_at']
    print(f"   Parsed and cleaned {len(recent_df)} active alerts in {time.time()-t0:.4f} seconds.")
    
    print("3. Generating daily resampling grid...")
    t0 = time.time()
    
    # Split alerts into daily segments
    daily_segments = []
    for idx, row in recent_df.iterrows():
        daily_segments.extend(split_to_daily_segments(row['oblast'], row['started_at'], row['finished_at']))
        
    seg_df = pd.DataFrame(daily_segments, columns=['oblast', 'date', 'seg_start', 'seg_end'])
    
    # Generate complete index of (oblast, date) to ensure all days and oblasts are present
    full_dates = pd.date_range(start_date.date(), max_date.date()).date
    multi_index = pd.MultiIndex.from_product([all_oblasts, full_dates], names=['oblast', 'date'])
    daily_union_grid = pd.Series(0.0, index=multi_index).reset_index(name='union_hours')
    
    # Group segments by oblast and date to calculate union threat duration
    if not seg_df.empty:
        union_durations = {}
        for (oblast, date), grp in seg_df.groupby(['oblast', 'date']):
            intervals = list(zip(grp['seg_start'], grp['seg_end']))
            merged = merge_intervals(intervals)
            total_union_sec = sum((end - start).total_seconds() for start, end in merged)
            union_durations[(oblast, date)] = total_union_sec / 3600.0
            
        # Update daily union grid
        daily_union_grid['union_hours'] = daily_union_grid.set_index(['oblast', 'date']).index.map(union_durations).fillna(0.0)
        
    # Save daily timeline to CSV
    daily_csv_path = os.path.join(CSV_OUT_DIR, 'daily_regional_trends.csv')
    daily_union_grid.to_csv(daily_csv_path, index=False)
    print(f"   Daily union grid completed and saved to CSV in {time.time()-t0:.4f} seconds.")
    
    print("4. Calculating regional comparison stats...")
    t0 = time.time()
    
    # Union total duration per region (in hours and days)
    union_totals = daily_union_grid.groupby('oblast')['union_hours'].sum().reset_index(name='union_hours')
    union_totals['union_days'] = union_totals['union_hours'] / 24.0
    
    # Alert count (including injected permanent alert records)
    alert_counts = recent_df.groupby('oblast').size().reset_index(name='alert_count')
    
    # Merge stats together
    regional_stats = pd.DataFrame({'oblast': all_oblasts})
    regional_stats = pd.merge(regional_stats, union_totals, on='oblast', how='left')
    regional_stats = pd.merge(regional_stats, alert_counts, on='oblast', how='left')
    
    # Fill missing values
    regional_stats['union_hours'] = regional_stats['union_hours'].fillna(0.0)
    regional_stats['union_days'] = regional_stats['union_days'].fillna(0.0)
    regional_stats['alert_count'] = regional_stats['alert_count'].fillna(0).astype(int)
    
    # Calculate % of period active
    total_window_hours = (max_date - start_date).total_seconds() / 3600.0
    regional_stats['pct_active'] = (regional_stats['union_hours'] / total_window_hours) * 100.0
    
    # Sort descending
    regional_stats = regional_stats.sort_values(by=['union_hours', 'alert_count', 'oblast'], ascending=[False, False, True])
    
    # Save comparison to CSV
    compare_csv_path = os.path.join(CSV_OUT_DIR, 'oblast_duration_analysis.csv')
    regional_stats.to_csv(compare_csv_path, index=False)
    
    # Write TXT report 1: Regional Summary
    summary_txt_path = os.path.join(TXT_OUT_DIR, 'regional_summary.txt')
    with open(summary_txt_path, 'w') as f:
        f.write(f"================================================================================\n")
        f.write(f"UKRAINE AIR RAID ALERTS: REGIONAL COMPARISON REPORT\n")
        f.write(f"Period: {start_date.strftime('%Y-%m-%d %H:%M:%S UTC')} to {max_date.strftime('%Y-%m-%d %H:%M:%S UTC')} ({days_to_analyze} Days)\n")
        f.write(f"================================================================================\n\n")
        f.write(f"{'Oblast (Region)':<30} | {'Alerts':<6} | {'Hours':<11} | {'Days':<11} | {'% Time Active':<13}\n")
        f.write("-" * 84 + "\n")
        for _, row in regional_stats.iterrows():
            f.write(f"{row['oblast']:<30} | {row['alert_count']:<6} | {row['union_hours']:11.2f} | {row['union_days']:11.2f} | {row['pct_active']:11.2f}%\n")
        f.write("-" * 84 + "\n")
        f.write(f"Total alert records processed (excl. permanent): {alert_counts['alert_count'].sum()}\n")
    print(f"   Regional summary report saved.")
    
    print("5. Calculating seasonality profiles (hourly & weekly)...")
    t0 = time.time()
    
    # Merge overlapping intervals *per region* first to get regional union intervals.
    # This prevents active percentages from exceeding 100% when sub-regions (raions/hromadas)
    # are alerted simultaneously.
    union_intervals_by_region = []
    for oblast, grp in recent_df.groupby('oblast'):
        intervals = list(zip(grp['started_at'], grp['finished_at']))
        merged = merge_intervals(intervals)
        for start, end in merged:
            union_intervals_by_region.append({
                'oblast': oblast,
                'started_at': start,
                'finished_at': end
            })
    union_intervals_df = pd.DataFrame(union_intervals_by_region) if union_intervals_by_region else pd.DataFrame(columns=['oblast', 'started_at', 'finished_at'])

    # Split union intervals into hourly chunks
    hourly_segments = []
    if not union_intervals_df.empty:
        for idx, row in union_intervals_df.iterrows():
            hourly_segments.extend(split_to_hourly_segments(row['oblast'], row['started_at'], row['finished_at']))
        
    hour_df = pd.DataFrame(hourly_segments, columns=['oblast', 'weekday', 'hour', 'duration_seconds'])
    if hour_df.empty:
        hour_df = pd.DataFrame(columns=['oblast', 'weekday', 'hour', 'duration_seconds'])
    
    # Calculate exact capacities of weekdays in the window (including fractional start/end days)
    def get_weekday_capacities(start, end):
        segments = list(split_to_daily_segments('window', start, end))
        capacities = {i: 0.0 for i in range(7)}
        for _, date, seg_start, seg_end in segments:
            dur = (seg_end - seg_start).total_seconds() / 3600.0
            capacities[date.weekday()] += dur
        return capacities
        
    weekday_capacities = get_weekday_capacities(start_date, max_date)
        
    # Helper to calculate percentages
    def get_seasonality_data(df_slice, is_nationwide=False):
        # Hourly distribution
        h_sum = df_slice.groupby('hour')['duration_seconds'].sum().reset_index() if not df_slice.empty else pd.DataFrame(columns=['hour', 'duration_seconds'])
        if 'duration_seconds' not in h_sum.columns:
            h_sum['duration_seconds'] = 0.0
        h_sum['hours'] = h_sum['duration_seconds'] / 3600.0
        
        # Normalization: total capacity of each hour bin is exactly days_to_analyze hours.
        # For nationwide average, capacity is scaled by the total number of regions (all_oblasts).
        denom_hours = days_to_analyze * len(all_oblasts) if is_nationwide else days_to_analyze
        h_sum['pct'] = (h_sum['hours'] / denom_hours) * 100.0
        
        # Ensure all 24 hours are represented
        h_map = pd.DataFrame({'hour': range(24)})
        h_sum = pd.merge(h_map, h_sum, on='hour', how='left').fillna(0.0)
        
        # Weekly distribution
        w_sum = df_slice.groupby('weekday')['duration_seconds'].sum().reset_index() if not df_slice.empty else pd.DataFrame(columns=['weekday', 'duration_seconds'])
        if 'duration_seconds' not in w_sum.columns:
            w_sum['duration_seconds'] = 0.0
        w_sum['hours'] = w_sum['duration_seconds'] / 3600.0
        
        # Normalization: total capacity of each weekday is weekday_capacities[weekday] hours.
        # For nationwide average, capacity is scaled by the total number of regions.
        denom_multiplier = len(all_oblasts) if is_nationwide else 1.0
        w_sum['pct'] = w_sum.apply(
            lambda r: (r['hours'] / (weekday_capacities[int(r['weekday'])] * denom_multiplier)) * 100.0 
            if weekday_capacities[int(r['weekday'])] > 0 else 0.0, 
            axis=1
        )
        
        # Ensure all 7 weekdays are represented
        w_map = pd.DataFrame({'weekday': range(7)})
        w_sum = pd.merge(w_map, w_sum, on='weekday', how='left').fillna(0.0)
        
        return h_sum, w_sum

    # A. Nationwide seasonality
    h_nat, w_nat = get_seasonality_data(hour_df, is_nationwide=True)
    
    weekday_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    
    nation_txt_path = os.path.join(TXT_OUT_DIR, 'seasonality_nationwide.txt')
    with open(nation_txt_path, 'w') as f:
        f.write(f"================================================================================\n")
        f.write(f"NATIONWIDE SEASONALITY PATTERNS (UTC)\n")
        f.write(f"Period: {start_date.strftime('%Y-%m-%d')} to {max_date.strftime('%Y-%m-%d')}\n")
        f.write(f"================================================================================\n\n")
        
        f.write(f"1. DIURNAL (HOURLY) THREAT DISTRIBUTION (UTC)\n")
        f.write(f"Represents the average % of time a region is under alert during each hour bin.\n\n")
        f.write(f"{'Hour (UTC)':<12} | {'Active %':<10} | {'ASCII Heat Indicator':<50}\n")
        f.write("-" * 80 + "\n")
        h_nat_min, h_nat_max = h_nat['pct'].min(), h_nat['pct'].max()
        has_var_h_nat = (h_nat_min != h_nat_max)
        for _, row in h_nat.iterrows():
            hour_str = f"{int(row['hour']):02d}:00-{int(row['hour'])+1:02d}:00"
            label = ""
            if has_var_h_nat:
                if row['pct'] == h_nat_max:
                    label = " (Max)"
                elif row['pct'] == h_nat_min:
                    label = " (Min)"
            f.write(f"{hour_str:<12} | {row['pct']:9.2f}% | {get_ascii_indicator(row['pct']/100.0)}{label}\n")
            
        f.write(f"\n2. WEEKLY THREAT DISTRIBUTION\n")
        f.write(f"Represents the average % of time warning sirens are active on each day of the week.\n\n")
        f.write(f"{'Weekday':<12} | {'Active %':<10} | {'ASCII Heat Indicator':<50}\n")
        f.write("-" * 80 + "\n")
        w_nat_min, w_nat_max = w_nat['pct'].min(), w_nat['pct'].max()
        has_var_w_nat = (w_nat_min != w_nat_max)
        for _, row in w_nat.iterrows():
            label = ""
            if has_var_w_nat:
                if row['pct'] == w_nat_max:
                    label = " (Max)"
                elif row['pct'] == w_nat_min:
                    label = " (Min)"
            f.write(f"{weekday_names[int(row['weekday'])]:<12} | {row['pct']:9.2f}% | {get_ascii_indicator(row['pct']/100.0)}{label}\n")
            
    # B. Regional seasonality (written to a dedicated file)
    regional_txt_path = os.path.join(TXT_OUT_DIR, 'seasonality_regional.txt')
    with open(regional_txt_path, 'w') as f:
        f.write(f"================================================================================\n")
        f.write(f"REGION-SPECIFIC SEASONALITY PROFILES (UTC)\n")
        f.write(f"Period: {start_date.strftime('%Y-%m-%d')} to {max_date.strftime('%Y-%m-%d')}\n")
        f.write(f"================================================================================\n\n")
        
        # Loop through sorted regions to show their individual seasonality
        for oblast in regional_stats['oblast']:
            grp = hour_df[hour_df['oblast'] == oblast]
            f.write(f"OBLAST: {oblast.upper()}\n")
            f.write(f"=" * 80 + "\n")
            
            if grp.empty:
                f.write("No alerts recorded in this region during this query window.\n\n\n")
                continue
                
            h_reg, w_reg = get_seasonality_data(grp)
            
            f.write(f"Hourly Threat Distribution (UTC):\n")
            h_reg_min, h_reg_max = h_reg['pct'].min(), h_reg['pct'].max()
            has_var_h_reg = (h_reg_min != h_reg_max)
            for _, row in h_reg.iterrows():
                hour_str = f"{int(row['hour']):02d}:00-{int(row['hour'])+1:02d}:00"
                label = ""
                if has_var_h_reg:
                    if row['pct'] == h_reg_max:
                        label = " (Max)"
                    elif row['pct'] == h_reg_min:
                        label = " (Min)"
                f.write(f"  {hour_str:<12} | {row['pct']:6.2f}% | {get_ascii_indicator(row['pct']/100.0)}{label}\n")
                
            f.write(f"\nWeekly Threat Distribution:\n")
            w_reg_min, w_reg_max = w_reg['pct'].min(), w_reg['pct'].max()
            has_var_w_reg = (w_reg_min != w_reg_max)
            for _, row in w_reg.iterrows():
                label = ""
                if has_var_w_reg:
                    if row['pct'] == w_reg_max:
                        label = " (Max)"
                    elif row['pct'] == w_reg_min:
                        label = " (Min)"
                f.write(f"  {weekday_names[int(row['weekday'])]:<12} | {row['pct']:6.2f}% | {get_ascii_indicator(row['pct']/100.0)}{label}\n")
            f.write("\n\n" + "-" * 80 + "\n\n")
            
    print(f"   Seasonality reports saved.")
    
    # 6. Monthly aggregation (if period > 60 days)
    if days_to_analyze > 60:
        print("6. Calculating historical monthly trends...")
        daily_union_grid['month'] = pd.to_datetime(daily_union_grid['date']).dt.to_period('M')
        monthly_union = daily_union_grid.groupby(['oblast', 'month'])['union_hours'].sum().reset_index()
        
        # Pivot table
        monthly_pivot = monthly_union.pivot(index='oblast', columns='month', values='union_hours').fillna(0.0)
        
        monthly_txt_path = os.path.join(TXT_OUT_DIR, 'historical_monthly.txt')
        with open(monthly_txt_path, 'w') as f:
            f.write(f"================================================================================\n")
            f.write(f"HISTORICAL MONTHLY THREAT TRENDS (Union Hours per Month)\n")
            f.write(f"================================================================================\n\n")
            
            # Format header
            months_headers = [str(col) for col in monthly_pivot.columns]
            header_str = f"{'Oblast (Region)':<30} | " + " | ".join(f"{m:<10}" for m in months_headers)
            f.write(header_str + "\n")
            f.write("-" * len(header_str) + "\n")
            
            # Sort monthly_pivot by latest month values descending
            latest_month = monthly_pivot.columns[-1]
            monthly_pivot = monthly_pivot.sort_values(by=latest_month, ascending=False)
            
            for oblast, row in monthly_pivot.iterrows():
                row_str = f"{oblast:<30} | " + " | ".join(f"{row[m]:10.2f}" for m in monthly_pivot.columns)
                f.write(row_str + "\n")
            f.write("-" * len(header_str) + "\n")
        print(f"   Monthly trends report saved.")
        
    print("7. Generating daily sparkline trends...")
    # Generate daily sparklines for all regions
    sparklines = []
    # Pivot daily union grid to get dates as columns
    daily_pivot = daily_union_grid.pivot(index='oblast', columns='date', values='union_hours').fillna(0.0)
    
    # Sort daily pivot by latest regional summary rank
    daily_pivot = daily_pivot.reindex(regional_stats['oblast'])
    
    spark_txt_path = os.path.join(TXT_OUT_DIR, 'daily_trends_sparklines.txt')
    with open(spark_txt_path, 'w') as f:
        f.write(f"================================================================================\n")
        f.write(f"DAILY THREAT ACTIVITY TREND LINES (Last {days_to_analyze} Days)\n")
        f.write(f"Key:  . = 0-3h, _ = 3-6h, - = 6-12h, = = 12-18h, # = 18-24h active threat per day\n")
        f.write(f"================================================================================\n\n")
        f.write(f"{'Oblast (Region)':<30} | Daily Threat Profile (Timeline ->)\n")
        f.write("-" * 80 + "\n")
        for oblast, row in daily_pivot.iterrows():
            f.write(f"{oblast:<30} | {get_ascii_sparkline(row)}\n")
        f.write("-" * 80 + "\n")
    print(f"   Daily sparklines report saved.")
    
    total_time = time.time() - total_start
    print(f"\n================================================================================")
    f"SUCCESS: Data processed and structured reports saved in output/txt/ and output/csv/"
    print(f"Total processing time: {total_time:.4f} seconds.")
    print(f"================================================================================\n")

if __name__ == '__main__':
    main()
