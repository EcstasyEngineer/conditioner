#!/usr/bin/env python3
"""
Analyze user encounter patterns from JSONL files to understand engagement metrics.

This script processes all user encounter logs to calculate:
- Response time distributions
- Streak patterns
- Theme-specific behaviors
- Power user identification
- Candidates for advanced features

Usage: python scripts/analyze_encounters.py
"""
import json
import glob
from pathlib import Path
from datetime import datetime
from collections import defaultdict
import statistics

def analyze_encounters():
    """Analyze all encounter data and generate statistics."""
    # Load all encounter data
    all_encounters = []
    user_stats = defaultdict(lambda: {
        'total': 0,
        'completed': 0,
        'response_times': [],
        'streaks': [],
        'max_streak': 0,
        'current_streak': 0,
        'themes': defaultdict(int),
        'difficulties': defaultdict(int),
        'quick_responses': 0,  # Under 15 seconds
        'fast_responses': 0,   # Under 30 seconds
        'themes_by_speed': defaultdict(list)
    })

    # Process all JSONL files
    for jsonl_file in glob.glob('logs/encounters/user_*.jsonl'):
        user_id = Path(jsonl_file).stem.replace('user_', '')
        
        with open(jsonl_file, 'r') as f:
            user_encounters = []
            for line in f:
                line = line.strip()
                if not line:
                    continue
                
                # Handle malformed lines with multiple JSON objects
                if '}{' in line:
                    parts = line.split('}{')
                    for i, part in enumerate(parts):
                        if i == 0:
                            part = part + '}'
                        elif i == len(parts) - 1:
                            part = '{' + part
                        else:
                            part = '{' + part + '}'
                        try:
                            encounter = json.loads(part)
                            user_encounters.append(encounter)
                        except:
                            pass
                else:
                    try:
                        encounter = json.loads(line)
                        user_encounters.append(encounter)
                    except:
                        pass
            
            # Calculate streaks and stats
            current_streak = 0
            streaks = []
            
            for enc in sorted(user_encounters, key=lambda x: x.get('timestamp', '')):
                user_stats[user_id]['total'] += 1
                
                if enc.get('completed', False):
                    user_stats[user_id]['completed'] += 1
                    current_streak += 1
                    
                    # Response time analysis
                    response_time = enc.get('response_time', 0)
                    if response_time > 0:
                        user_stats[user_id]['response_times'].append(response_time)
                        theme = enc.get('theme', 'unknown')
                        user_stats[user_id]['themes_by_speed'][theme].append(response_time)
                        
                        if response_time < 15:
                            user_stats[user_id]['quick_responses'] += 1
                        elif response_time < 30:
                            user_stats[user_id]['fast_responses'] += 1
                    
                    # Track themes and difficulties
                    user_stats[user_id]['themes'][enc.get('theme', 'unknown')] += 1
                    user_stats[user_id]['difficulties'][enc.get('difficulty', 'unknown')] += 1
                else:
                    # Streak broken
                    if current_streak > 0:
                        streaks.append(current_streak)
                        user_stats[user_id]['max_streak'] = max(user_stats[user_id]['max_streak'], current_streak)
                    current_streak = 0
            
            # Save final streak
            if current_streak > 0:
                streaks.append(current_streak)
                user_stats[user_id]['max_streak'] = max(user_stats[user_id]['max_streak'], current_streak)
                user_stats[user_id]['current_streak'] = current_streak
            
            user_stats[user_id]['streaks'] = streaks
            all_encounters.extend(user_encounters)

    return all_encounters, user_stats


def print_statistics(all_encounters, user_stats):
    """Print formatted statistics from the analysis."""
    # Global statistics
    print("=== GLOBAL MANTRA STATISTICS ===\n")
    print(f"Total Users: {len(user_stats)}")
    print(f"Total Encounters: {len(all_encounters)}")
    completed_count = sum(1 for e in all_encounters if e.get('completed', False))
    print(f"Completed: {completed_count}")
    if all_encounters:
        print(f"Success Rate: {completed_count / len(all_encounters) * 100:.1f}%\n")

    # Response time analysis
    all_response_times = []
    for user_id, stats in user_stats.items():
        all_response_times.extend(stats['response_times'])

    if all_response_times:
        print("=== RESPONSE TIME ANALYSIS ===")
        print(f"Mean: {statistics.mean(all_response_times):.1f}s")
        print(f"Median: {statistics.median(all_response_times):.1f}s")
        try:
            print(f"Mode: {statistics.mode(all_response_times)}s")
        except statistics.StatisticsError:
            print(f"Mode: No unique mode")
        print(f"Min: {min(all_response_times)}s")
        print(f"Max: {max(all_response_times)}s")
        if len(all_response_times) > 1:
            print(f"Std Dev: {statistics.stdev(all_response_times):.1f}s")
        
        # Percentiles
        sorted_times = sorted(all_response_times)
        p25 = sorted_times[len(sorted_times)//4] if len(sorted_times) >= 4 else sorted_times[0]
        p75 = sorted_times[3*len(sorted_times)//4] if len(sorted_times) >= 4 else sorted_times[-1]
        p90 = sorted_times[9*len(sorted_times)//10] if len(sorted_times) >= 10 else sorted_times[-1]
        p95 = sorted_times[19*len(sorted_times)//20] if len(sorted_times) >= 20 else sorted_times[-1]
        
        print(f"\nPercentiles:")
        print(f"25th: {p25}s")
        print(f"50th: {statistics.median(all_response_times):.0f}s")
        print(f"75th: {p75}s")
        print(f"90th: {p90}s")
        print(f"95th: {p95}s")
        
        # Speed categories
        ultra_fast = sum(1 for t in all_response_times if t <= 15)
        fast = sum(1 for t in all_response_times if 15 < t <= 30)
        normal = sum(1 for t in all_response_times if 30 < t <= 60)
        slow = sum(1 for t in all_response_times if 60 < t <= 120)
        very_slow = sum(1 for t in all_response_times if t > 120)
        
        print(f"\nSpeed Distribution:")
        print(f"Ultra Fast (≤15s): {ultra_fast} ({ultra_fast/len(all_response_times)*100:.1f}%)")
        print(f"Fast (16-30s): {fast} ({fast/len(all_response_times)*100:.1f}%)")
        print(f"Normal (31-60s): {normal} ({normal/len(all_response_times)*100:.1f}%)")
        print(f"Slow (61-120s): {slow} ({slow/len(all_response_times)*100:.1f}%)")
        print(f"Very Slow (>120s): {very_slow} ({very_slow/len(all_response_times)*100:.1f}%)")

    # Streak analysis
    all_streaks = []
    for user_id, stats in user_stats.items():
        all_streaks.extend(stats['streaks'])

    if all_streaks:
        print(f"\n=== STREAK ANALYSIS ===")
        print(f"Total Streaks: {len(all_streaks)}")
        print(f"Mean Streak: {statistics.mean(all_streaks):.1f}")
        print(f"Median Streak: {statistics.median(all_streaks):.0f}")
        print(f"Max Streak: {max(all_streaks)}")
        
        print(f"\nStreak Distribution:")
        short_streaks = sum(1 for s in all_streaks if s < 3)
        medium_streaks = sum(1 for s in all_streaks if 3 <= s < 10)
        long_streaks = sum(1 for s in all_streaks if 10 <= s < 20)
        ultra_streaks = sum(1 for s in all_streaks if s >= 20)
        
        print(f"Short (1-2): {short_streaks} ({short_streaks/len(all_streaks)*100:.1f}%)")
        print(f"Medium (3-9): {medium_streaks} ({medium_streaks/len(all_streaks)*100:.1f}%)")
        print(f"Long (10-19): {long_streaks} ({long_streaks/len(all_streaks)*100:.1f}%)")
        print(f"Ultra (20+): {ultra_streaks} ({ultra_streaks/len(all_streaks)*100:.1f}%)")

    # Power user analysis
    print(f"\n=== POWER USER ANALYSIS ===")
    power_users = []
    for user_id, stats in user_stats.items():
        if stats['completed'] >= 10:  # At least 10 completed mantras
            completion_rate = stats['completed'] / stats['total'] * 100 if stats['total'] > 0 else 0
            avg_response = statistics.mean(stats['response_times']) if stats['response_times'] else 0
            
            power_users.append({
                'user_id': user_id,
                'completed': stats['completed'],
                'completion_rate': completion_rate,
                'avg_response': avg_response,
                'max_streak': stats['max_streak'],
                'current_streak': stats['current_streak'],
                'quick_ratio': stats['quick_responses'] / stats['completed'] * 100 if stats['completed'] > 0 else 0
            })

    # Sort by completed count
    power_users.sort(key=lambda x: x['completed'], reverse=True)

    print(f"Power Users (10+ completions): {len(power_users)}")
    if power_users:
        print("\nTop 10 Most Active Users:")
        print(f"{'User ID':>20} | {'Completed':>9} | {'Rate':>6} | {'Avg Time':>8} | {'Max Streak':>10} | {'Quick %':>7}")
        print("-" * 80)
        for user in power_users[:10]:
            print(f"{user['user_id']:>20} | {user['completed']:>9} | {user['completion_rate']:>5.1f}% | {user['avg_response']:>7.1f}s | {user['max_streak']:>10} | {user['quick_ratio']:>6.1f}%")

    # Candidates for delay mode
    print(f"\n=== DELAY MODE CANDIDATES ===")
    print("Users with high engagement who would benefit from forced delays:")
    delay_candidates = []
    for user in power_users:
        if (user['quick_ratio'] > 50 or  # More than 50% ultra-fast responses
            user['avg_response'] < 25 or  # Average under 25 seconds
            user['max_streak'] >= 20):    # Has achieved ultra streaks
            delay_candidates.append(user)

    print(f"\nFound {len(delay_candidates)} candidates:")
    for user in delay_candidates[:10]:
        print(f"User {user['user_id']}: {user['quick_ratio']:.1f}% quick responses, {user['avg_response']:.1f}s avg, streak {user['max_streak']}")

    # Theme-specific response patterns
    print(f"\n=== THEME RESPONSE PATTERNS ===")
    theme_speeds = defaultdict(list)
    for user_id, stats in user_stats.items():
        for theme, times in stats['themes_by_speed'].items():
            theme_speeds[theme].extend(times)

    print("Average response time by theme:")
    theme_list = []
    for theme, times in theme_speeds.items():
        if times and theme != 'timeout':
            theme_list.append((theme, statistics.mean(times), len(times)))
    
    # Sort by average time
    theme_list.sort(key=lambda x: x[1])
    
    for theme, avg_time, count in theme_list:
        print(f"{theme:>20}: {avg_time:>5.1f}s (n={count})")


if __name__ == "__main__":
    all_encounters, user_stats = analyze_encounters()
    print_statistics(all_encounters, user_stats)