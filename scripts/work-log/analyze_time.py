import sys
import datetime
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
    # Pattern: DD/MM/YYYY Day StartTime EndTime "Description"
    match = re.match(r'^(\d{2}/\d{2}/\d{4})\s+\w+\s+(\d{2}:\d{2}:\d{2})\s+(\d{2}:\d{2}:\d{2})\s+"(.*)"', line)
    if not match:
        return None
    
    date_str, start_str, end_str, desc = match.groups()
    
    try:
        # We only care about time for duration calculation
        start_time = datetime.datetime.strptime(start_str, "%H:%M:%S")
        end_time = datetime.datetime.strptime(end_str, "%H:%M:%S")
        
        duration = (end_time - start_time).total_seconds()
        
        # Safety check for midnight crossing, though user said no crossings exist now
        if duration < 0:
            duration += 24 * 3600
            
        return {
            "date": date_str,
            "range": f"{start_str} - {end_str}",
            "desc": desc,
            "duration": duration
        }
    except ValueError:
        return None

def main():
    if len(sys.argv) < 2:
        print("Usage: python analyze_time.py <filename>")
        return

    filename = sys.argv[1]
    entries = []
    
    try:
        with open(filename, 'r') as f:
            for line in f:
                parsed = parse_line(line.strip())
                if parsed:
                    entries.append(parsed)
    except FileNotFoundError:
        print(f"Error: File '{filename}' not found.")
        return

    if not entries:
        print("No valid entries found in the file.")
        return

    # --- TABLE 1: EACH ENTRY ---
    print("\n" + "="*100)
    print(f"{'TABLE 1: INDIVIDUAL ENTRIES':^100}")
    print("="*100)
    header = f"{'Date':<12} | {'Time Range':<22} | {'Duration':<10} | {'Entry Description'}"
    print(header)
    print("-" * len(header))
    
    for e in entries:
        print(f"{e['date']:<12} | {e['range']:<22} | {format_duration(e['duration']):<10} | {e['desc']}")
    
    # --- TABLE 2: GROUPED BY DAY ---
    print("\n" + "="*100)
    print(f"{'TABLE 2: DAILY SUMMARY & DETAILS':^100}")
    print("="*100)
    
    days_data = defaultdict(list)
    for e in entries:
        days_data[e['date']].append(e)
    
    # Sort dates chronologically
    sorted_dates = sorted(days_data.keys(), key=lambda x: datetime.datetime.strptime(x, "%d/%m/%Y"))
    
    total_month_seconds = 0
    for date in sorted_dates:
        day_entries = days_data[date]
        day_total = sum(e['duration'] for e in day_entries)
        total_month_seconds += day_total
        
        day_header = f"DATE: {date} | TOTAL TIME: {format_duration(day_total)}"
        print(f"\n{day_header}")
        print("-" * len(day_header))
        for e in day_entries:
            print(f"  [{format_duration(e['duration'])}] {e['range']} -> {e['desc']}")
    
    # --- FINAL SUMMARY ---
    num_days = len(sorted_dates)
    avg_seconds = total_month_seconds / num_days if num_days > 0 else 0
    
    print("\n" + "="*40)
    print(f"{'MONTHLY TOTALS':^40}")
    print("="*40)
    print(f"Total Time for Month:  {format_duration(total_month_seconds)} ({total_month_seconds/3600:.2f} hours)")
    print(f"Average Time per Day:  {format_duration(avg_seconds)} ({avg_seconds/3600:.2f} hours)")
    print(f"Number of Active Days: {num_days}")
    print("="*40 + "\n")

if __name__ == "__main__":
    main()
