from typing import Any, Tuple
import random

TOP_K = 3  # number of best slots to track

def SubmissionGhost(step, total_steps, pos, last_pos, neighbors, has_slot, slot_coins, data) -> Tuple[int, Any]:
    if data is None:
        data = {
            "slots": {},        # node -> (total_value, visits)
            "targets": [],      # top K nodes
            "hist": []          # recent positions (anti-loop)
        }

    data["hist"].append(pos)
    if len(data["hist"]) > 10:
        data["hist"].pop(0)

    if has_slot:
        total, count = data["slots"].get(pos, (0, 0))
        data["slots"][pos] = (total + slot_coins, count + 1)

    if has_slot and slot_coins > 0:
        return (-1, data)

    avg_slots = {
        node: total / count
        for node, (total, count) in data["slots"].items()
        if count > 0
    }

    if avg_slots:
        sorted_nodes = sorted(avg_slots, key=lambda n: avg_slots[n], reverse=True)
        data["targets"] = sorted_nodes[:TOP_K]

    if pos in data.get("targets", []):
        if has_slot:
            return (-1, data)

    for t in data.get("targets", []):
        if t in neighbors:
            return (t, data)

    choices = [n for n in neighbors if n != last_pos and n not in data["hist"]]
    if not choices:
        choices = [n for n in neighbors if n != last_pos] or neighbors

    unseen = [n for n in choices if n not in data["slots"]]

    if unseen:
        return (random.choice(unseen), data)

    return (random.choice(choices), data)
