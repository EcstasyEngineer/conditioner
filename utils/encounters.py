"""
Encounter logging and streak management utilities.

Handles JSONL-based encounter storage and streak calculation logic
that can be shared across multiple cogs.
"""

import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Optional


def log_encounter(user_id: int, encounter: Dict):
    """Log encounter to JSONL file for performance."""
    encounters_dir = Path('logs/encounters')
    encounters_dir.mkdir(parents=True, exist_ok=True)
    
    encounters_file = encounters_dir / f'user_{user_id}.jsonl'
    with open(encounters_file, 'a') as f:
        f.write(json.dumps(encounter) + '\n')


def load_encounters(user_id: int) -> List[Dict]:
    """Load all encounters from JSONL file."""
    encounters_file = Path('logs/encounters') / f'user_{user_id}.jsonl'
    
    if not encounters_file.exists():
        return []
    
    encounters = []
    try:
        with open(encounters_file, 'r') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if line:
                    # Handle potential multiple JSON objects on one line
                    if '}{' in line:
                        # Split and process each JSON object separately
                        parts = line.split('}{')
                        for i, part in enumerate(parts):
                            if i == 0:
                                part = part + '}'
                            elif i == len(parts) - 1:
                                part = '{' + part
                            else:
                                part = '{' + part + '}'
                            
                            try:
                                encounters.append(json.loads(part))
                            except json.JSONDecodeError as e:
                                print(f"Error parsing JSON fragment on line {line_num} for user {user_id}: {e}")
                    else:
                        try:
                            encounters.append(json.loads(line))
                        except json.JSONDecodeError as e:
                            print(f"Error parsing JSON on line {line_num} for user {user_id}: {e}")
                            # Continue processing other lines instead of failing completely
    except IOError as e:
        print(f"Error reading encounters file for user {user_id}: {e}")
        return []
    
    return encounters


def load_recent_encounters(user_id: int, limit: int = 7) -> List[Dict]:
    """Load the most recent N encounters for a user."""
    encounters_file = Path('logs/encounters') / f'user_{user_id}.jsonl'
    
    if not encounters_file.exists():
        return []
    
    encounters = []
    try:
        with open(encounters_file, 'r') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if line:
                    # Handle potential multiple JSON objects on one line
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
                                encounters.append(json.loads(part))
                            except json.JSONDecodeError as e:
                                print(f"Error parsing JSON fragment on line {line_num} for user {user_id}: {e}")
                    else:
                        try:
                            encounters.append(json.loads(line))
                        except json.JSONDecodeError as e:
                            print(f"Error parsing JSON on line {line_num} for user {user_id}: {e}")
                            # Continue processing other lines instead of failing completely
    except IOError as e:
        print(f"Error reading encounters file for user {user_id}: {e}")
        return []
    
    # Return the last N encounters
    return encounters[-limit:] if encounters else []


def calculate_user_streak_from_history(user_id: int) -> Optional[Dict]:
    """
    Calculate user's current streak from encounter history.
    
    Returns:
        Optional[Dict]: {"count": int, "last_response": datetime} or None if no streak
    """
    encounters = load_encounters(user_id)
    if not encounters:
        return None
        
    # Sort encounters by timestamp (most recent first)
    sorted_encounters = sorted(
        encounters,
        key=lambda x: x["timestamp"],
        reverse=True
    )
    
    # Count consecutive successes from most recent until first failure
    streak_count = 0
    last_successful_timestamp = None
    
    for encounter in sorted_encounters:
        if encounter.get("completed", False):
            streak_count += 1
            if last_successful_timestamp is None:  # First successful encounter (most recent)
                last_successful_timestamp = datetime.fromisoformat(encounter["timestamp"])
        else:
            # Hit a failure - stop counting
            break
    
    # Return streak if user has any consecutive successes
    if streak_count > 0 and last_successful_timestamp:
        return {
            "count": streak_count,
            "last_response": last_successful_timestamp
        }
    
    return None


def get_user_encounter_stats(user_id: int) -> Dict:
    """
    Get comprehensive encounter statistics for a user.
    
    Returns:
        Dict: Statistics including total, completed, success rate, etc.
    """
    encounters = load_encounters(user_id)
    
    if not encounters:
        return {
            "total_encounters": 0,
            "completed_encounters": 0,
            "success_rate": 0.0,
            "avg_response_time": 0.0,
            "public_responses": 0,
            "recent_encounters": []
        }
    
    total = len(encounters)
    completed = sum(1 for e in encounters if e.get("completed", False))
    success_rate = (completed / total * 100) if total > 0 else 0.0
    
    # Calculate average response time for completed encounters
    response_times = [e["response_time"] for e in encounters 
                     if e.get("completed", False) and "response_time" in e]
    avg_response = sum(response_times) / len(response_times) if response_times else 0.0
    
    # Count public responses
    public_responses = sum(1 for e in encounters if e.get("was_public", False))
    
    # Get recent encounters (last 5)
    recent = encounters[-5:] if encounters else []
    
    return {
        "total_encounters": total,
        "completed_encounters": completed,
        "success_rate": success_rate,
        "avg_response_time": avg_response,
        "public_responses": public_responses,
        "recent_encounters": recent
    }