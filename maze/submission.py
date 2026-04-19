from typing import Any, Tuple
import random
from collections import deque

NO_TARGET = 127
EXPLORE_STEPS = 130
MIN_SPINS_BEFORE_BAIL = 20
MIN_AVG_PER_SPIN = 40

def SubmissionBot(step, total_steps, pos, last_pos, neighbors, has_slot, slot_coins, data) -> Tuple[int, Any]:
    if data is None:
        data = ((NO_TARGET) | (NO_TARGET << 7), 0)
    p1, p2 = data
    camped = p1 & 0x7F
    bailed = (p1 >> 7) & 0x7F
    spins_here = (p1 >> 14) & 0x3FF
    total_earned = (p1 >> 24) & 0xFFFF
    explored = p2 & 0x3FF

    def pack():
        v1 = ((camped & 0x7F)
              | ((bailed & 0x7F) << 7)
              | ((min(spins_here, 1023) & 0x3FF) << 14)
              | ((min(total_earned, 65535) & 0xFFFF) << 24))
        v2 = min(explored, 1023) & 0x3FF
        return (v1, v2)

    if explored < 1023:
        explored += 1

    if has_slot and camped != NO_TARGET and pos == camped:
        total_earned = min(total_earned + slot_coins, 65535)
        spins_here = min(spins_here + 1, 1023)

    if camped != NO_TARGET and spins_here >= MIN_SPINS_BEFORE_BAIL:
        if total_earned / max(spins_here, 1) < MIN_AVG_PER_SPIN:
            bailed = camped
            camped = NO_TARGET
            spins_here = 0
            total_earned = 0

    if bailed != NO_TARGET and pos != bailed:
        bailed = NO_TARGET

    if explored < EXPLORE_STEPS:
        forward = [n for n in neighbors if n != last_pos] or neighbors
        return (random.choice(forward), pack())

    if has_slot and camped == NO_TARGET and pos != bailed:
        camped = pos
        spins_here = 0
        total_earned = 0

    if has_slot and pos == camped:
        return (-1, pack())

    if has_slot and pos == bailed:
        forward = [n for n in neighbors if n != last_pos] or neighbors
        return (random.choice(forward), pack())

    if has_slot:
        if camped == NO_TARGET:
            camped = pos
            spins_here = 0
            total_earned = 0
        return (-1, pack())

    if camped != NO_TARGET and camped in neighbors:
        return (camped, pack())

    forward = [n for n in neighbors if n != last_pos] or neighbors
    return (random.choice(forward), pack())

def SubmissionGhost(step, total_steps, pos, last_pos, neighbors, has_slot, slot_coins, data) -> Tuple[int, Any]:
    if data is None:
        data = {
            "adj": {},
            "seen": set(),
            "maxv": {},
            "stock": {},
            "hot": {},
            "path": [],
            "target": -1,
        }

    adj, seen, maxv, stock, hot = (data["adj"], data["seen"], data["maxv"],
                                    data["stock"], data["hot"])

    if pos not in adj:
        adj[pos] = set(neighbors)
    else:
        adj[pos].update(neighbors)
    for n in neighbors:
        if n not in adj:
            adj[n] = set()
        adj[n].add(pos)

    if has_slot:
        seen.add(pos)
        prev = stock.get(pos, None)
        if prev is not None and slot_coins < prev:
            hot[pos] = hot.get(pos, 0) + (prev - slot_coins)
        stock[pos] = slot_coins
        if pos not in maxv:
            maxv[pos] = max(1, slot_coins)
        elif slot_coins > maxv[pos]:
            maxv[pos] = slot_coins

    if has_slot and slot_coins < 45:
        return (-1, data)

    path, target = data["path"], data["target"]

    if target != -1 and stock.get(target, 0) >= 45:
        target = -1
        path = []

    if target == -1 or not path:
        candidates = []
        for n in seen:
            if stock.get(n, 0) >= 45:
                continue
            score = maxv.get(n, 1) + 10 * hot.get(n, 0)
            candidates.append((score, n))
        if candidates:
            candidates.sort(reverse=True)
            target = candidates[0][1]
            path = _bfs_path(adj, pos, target)
            if not path:
                target = -1

        if target == -1:
            data["target"] = -1
            data["path"] = []
            unknown = [n for n in neighbors if n not in adj or not adj[n]]
            if unknown:
                return (random.choice(unknown), data)
            forward = [n for n in neighbors if n != last_pos] or neighbors
            return (random.choice(forward), data)

    if path and path[0] == pos and len(path) >= 2:
        nxt = path[1]
        data["path"] = path[1:]
        data["target"] = target
        if nxt in neighbors:
            return (nxt, data)

    data["target"] = -1
    data["path"] = []
    forward = [n for n in neighbors if n != last_pos] or neighbors
    return (random.choice(forward), data)


def _bfs_path(adj, start, goal):
    if start == goal:
        return [start]
    if start not in adj or goal not in adj:
        return []
    prev = {start: None}
    q = deque([start])
    while q:
        u = q.popleft()
        if u == goal:
            path = []
            while u is not None:
                path.append(u)
                u = prev[u]
            path.reverse()
            return path
        for v in adj.get(u, ()):
            if v not in prev:
                prev[v] = u
                q.append(v)
    return []
