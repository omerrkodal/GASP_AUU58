#!/usr/bin/env python3
"""
UE FPS Chart Parser
Parses Unreal Engine FPS chart dump files and appends results to a master CSV.

Usage:
    python fps_parser.py <folder_path>
    python fps_parser.py <folder_path> --scenario "2A - All Enabled"
    python fps_parser.py <folder_path> --all          (process every file in folder)

Example:
    python fps_parser.py "Saved/Profiling/FPSChartStats"
    python fps_parser.py "Saved/Profiling/FPSChartStats" --scenario "2A - All Enabled"
"""

import os
import re
import csv
import sys
import argparse
from datetime import datetime
from pathlib import Path


# ---------------------------------------------------------------------------
# FILE DISCOVERY
# ---------------------------------------------------------------------------

def find_latest_chart_file(folder: Path) -> Path:
    files = [f for f in folder.rglob('*.log') if f.is_file()]
    if not files:
        raise FileNotFoundError(f"No .log files found in: {folder} or its subfolders")
    return max(files, key=lambda f: f.stat().st_mtime)


def find_all_chart_files(folder: Path) -> list:
    files = [f for f in folder.rglob('*.log') if f.is_file()]
    if not files:
        raise FileNotFoundError(f"No .log files found in: {folder} or its subfolders")
    return sorted(files, key=lambda f: f.stat().st_mtime)


# ---------------------------------------------------------------------------
# PARSING
# ---------------------------------------------------------------------------

def _find(pattern, text, group=1, default=None):
    m = re.search(pattern, text)
    return m.group(group) if m else default


def _worst_hitch_bucket(content: str) -> str:
    buckets = [
        (r'Bucket: 5\.00s - inf\s+Count: (\d+)',        '>5.0s'),
        (r'Bucket: 2\.50s - 5\.00s\s+Count: (\d+)',     '2.5-5.0s'),
        (r'Bucket: 2\.00s - 2\.50s\s+Count: (\d+)',     '2.0-2.5s'),
        (r'Bucket: 1\.50s - 2\.00s\s+Count: (\d+)',     '1.5-2.0s'),
        (r'Bucket: 1\.00s - 1\.50s\s+Count: (\d+)',     '1.0-1.5s'),
        (r'Bucket: 0\.75s - 1\.00s\s+Count: (\d+)',     '0.75-1.0s'),
        (r'Bucket: 0\.50s - 0\.75s\s+Count: (\d+)',     '0.5-0.75s'),
        (r'Bucket: 0\.30s - 0\.50s\s+Count: (\d+)',     '0.3-0.5s'),
        (r'Bucket: 0\.20s - 0\.30s\s+Count: (\d+)',     '0.2-0.3s'),
        (r'Bucket: 0\.15s - 0\.20s\s+Count: (\d+)',     '0.15-0.2s'),
        (r'Bucket: 0\.10s - 0\.15s\s+Count: (\d+)',     '0.1-0.15s'),
        (r'Bucket: 0\.06s - 0\.10s\s+Count: (\d+)',     '0.06-0.1s'),
        (r'Bucket: 0\.03s - 0\.06s\s+Count: (\d+)',     '0.03-0.06s'),
    ]
    for pattern, label in buckets:
        m = re.search(pattern, content)
        if m and int(m.group(1)) > 0:
            return f"{label} (x{m.group(1)})"
    return 'None'


def _bottleneck(gt: float, rt: float, gpu: float) -> str:
    d = {'GameThread': gt, 'RenderThread': rt, 'GPU': gpu}
    top = max(d, key=d.get)
    return top if d[top] > 0 else 'None'


def parse_fps_chart(file_path: Path) -> dict:
    content = file_path.read_text(encoding='utf-8', errors='ignore')

    dump_time = _find(r'Dumping FPS chart at (\S+)',         content) or 'Unknown'
    level     = _find(r"for level '([^']+)'",                content) or 'Unknown'
    frames    = int(_find(r'(\d+) frames collected',         content) or 0)
    duration  = float(_find(r'over ([\d.]+) seconds',        content) or 0)
    avg_fps   = float(_find(r'for a ([\d.]+) FPS average',   content) or 0)

    gpu_ms = float(_find(r'Average GPU frametime: ([\d.]+)',          content) or 0)
    rt_ms  = float(_find(r'Average RenderThread frametime: ([\d.]+)', content) or 0)
    gt_ms  = float(_find(r'Average GameThread frametime: ([\d.]+)',   content) or 0)

    bound_gt  = float(_find(r'BoundGameThreadPct: ([\d.]+)',   content) or 0)
    bound_rt  = float(_find(r'BoundRenderThreadPct: ([\d.]+)', content) or 0)
    bound_gpu = float(_find(r'BoundGPUPct: ([\d.]+)',          content) or 0)

    hitch_count   = int(_find(r'Total hitch count:\s+(\d+)',           content) or 0)
    hitch_pct     = float(_find(r'Total hitch time:.*?\(([\d.]+) %\)', content) or 0)
    hitches_p_min = float(_find(r'Hitches / min:\s+([\d.]+)',          content) or 0)

    # ---------------------------------------------------------
    # CALCULATE 1% LOW FPS FROM COMPANION .CSV FILE
    # ---------------------------------------------------------
    csv_file = file_path.with_suffix('.csv')
    one_percent_low_fps = 0.0
    
    if csv_file.exists():
        try:
            frame_times_ms = []
            with csv_file.open('r', encoding='utf-8') as cf:
                # Skip until we hit the actual frame data header
                for line in cf:
                    if line.startswith('Time (sec)'):
                        break
                
                # Parse all remaining frames
                for line in cf:
                    parts = line.strip().split(',')
                    if len(parts) >= 2:
                        try:
                            # Frame (ms) is the second column
                            frame_times_ms.append(float(parts[1]))
                        except ValueError:
                            pass
            
            if frame_times_ms:
                # To find 1% lows: sort by frame time descending (slowest frames first)
                frame_times_ms.sort(reverse=True)
                
                # Get the top 1% worst frames
                one_percent_count = max(1, int(len(frame_times_ms) * 0.01))
                worst_1_percent_frames = frame_times_ms[:one_percent_count]
                
                # Average the worst 1% frame times, then convert to FPS
                avg_worst_ms = sum(worst_1_percent_frames) / len(worst_1_percent_frames)
                if avg_worst_ms > 0:
                    one_percent_low_fps = round(1000.0 / avg_worst_ms, 2)
        except Exception as e:
            print(f"  Warning: Could not parse 1% lows from {csv_file.name}: {e}")

    return {
        'dump_time':       dump_time,
        'level':           level,
        'duration_s':      round(duration, 2),
        'frames':          frames,
        'avg_fps':         round(avg_fps,    2),
        '1%_low_fps':      one_percent_low_fps,
        'gt_ms':           round(gt_ms,      2),
        'rt_ms':           round(rt_ms,      2),
        'gpu_ms':          round(gpu_ms,     2),
        'bound_gt_pct':    round(bound_gt,   2),
        'bound_rt_pct':    round(bound_rt,   2),
        'bound_gpu_pct':   round(bound_gpu,  2),
        'bottleneck':      _bottleneck(bound_gt, bound_rt, bound_gpu),
        'hitch_count':     hitch_count,
        'hitch_pct':       round(hitch_pct, 2),
        'hitches_per_min': round(hitches_p_min, 2),
        'worst_hitch':     _worst_hitch_bucket(content),
    }


# ---------------------------------------------------------------------------
# CSV OUTPUT
# ---------------------------------------------------------------------------

FIELDNAMES = [
    'Scenario', 'Avg FPS', '1% Low FPS', 'GameThread ms', 'RenderThread ms', 'GPU ms',
    'Bottleneck', 'Hitches', 'Hitch %', 'Worst Hitch'
]


def append_to_csv(metrics: dict, scenario: str, output_csv: Path):
    def localize_number(val):
        if isinstance(val, (float, int)):
            # Convert to string and replace decimal point with a comma
            return str(val).replace('.', ',')
        return val

    row = {
        'Scenario':        scenario,
        'Avg FPS':         localize_number(metrics['avg_fps']),
        '1% Low FPS':      localize_number(metrics['1%_low_fps']),
        'GameThread ms':   localize_number(metrics['gt_ms']),
        'RenderThread ms': localize_number(metrics['rt_ms']),
        'GPU ms':          localize_number(metrics['gpu_ms']),
        'Bottleneck':      metrics['bottleneck'],
        'Hitches':         localize_number(metrics['hitch_count']),
        'Hitch %':         localize_number(metrics['hitch_pct']),
        'Worst Hitch':     metrics['worst_hitch'],
    }
    file_exists = output_csv.exists()
    with output_csv.open('a', newline='', encoding='utf-8') as f:
        # Using semicolon delimiter for regions where comma is the decimal point
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES, delimiter=';')
        if not file_exists:
            writer.writeheader()
        writer.writerow(row)


# ---------------------------------------------------------------------------
# PRINT
# ---------------------------------------------------------------------------

def print_summary(metrics: dict, scenario: str, source: str, output: Path):
    print(f"\n  OK  {scenario}  <-  {source}")
    print(f"     Avg FPS      : {metrics['avg_fps']}")
    print(f"     1% Low FPS   : {metrics['1%_low_fps']}")
    print(f"     GameThread   : {metrics['gt_ms']} ms  (bound {metrics['bound_gt_pct']}%)")
    print(f"     RenderThread : {metrics['rt_ms']} ms  (bound {metrics['bound_rt_pct']}%)")
    print(f"     GPU          : {metrics['gpu_ms']} ms  (bound {metrics['bound_gpu_pct']}%)")
    print(f"     Bottleneck   : {metrics['bottleneck']}")
    print(f"     Hitches      : {metrics['hitch_count']}  ({metrics['hitch_pct']}%)  worst -> {metrics['worst_hitch']}")
    print(f"     Saved to     : {output.resolve()}")


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description='Parse UE FPS Chart dumps and append rows to a master CSV.',
    )
    parser.add_argument('folder',
        help='Folder containing the FPS chart dump file(s)')
    parser.add_argument('--scenario', '-s', default='',
        help='Label for this test run e.g. "2A - All Enabled"')
    parser.add_argument('--output', '-o', default='fps_benchmark_results.csv',
        help='Master CSV file to append results to (default: fps_benchmark_results.csv)')
    parser.add_argument('--all', '-a', action='store_true',
        help='Process ALL files in the folder, not just the latest')
    args = parser.parse_args()

    folder = Path(args.folder)
    if not folder.exists() or not folder.is_dir():
        print(f"ERROR: Folder not found: {folder}")
        sys.exit(1)

    output_csv = Path(args.output)
    files = find_all_chart_files(folder) if args.all else [find_latest_chart_file(folder)]

    print(f"\nFound {len(files)} file(s) to process.")
    current_scenario = args.scenario

    for i, file in enumerate(files):
        print(f"\n[{i+1}/{len(files)}] {file.name}")

        scenario = current_scenario
        if not scenario:
            scenario = input("  Enter scenario name (e.g. '2A - All Enabled'): ").strip()
        if not scenario:
            scenario = file.stem

        try:
            metrics = parse_fps_chart(file)
            append_to_csv(metrics, scenario, output_csv)
            print_summary(metrics, scenario, file.name, output_csv)
            # Reset so next file prompts again
            current_scenario = ''
        except Exception as e:
            print(f"  ERROR: {e}")

    print(f"\nAll done.")


if __name__ == '__main__':
    main()
