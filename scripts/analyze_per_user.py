#!/usr/bin/env python3
"""Per-user timing analysis to find individual patterns."""

import json
import sys
from pathlib import Path
from datetime import datetime, timedelta
from collections import defaultdict

def analyze_user_patterns(encounters_file):
    """Analyze a single user's encounter patterns."""
    encounters = []
    with open(encounters_file) as f:
        for line in f:
            encounters.append(json.loads(line))

    if len(encounters) < 10:
        return None  # Need minimum data

    # Sort by timestamp
    encounters.sort(key=lambda e: e['timestamp'])

    # Analyze inter-encounter spacing
    completed = [e for e in encounters if e.get('completed', False)]

    if len(completed) < 5:
        return None

    # Calculate time between consecutive completions
    intervals = []
    for i in range(len(completed) - 1):
        t1 = datetime.fromisoformat(completed[i]['timestamp'])
        t2 = datetime.fromisoformat(completed[i+1]['timestamp'])
        hours_between = (t2 - t1).total_seconds() / 3600
        intervals.append(hours_between)

    # Hour of day distribution (user's local pattern)
    hour_stats = defaultdict(lambda: {'completed': 0, 'total': 0, 'avg_response': []})

    for enc in encounters:
        dt = datetime.fromisoformat(enc['timestamp'])
        hour = dt.hour
        hour_stats[hour]['total'] += 1

        if enc.get('completed', False):
            hour_stats[hour]['completed'] += 1
            if 'response_time' in enc:
                hour_stats[hour]['avg_response'].append(enc['response_time'])

    # Find user's active hours (>60% completion rate, min 3 samples)
    active_hours = []
    for hour, stats in hour_stats.items():
        if stats['total'] >= 3:
            rate = stats['completed'] / stats['total']
            if rate >= 0.6:
                avg_resp = sum(stats['avg_response']) / len(stats['avg_response']) if stats['avg_response'] else 999
                active_hours.append({
                    'hour': hour,
                    'rate': rate,
                    'count': stats['total'],
                    'avg_response': avg_resp
                })

    active_hours.sort(key=lambda x: x['rate'], reverse=True)

    # Analyze day of week
    weekday_stats = defaultdict(lambda: {'completed': 0, 'total': 0})
    for enc in encounters:
        dt = datetime.fromisoformat(enc['timestamp'])
        weekday = dt.weekday()
        weekday_stats[weekday]['total'] += 1
        if enc.get('completed', False):
            weekday_stats[weekday]['completed'] += 1

    # Calculate average response time for completed
    response_times = [e['response_time'] for e in completed if 'response_time' in e]

    return {
        'total_encounters': len(encounters),
        'completed': len(completed),
        'completion_rate': len(completed) / len(encounters),
        'avg_interval_hours': sum(intervals) / len(intervals) if intervals else 0,
        'median_interval_hours': sorted(intervals)[len(intervals)//2] if intervals else 0,
        'active_hours': active_hours[:5],  # Top 5
        'avg_response_time': sum(response_times) / len(response_times) if response_times else 0,
        'fast_responses': len([r for r in response_times if r < 60]),
        'weekday_pattern': {day: weekday_stats[day] for day in range(7)}
    }

def analyze_all_users(encounters_dir):
    """Analyze all users and aggregate insights."""
    print("=" * 80)
    print("PER-USER PATTERN ANALYSIS")
    print("=" * 80)

    user_patterns = []

    for jsonl_file in sorted(Path(encounters_dir).glob('user_*.jsonl')):
        user_id = jsonl_file.stem.replace('user_', '')
        pattern = analyze_user_patterns(jsonl_file)

        if pattern:
            user_patterns.append((user_id, pattern))

    print(f"\nAnalyzed {len(user_patterns)} users with sufficient data\n")

    # Show per-user insights
    for user_id, pattern in user_patterns:
        print(f"\n{'='*80}")
        print(f"User {user_id}")
        print(f"{'='*80}")
        print(f"Total encounters: {pattern['total_encounters']}")
        print(f"Completion rate: {pattern['completion_rate']*100:.1f}%")
        print(f"Avg interval between completions: {pattern['avg_interval_hours']:.1f}h")
        print(f"Median interval: {pattern['median_interval_hours']:.1f}h")
        print(f"Avg response time: {pattern['avg_response_time']:.0f}s")
        print(f"Fast responses (<60s): {pattern['fast_responses']}")

        print(f"\nTop active hours (completion rate):")
        for ah in pattern['active_hours']:
            print(f"  {ah['hour']:02d}:00 - {ah['rate']*100:.1f}% "
                  f"({ah['count']} encounters, {ah['avg_response']:.0f}s avg response)")

        print(f"\nDay of week pattern:")
        days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
        for day in range(7):
            stats = pattern['weekday_pattern'][day]
            if stats['total'] > 0:
                rate = 100 * stats['completed'] / stats['total']
                print(f"  {days[day]}: {rate:.1f}% ({stats['completed']}/{stats['total']})")

    # Aggregate insights
    print(f"\n{'='*80}")
    print("AGGREGATE INSIGHTS")
    print(f"{'='*80}")

    # Average intervals (tells us natural pacing)
    avg_intervals = [p['avg_interval_hours'] for _, p in user_patterns]
    print(f"\nAvg hours between completions (across users):")
    print(f"  Mean: {sum(avg_intervals)/len(avg_intervals):.1f}h")
    print(f"  Min: {min(avg_intervals):.1f}h")
    print(f"  Max: {max(avg_intervals):.1f}h")

    # Hour spread analysis
    all_active_hours = []
    for _, p in user_patterns:
        all_active_hours.extend([ah['hour'] for ah in p['active_hours']])

    if all_active_hours:
        hour_freq = defaultdict(int)
        for h in all_active_hours:
            hour_freq[h] += 1

        print(f"\nMost common active hours (across all users):")
        for hour, count in sorted(hour_freq.items(), key=lambda x: x[1], reverse=True)[:10]:
            print(f"  {hour:02d}:00 - {count} users")

    # Response time distribution
    all_response_times = []
    for _, p in user_patterns:
        all_response_times.append(p['avg_response_time'])

    print(f"\nResponse time distribution:")
    print(f"  Mean: {sum(all_response_times)/len(all_response_times):.0f}s")
    print(f"  Fast responders (<200s avg): {len([r for r in all_response_times if r < 200])}")
    print(f"  Slow responders (>400s avg): {len([r for r in all_response_times if r > 400])}")

    # Completion rate distribution
    completion_rates = [p['completion_rate'] for _, p in user_patterns]
    print(f"\nCompletion rate distribution:")
    print(f"  Mean: {100*sum(completion_rates)/len(completion_rates):.1f}%")
    print(f"  High performers (>85%): {len([r for r in completion_rates if r > 0.85])}")
    print(f"  Low performers (<60%): {len([r for r in completion_rates if r < 0.6])}")

if __name__ == '__main__':
    encounters_dir = sys.argv[1] if len(sys.argv) > 1 else '/home/dudebot/conditioner/logs/encounters'
    analyze_all_users(encounters_dir)
