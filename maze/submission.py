from typing import Any, List, Tuple
import numpy as np

from typing import Any, List, Tuple
import collections

def SubmissionBot(step, total_steps, pos, last_pos, neighbors, has_slot, slot_coins, data) -> Tuple[int, Any]:
    # Memory limit is 128 bytes. We use a list to track the last few visited nodes.
    if data is None:
        data = []
    
    data.append(pos)
    if len(data) > 15: # Keeping history short to stay under 128 bytes
        data.pop(0)

    if slot_coins > 0:
        return (-1, data)

    targets = [n for n in neighbors if n not in data[-3:]] # Avoid very recent nodes
    if not targets:
        targets = neighbors
        
    best_move = max(targets)
    
    return (best_move, data)

def SubmissionGhost(step, total_steps, pos, last_pos, neighbors, has_slot, slot_coins, data) -> Tuple[int, Any]:
    if data is None:
        data = {"graph": {}, "best_slot_pos": -1, "best_id": -1}

    if pos not in data["graph"]:
        data["graph"][pos] = neighbors

    if has_slot:
        if pos > data["best_id"]:
            data["best_id"] = pos
            data["best_slot_pos"] = pos

    if pos == data["best_slot_pos"] and slot_coins < 48:
        return (-1, data)

    best_move = max(neighbors)
    
    return (best_move, data)
