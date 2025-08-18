"""
Encounter logging and simple stats utilities (moved from utils.encounters).
"""

import json
from pathlib import Path
from typing import List, Dict


def log_encounter(user_id: int, encounter: Dict):
    encounters_dir = Path('logs/encounters')
    encounters_dir.mkdir(parents=True, exist_ok=True)
    encounters_file = encounters_dir / f'user_{user_id}.jsonl'
    with open(encounters_file, 'a') as f:
        f.write(json.dumps(encounter) + '\n')


def load_encounters(user_id: int) -> List[Dict]:
    encounters_file = Path('logs/encounters') / f'user_{user_id}.jsonl'
    if not encounters_file.exists():
        return []
    encounters: List[Dict] = []
    try:
        with open(encounters_file, 'r') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
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
                        except json.JSONDecodeError:
                            pass
                else:
                    try:
                        encounters.append(json.loads(line))
                    except json.JSONDecodeError:
                        pass
    except IOError:
        return []
    return encounters


def load_recent_encounters(user_id: int, limit: int = 7) -> List[Dict]:
    encounters = load_encounters(user_id)
    return encounters[-limit:] if encounters else []


def get_user_encounter_stats(user_id: int) -> Dict:
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
    success_rate = (completed / total * 100) if total else 0.0
    times = [e["response_time"] for e in encounters if e.get("completed", False) and "response_time" in e]
    avg_response = sum(times) / len(times) if times else 0.0
    public_responses = sum(1 for e in encounters if e.get("was_public", False))
    recent = encounters[-5:] if encounters else []
    return {
        "total_encounters": total,
        "completed_encounters": completed,
        "success_rate": success_rate,
        "avg_response_time": avg_response,
        "public_responses": public_responses,
        "recent_encounters": recent
    }
