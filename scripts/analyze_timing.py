#!/usr/bin/env python3
"""Analyze historical encounter timing to find optimal delivery windows."""

import json
import sys
from pathlib import Path
from datetime import datetime
from collections import defaultdict

def analyze_encounters(encounters_dir):
    """Analyze timing patterns from all encounter logs."""
    hour_responses = defaultdict(list)  # hour -> [response_times]
    weekday_responses = defaultdict(list)  # weekday -> [response_times]
    hour_completion_rate = defaultdict(lambda: {'completed': 0, 'total': 0})

    total_encounters = 0
    total_completed = 0
    total_expired = 0

    for jsonl_file in Path(encounters_dir).glob('user_*.jsonl'):
        with open(jsonl_file) as f:
            for line in f:
                encounter = json.loads(line)
                total_encounters += 1

                timestamp = datetime.fromisoformat(encounter['timestamp'])
                hour = timestamp.hour
                weekday = timestamp.weekday()  # 0=Monday, 6=Sunday

                completed = encounter.get('completed', False)
                expired = encounter.get('expired', False)

                if completed:
                    total_completed += 1
                    response_time = encounter.get('response_time', 0)
                    hour_responses[hour].append(response_time)
                    weekday_responses[weekday].append(response_time)
                    hour_completion_rate[hour]['completed'] += 1

                if expired:
                    total_expired += 1

                hour_completion_rate[hour]['total'] += 1

    print("=" * 60)
    print("MANTRA TIMING ANALYSIS")
    print("=" * 60)
    print(f"\nTotal encounters: {total_encounters}")
    print(f"Completed: {total_completed} ({100*total_completed/total_encounters:.1f}%)")
    print(f"Expired: {total_expired} ({100*total_expired/total_encounters:.1f}%)")

    print("\n" + "=" * 60)
    print("HOUR OF DAY ANALYSIS")
    print("=" * 60)
    print(f"{'Hour':<6} {'Encounters':<12} {'Completed':<12} {'Rate':<8} {'Avg Response'}")
    print("-" * 60)

    for hour in sorted(hour_completion_rate.keys()):
        stats = hour_completion_rate[hour]
        total = stats['total']
        completed = stats['completed']
        rate = 100 * completed / total if total > 0 else 0

        avg_response = 0
        if hour in hour_responses and hour_responses[hour]:
            avg_response = sum(hour_responses[hour]) / len(hour_responses[hour])

        print(f"{hour:02d}:00  {total:<12} {completed:<12} {rate:>6.1f}%  {avg_response:>6.0f}s")

    print("\n" + "=" * 60)
    print("DAY OF WEEK ANALYSIS")
    print("=" * 60)
    days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']

    weekday_totals = defaultdict(int)
    weekday_completed = defaultdict(int)

    for jsonl_file in Path(encounters_dir).glob('user_*.jsonl'):
        with open(jsonl_file) as f:
            for line in f:
                encounter = json.loads(line)
                timestamp = datetime.fromisoformat(encounter['timestamp'])
                weekday = timestamp.weekday()
                weekday_totals[weekday] += 1
                if encounter.get('completed', False):
                    weekday_completed[weekday] += 1

    for weekday in range(7):
        total = weekday_totals[weekday]
        completed = weekday_completed[weekday]
        rate = 100 * completed / total if total > 0 else 0

        avg_response = 0
        if weekday in weekday_responses and weekday_responses[weekday]:
            avg_response = sum(weekday_responses[weekday]) / len(weekday_responses[weekday])

        print(f"{days[weekday]:<12} {total:<12} {completed:<12} {rate:>6.1f}%  {avg_response:>6.0f}s")

    # Find peak hours (top 5)
    print("\n" + "=" * 60)
    print("TOP 5 PEAK HOURS (by completion rate)")
    print("=" * 60)

    hour_rates = [(h, 100 * stats['completed'] / stats['total'])
                  for h, stats in hour_completion_rate.items() if stats['total'] >= 3]
    hour_rates.sort(key=lambda x: x[1], reverse=True)

    for hour, rate in hour_rates[:5]:
        total = hour_completion_rate[hour]['total']
        completed = hour_completion_rate[hour]['completed']
        print(f"{hour:02d}:00 - {rate:.1f}% ({completed}/{total} encounters)")

if __name__ == '__main__':
    encounters_dir = sys.argv[1] if len(sys.argv) > 1 else '/home/dudebot/conditioner/logs/encounters'
    analyze_encounters(encounters_dir)
