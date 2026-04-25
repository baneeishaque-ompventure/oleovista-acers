import sys
import datetime
import os
from collections import defaultdict
import re

def format_duration(seconds):
    """Formats seconds into HH:MM:SS."""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    return f"{h:02d}:{m:02d}:{s:02d}"

def parse_line(line):
    """Parses a single log line into a dictionary."""
    match = re.match(r'^(\d{2}/\d{2}/\d{4})\s+\w+\s+(\d{2}:\d{2}:\d{2})\s+(\d{2}:\d{2}:\d{2})\s+"(.*)"', line)
    if not match:
        return None
    
    date_str, start_str, end_str, desc = match.groups()
    try:
        start_time = datetime.datetime.strptime(start_str, "%H:%M:%S")
        end_time = datetime.datetime.strptime(end_str, "%H:%M:%S")
        duration = (end_time - start_time).total_seconds()
        if duration < 0: duration += 24 * 3600
        return {"date": date_str, "range": f"{start_str} - {end_str}", "desc": desc, "duration": duration}
    except ValueError:
        return None

def main():
    if len(sys.argv) < 2:
        print("Usage: python analyze_time.py <filename>")
        return

    input_filename = sys.argv[1]
    output_filename = os.path.splitext(input_filename)[0] + ".md"
    
    entries = []
    try:
        with open(input_filename, 'r') as f:
            for line in f:
                parsed = parse_line(line.strip())
                if parsed: entries.append(parsed)
    except FileNotFoundError:
        print(f"Error: File '{input_filename}' not found.")
        return

    if not entries:
        print("No valid entries found.")
        return

    days_data = defaultdict(list)
    for e in entries: days_data[e['date']].append(e)
    sorted_dates = sorted(days_data.keys(), key=lambda x: datetime.datetime.strptime(x, "%d/%m/%Y"))
    
    total_seconds = sum(e['duration'] for e in entries)
    num_days = len(sorted_dates)
    avg_seconds = total_seconds / num_days if num_days > 0 else 0

    with open(output_filename, 'w') as f:
        f.write(f"# Time Tracking Analysis - {os.path.basename(input_filename)}\n")

        # --- 1. MONTHLY SUMMARY ---
        f.write("\n## Monthly Statistics\n")
        f.write("| Metric | Value |\n")
        f.write("| :--- | :--- |\n")
        f.write(f"| **Total Monthly Time** | {format_duration(total_seconds)} ({total_seconds/3600:.2f} hours) |\n")
        f.write(f"| **Average Daily Time** | {format_duration(avg_seconds)} ({avg_seconds/3600:.2f} hours) |\n")
        f.write(f"| **Number of Active Days** | {num_days} |\n")

        # --- 2. DAILY SUMMARIES ---
        f.write("\n## Daily Summaries\n")
        for date in sorted_dates:
            day_entries = days_data[date]
            day_total = sum(e['duration'] for e in day_entries)
            f.write(f"\n### {date} (Total: {format_duration(day_total)})\n")
            f.write("| Time Range | Duration | Description |\n")
            f.write("| :--- | :--- | :--- |\n")
            for e in day_entries:
                f.write(f"| {e['range']} | {format_duration(e['duration'])} | {e['desc']} |\n")

        # --- 3. ALL ENTRIES ---
        f.write("\n## Full Entry Log\n")
        f.write("| Date | Time Range | Duration | Description |\n")
        f.write("| :--- | :--- | :--- | :--- |\n")
        for e in entries:
            f.write(f"| {e['date']} | {e['range']} | {format_duration(e['duration'])} | {e['desc']} |\n")

    print(f"Successfully analyzed '{input_filename}'")
    print(f"Saved Markdown report to: '{output_filename}'")
    print("-" * 40)
    print(f"Total Month Time: {format_duration(total_seconds)} ({total_seconds/3600:.2f} hours)")
    print(f"Average Day Time: {format_duration(avg_seconds)}")
    print("-" * 40)

if __name__ == "__main__":
    main()
