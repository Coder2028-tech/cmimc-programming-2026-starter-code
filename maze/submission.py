from typing import Any, Tuple
import random
MAX_ZERO_STREAK = 15
 
def SubmissionBot(step, total_steps, pos, last_pos, neighbors, has_slot, slot_coins, data) -> Tuple[int, Any]:
    if data is None:
        data = (-1, 0)
    best_seen, zero_streak = data
 
    if has_slot and pos == best_seen:
        if slot_coins == 0:
            zero_streak += 1
        else:
            zero_streak = 0
 
    if best_seen != -1 and zero_streak >= MAX_ZERO_STREAK:
        best_seen = -1
        zero_streak = 0
 
    if has_slot and best_seen == -1:
        best_seen = pos
        zero_streak = 0
 
    if has_slot:
        if pos != best_seen:
            best_seen = pos
            zero_streak = 0
        return (-1, (best_seen, zero_streak))
 
    if best_seen != -1 and best_seen in neighbors:
        return (best_seen, (best_seen, zero_streak))
 
    # Wander forward
    forward = [n for n in neighbors if n != last_pos] or neighbors
    return (random.choice(forward), (best_seen, zero_streak))
 
 

def SubmissionGhost(step, total_steps, pos, last_pos, neighbors, has_slot, slot_coins, data) -> Tuple[int, Any]:
    if data is None:
        data = {
            "adj": {},      
            "seen": set(),  
            "maxv": {},     
            "stock": {},    
            "path": [],     
            "target": -1,
        }
 
    adj, seen, maxv, stock = data["adj"], data["seen"], data["maxv"], data["stock"]
 
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
        candidates = [(maxv[n], n) for n in seen if stock.get(n, 0) < 45]
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
    """BFS shortest path in observed graph. Returns [start, ..., goal] or []."""
    if start == goal:
        return [start]
    if start not in adj or goal not in adj:
        return []
    from collections import deque
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
