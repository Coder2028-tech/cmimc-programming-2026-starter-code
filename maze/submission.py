from collections import deque
from typing import Any, Tuple


def SubmissionBot(
    step, total_steps, pos, last_pos, neighbors, has_slot, slot_coins, data
) -> Tuple[int, Any]:
    no_target = 127
    visit_bits = 100
    recent_len = 8
    visit_mask = (1 << visit_bits) - 1
    camp_shift = visit_bits
    banned_shift = camp_shift + 7
    spins_shift = banned_shift + 7
    gain_shift = spins_shift + 8
    explore_shift = gain_shift + 14
    recent_shift = explore_shift + 9
    degree_shift = recent_shift + 7 * recent_len
    run_shift = degree_shift + 10
    recent_mask = (1 << (7 * recent_len)) - 1

    def unpack_recent(bits):
        out = []
        for i in range(recent_len):
            out.append((bits >> (7 * i)) & 0x7F)
        return out

    def pack_recent(nodes):
        bits = 0
        for i, node in enumerate(nodes[:recent_len]):
            bits |= (node & 0x7F) << (7 * i)
        return bits

    def pack(visited, camp, banned, spins, total_gain, explored, recent_bits, degree_sum, fresh_run):
        return (
            (visited & visit_mask)
            | ((camp & 0x7F) << camp_shift)
            | ((banned & 0x7F) << banned_shift)
            | ((min(spins, 255) & 0xFF) << spins_shift)
            | ((min(total_gain, (1 << 14) - 1) & ((1 << 14) - 1)) << gain_shift)
            | ((min(explored, (1 << 9) - 1) & ((1 << 9) - 1)) << explore_shift)
            | ((recent_bits & recent_mask) << recent_shift)
            | ((min(degree_sum, 1023) & 0x3FF) << degree_shift)
            | ((min(fresh_run, 63) & 0x3F) << run_shift)
        )

    if data is None:
        visited = 0
        camp = no_target
        banned = no_target
        spins = 0
        total_gain = 0
        explored = 0
        degree_sum = 0
        recent = [no_target] * recent_len
        fresh_run = 0
    else:
        state = int(data)
        visited = state & visit_mask
        camp = (state >> camp_shift) & 0x7F
        banned = (state >> banned_shift) & 0x7F
        spins = (state >> spins_shift) & 0xFF
        total_gain = (state >> gain_shift) & ((1 << 14) - 1)
        explored = (state >> explore_shift) & ((1 << 9) - 1)
        recent = unpack_recent((state >> recent_shift) & recent_mask)
        degree_sum = (state >> degree_shift) & 0x3FF
        fresh_run = (state >> run_shift) & 0x3F

    first_visit = ((visited >> pos) & 1) == 0
    visited |= 1 << pos
    explored = min(explored + 1, (1 << 9) - 1)
    remaining = total_steps - step
    avg_x8 = (total_gain * 8) // max(spins, 1) if spins else 0
    recent = [pos] + [node for node in recent if node != pos][: recent_len - 1]
    recent_set = set(recent)
    if first_visit:
        degree_sum = min(degree_sum + len(neighbors), 1023)
        if step > 1:
            fresh_run = min(fresh_run + 1, 63)
    else:
        fresh_run = max(fresh_run - 1, 0)
    visited_count = visited.bit_count()
    avg_degree_x10 = (degree_sum * 10) // max(visited_count, 1)
    recent_seed = 0
    for i, node in enumerate(recent):
        recent_seed += (i + 3) * (0 if node == no_target else node + 1)

    def pick(options, salt):
        ordered = sorted(options)
        seed = (
            step * 17
            + pos * 31
            + visited_count * 13
            + recent_seed * 7
            + explored * 5
            + salt
        )
        return ordered[seed % len(ordered)]

    def recency_age(node):
        for idx, seen_node in enumerate(recent):
            if seen_node == node:
                return idx
        return recent_len + 1

    def pick_oldest(options, salt):
        best_age = max(recency_age(node) for node in options)
        oldest = [node for node in options if recency_age(node) == best_age]
        return pick(oldest, salt)

    if has_slot and camp != no_target and pos == camp:
        total_gain = min(total_gain + max(slot_coins, 0), (1 << 14) - 1)
        spins = min(spins + 1, 255)
        avg_x8 = (total_gain * 8) // max(spins, 1)

    if camp != no_target and pos == camp and spins >= 10:
        bail_bar = 30 if remaining > 500 else 24 if remaining > 220 else 16
        if avg_degree_x10 >= 55:
            if spins >= 48 and avg_x8 < 88 and slot_coins < 18:
                bail_bar = max(bail_bar, 200)
            elif spins >= 96 and avg_x8 < 112 and slot_coins < 24:
                bail_bar = max(bail_bar, 200)
        if avg_x8 < bail_bar and slot_coins < 8:
            banned = camp
            camp = no_target
            spins = 0
            total_gain = 0
            avg_x8 = 0

    if banned != no_target and pos != banned:
        banned = no_target

    if avg_degree_x10 >= 55:
        early_adopt = 22
        mid_adopt = 16
        explore_node_cap = 36
        explore_step_cap = 180
        run_target = 2
    elif avg_degree_x10 >= 38:
        early_adopt = 18
        mid_adopt = 12
        explore_node_cap = 32
        explore_step_cap = 180
        run_target = 4
    elif avg_degree_x10 >= 28:
        early_adopt = 24
        mid_adopt = 18
        explore_node_cap = 42
        explore_step_cap = 230
        run_target = 7
    else:
        early_adopt = 22
        mid_adopt = 14
        explore_node_cap = 34
        explore_step_cap = 180
        run_target = 5

    if step < 120:
        adopt_threshold = early_adopt
    elif step < 400:
        adopt_threshold = mid_adopt
    elif remaining > 200:
        adopt_threshold = 8
    else:
        adopt_threshold = 4

    if slot_coins >= 32:
        adopt_threshold = 0

    still_exploring = (
        visited_count < explore_node_cap
        and step < explore_step_cap
        and (slot_coins < adopt_threshold or fresh_run < run_target)
    )

    if has_slot and camp == no_target and pos != banned and (not still_exploring):
        camp = pos
        spins = 0
        total_gain = 0
        avg_x8 = 0

    if has_slot and pos != banned and camp != no_target and pos != camp:
        switch_now = False
        if slot_coins >= 36:
            switch_now = True
        elif slot_coins >= 24 and avg_x8 < 40:
            switch_now = True
        elif remaining < 250 and slot_coins >= 16 and avg_x8 < 56:
            switch_now = True
        elif avg_degree_x10 >= 55 and slot_coins >= 18 and avg_x8 < 80:
            switch_now = True
        if switch_now:
            camp = pos
            spins = 0
            total_gain = 0
            avg_x8 = 0

    packed = pack(
        visited,
        camp,
        banned,
        spins,
        total_gain,
        explored,
        pack_recent(recent),
        degree_sum,
        fresh_run,
    )

    if has_slot and pos == camp:
        return (-1, packed)

    if has_slot and pos == banned:
        forward = [n for n in neighbors if n != last_pos and n not in recent_set] or [
            n for n in neighbors if n != last_pos
        ] or neighbors
        return (pick(forward, 5), packed)

    if camp != no_target and camp in neighbors:
        return (camp, packed)

    unseen_forward = [
        n
        for n in neighbors
        if not ((visited >> n) & 1) and n != last_pos and n not in recent_set
    ]
    if unseen_forward:
        return (pick(unseen_forward, 1), packed)

    unseen = [n for n in neighbors if not ((visited >> n) & 1) and n not in recent_set]
    if unseen:
        return (pick(unseen, 2), packed)

    forward = [n for n in neighbors if n != last_pos and n not in recent_set]
    if not forward:
        forward = [n for n in neighbors if n not in recent_set]
    if forward:
        return (pick(forward, 3), packed)

    revisit = [n for n in neighbors if n != last_pos]
    if revisit:
        return (pick_oldest(revisit, 4), packed)

    return (pick_oldest(neighbors, 5), packed)


def SubmissionGhost(
    step, total_steps, pos, last_pos, neighbors, has_slot, slot_coins, data
) -> Tuple[int, Any]:
    history_limit = 16

    def pick(options, salt):
        ordered = sorted(options)
        return ordered[(step * 19 + pos * 23 + salt) % len(ordered)]

    def bfs(graph, start):
        dist = {start: 0}
        parent = {start: -1}
        queue = deque([start])
        while queue:
            node = queue.popleft()
            for nxt in graph.get(node, ()):
                if nxt in dist:
                    continue
                dist[nxt] = dist[node] + 1
                parent[nxt] = node
                queue.append(nxt)
        return dist, parent

    def first_step(parent, target):
        if target not in parent:
            return -1
        node = target
        while parent[node] != -1 and parent[parent[node]] != -1:
            node = parent[node]
        return node

    if data is None:
        data = {
            "graph": {},
            "seen": set(),
            "slots": {},
            "recent": [],
            "last_pos": -1,
            "last_action": 0,
            "last_slot_coins": 0,
            "spin_streak": 0,
        }

    graph = data["graph"]
    seen = data["seen"]
    slots = data["slots"]
    recent = data["recent"]

    graph.setdefault(pos, set()).update(neighbors)
    seen.add(pos)
    for nxt in neighbors:
        graph.setdefault(nxt, set()).add(pos)

    recent.append(pos)
    if len(recent) > history_limit:
        recent.pop(0)

    if data["last_action"] == -1 and data["last_pos"] == pos:
        spin_streak = min(data.get("spin_streak", 0) + 1, 255)
    else:
        spin_streak = 0

    info = None
    if has_slot:
        info = slots.setdefault(
            pos,
            {
                "gain_total": 0,
                "gain_count": 0,
                "best_gain": 0,
                "stash": 0,
                "drained": 0,
                "visits": 0,
            },
        )
        previous_stash = info["stash"]
        info["visits"] += 1
        if previous_stash > slot_coins:
            info["drained"] += previous_stash - slot_coins
        if data["last_action"] == -1 and data["last_pos"] == pos and slot_coins >= data["last_slot_coins"]:
            gain = slot_coins - data["last_slot_coins"]
            info["gain_total"] += gain
            info["gain_count"] += 1
            if gain > info["best_gain"]:
                info["best_gain"] = gain
        info["stash"] = slot_coins

    def finish(action):
        data["last_pos"] = pos
        data["last_action"] = action
        data["last_slot_coins"] = slot_coins
        data["spin_streak"] = spin_streak if action == -1 and has_slot else 0
        return (action, data)

    current_dist, parents = bfs(graph, pos)
    start_dist, _ = bfs(graph, 0)

    direct_unseen = [n for n in neighbors if n not in seen and n != last_pos]
    if not direct_unseen:
        direct_unseen = [n for n in neighbors if n not in seen]

    frontier_nodes = []
    for node, node_neighbors in graph.items():
        unseen_count = sum(1 for nxt in node_neighbors if nxt not in seen)
        if unseen_count:
            frontier_nodes.append((node, unseen_count))

    frontier_exists = bool(frontier_nodes)
    explore_phase = step < int(total_steps * 0.5)

    if has_slot:
        avg_gain = (
            info["gain_total"] / info["gain_count"] if info["gain_count"] else 0.0
        )
        best_gain = info["best_gain"]
        depth = start_dist.get(pos, 0)
        sample_target = 1
        if depth >= 8:
            sample_target = 4
        elif depth >= 5:
            sample_target = 3
        elif depth >= 3:
            sample_target = 2

        if explore_phase and frontier_exists and info["gain_count"] < sample_target:
            return finish(-1)

        fill_target = 6 + min(10, 2 * depth)

        if avg_gain >= 8 or best_gain >= 14:
            fill_target = 50
        elif avg_gain >= 4 or best_gain >= 8:
            fill_target = min(42, fill_target + 18)
        elif avg_gain >= 2 or best_gain >= 5:
            fill_target = min(28, fill_target + 8)
        else:
            fill_target = min(fill_target, 10)

        if explore_phase and frontier_exists and avg_gain < 3 and best_gain < 6:
            fill_target = min(fill_target, 6)

        if step > total_steps - 220 and (avg_gain >= 2 or best_gain >= 6 or info["drained"] >= 12):
            fill_target = 50

        spin_cap = 7 if frontier_exists and explore_phase else 12
        if slot_coins < fill_target and spin_streak < spin_cap:
            return finish(-1)

    if direct_unseen:
        return finish(pick(direct_unseen, 1))

    best_frontier = -1
    frontier_score = None
    for node, unseen_count in frontier_nodes:
        if node not in current_dist:
            continue
        score = 5 * start_dist.get(node, 0) + 4 * unseen_count - 2 * current_dist[node]
        if node in recent:
            score -= 4
        if frontier_score is None or score > frontier_score:
            frontier_score = score
            best_frontier = node

    if best_frontier != -1 and best_frontier != pos:
        nxt = first_step(parents, best_frontier)
        if nxt != -1:
            return finish(nxt)

    best_slot = -1
    best_slot_score = None
    for node, slot_info in slots.items():
        if node not in current_dist:
            continue
        avg_gain = (
            slot_info["gain_total"] / slot_info["gain_count"]
            if slot_info["gain_count"]
            else 0.0
        )
        best_gain = slot_info["best_gain"]
        depth = start_dist.get(node, 0)
        stash = slot_info["stash"]
        refill_need = 50 - stash
        score = (
            7 * avg_gain
            + 2 * best_gain
            + 1.5 * depth
            + min(refill_need, 24) / 2
            + min(slot_info["drained"], 24) / 3
            - 1.8 * current_dist[node]
        )
        if step < int(total_steps * 0.35) and depth < 4 and avg_gain < 3 and best_gain < 6:
            score -= 8
        if node in recent:
            score -= 3
        if best_slot_score is None or score > best_slot_score:
            best_slot_score = score
            best_slot = node

    if best_slot != -1 and best_slot != pos:
        nxt = first_step(parents, best_slot)
        if nxt != -1:
            return finish(nxt)

    forward = [n for n in neighbors if n != last_pos and n not in recent[-5:]]
    if not forward:
        forward = [n for n in neighbors if n != last_pos] or neighbors
    return finish(pick(forward, 9))
