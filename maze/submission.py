from collections import deque
from typing import Any, Tuple


def SubmissionBot(
    step, total_steps, pos, last_pos, neighbors, has_slot, slot_coins, data
) -> Tuple[int, Any]:
    no_target = 127
    visit_bits = 100
    max_stack_len = 32
    visit_mask = (1 << visit_bits) - 1
    camp_shift = visit_bits
    banned_shift = camp_shift + 7
    spins_shift = banned_shift + 7
    gain_shift = spins_shift + 8
    explore_shift = gain_shift + 14
    degree_shift = explore_shift + 9
    camp_depth_shift = degree_shift + 10
    stack_len_shift = camp_depth_shift + 6
    stack_shift = stack_len_shift + 6
    stack_mask = (1 << (7 * max_stack_len)) - 1

    def unpack_stack(bits, stack_len):
        out = []
        for i in range(stack_len):
            out.append((bits >> (7 * i)) & 0x7F)
        return out

    def pack_stack(nodes):
        bits = 0
        for i, node in enumerate(nodes[:max_stack_len]):
            bits |= (node & 0x7F) << (7 * i)
        return bits

    def pack(visited, camp, banned, spins, total_gain, explored, degree_sum, camp_depth, stack):
        return (
            (visited & visit_mask)
            | ((camp & 0x7F) << camp_shift)
            | ((banned & 0x7F) << banned_shift)
            | ((min(spins, 255) & 0xFF) << spins_shift)
            | ((min(total_gain, (1 << 14) - 1) & ((1 << 14) - 1)) << gain_shift)
            | ((min(explored, (1 << 9) - 1) & ((1 << 9) - 1)) << explore_shift)
            | ((min(degree_sum, 1023) & 0x3FF) << degree_shift)
            | ((min(camp_depth, 63) & 0x3F) << camp_depth_shift)
            | ((min(len(stack), max_stack_len) & 0x3F) << stack_len_shift)
            | ((pack_stack(stack) & stack_mask) << stack_shift)
        )

    if data is None:
        visited = 0
        camp = no_target
        banned = no_target
        spins = 0
        total_gain = 0
        explored = 0
        degree_sum = 0
        camp_depth = 0
        stack = [pos]
    else:
        state = int(data)
        visited = state & visit_mask
        camp = (state >> camp_shift) & 0x7F
        banned = (state >> banned_shift) & 0x7F
        spins = (state >> spins_shift) & 0xFF
        total_gain = (state >> gain_shift) & ((1 << 14) - 1)
        explored = (state >> explore_shift) & ((1 << 9) - 1)
        degree_sum = (state >> degree_shift) & 0x3FF
        camp_depth = (state >> camp_depth_shift) & 0x3F
        stack_len = (state >> stack_len_shift) & 0x3F
        stack = unpack_stack((state >> stack_shift) & stack_mask, stack_len)

    if not stack:
        stack = [pos]
    elif stack[-1] != pos:
        if pos in stack:
            stack = stack[: stack.index(pos) + 1]
        elif len(stack) >= 2 and stack[-2] == pos:
            stack = stack[:-1]
        else:
            stack = [pos]

    first_visit = ((visited >> pos) & 1) == 0
    visited |= 1 << pos
    explored = min(explored + 1, (1 << 9) - 1)
    remaining = total_steps - step
    avg_x8 = (total_gain * 8) // max(spins, 1) if spins else 0
    if first_visit:
        degree_sum = min(degree_sum + len(neighbors), 1023)
    visited_count = visited.bit_count()
    avg_degree_x10 = (degree_sum * 10) // max(visited_count, 1)
    current_depth = max(0, len(stack) - 1)
    stack_seed = 0
    for i, node in enumerate(stack[-8:]):
        stack_seed += (i + 5) * (node + 1)

    def pick(options, salt):
        ordered = sorted(options)
        seed = (
            step * 17
            + pos * 31
            + visited_count * 13
            + stack_seed * 7
            + explored * 5
            + current_depth * 11
            + salt
        )
        return ordered[seed % len(ordered)]

    if has_slot and camp != no_target and pos == camp:
        total_gain = min(total_gain + max(slot_coins, 0), (1 << 14) - 1)
        spins = min(spins + 1, 255)
        avg_x8 = (total_gain * 8) // max(spins, 1)

    if avg_degree_x10 >= 55:
        min_camp_depth = 2
        force_step = 110
        review_1 = 48
        poor_1 = 88
        review_2 = 96
        poor_2 = 112
    elif avg_degree_x10 >= 38:
        min_camp_depth = 5
        force_step = 180
        review_1 = 72
        poor_1 = 136
        review_2 = 144
        poor_2 = 168
    else:
        min_camp_depth = 8
        force_step = 240
        review_1 = 84
        poor_1 = 160
        review_2 = 168
        poor_2 = 200

    if camp != no_target and pos == camp and spins >= review_1:
        bail_now = False
        if spins >= review_2 and avg_x8 < poor_2:
            bail_now = True
        elif avg_x8 < poor_1 and (camp_depth <= min_camp_depth or avg_degree_x10 >= 55):
            bail_now = True
        elif avg_x8 < poor_1 and slot_coins < max(8, poor_1 // 16):
            bail_now = True
        if bail_now:
            banned = camp
            camp = no_target
            spins = 0
            total_gain = 0
            avg_x8 = 0
            camp_depth = 0

    if banned != no_target and pos != banned:
        banned = no_target

    ready_to_camp = (
        current_depth >= min_camp_depth
        or step >= force_step
        or slot_coins >= 24
        or remaining < 220
    )

    if has_slot and camp == no_target and pos != banned and ready_to_camp:
        camp = pos
        spins = 0
        total_gain = 0
        avg_x8 = 0
        camp_depth = current_depth

    if has_slot and pos != banned and camp != no_target and pos != camp:
        switch_now = False
        if slot_coins >= 36:
            switch_now = True
        elif current_depth >= camp_depth + 2 and step < total_steps - 160:
            switch_now = True
        elif current_depth > camp_depth and slot_coins >= 16:
            switch_now = True
        elif avg_degree_x10 >= 55 and slot_coins >= 18 and avg_x8 < 80:
            switch_now = True
        if switch_now:
            camp = pos
            spins = 0
            total_gain = 0
            avg_x8 = 0
            camp_depth = current_depth

    def next_stack_for(target):
        if target == -1:
            return stack
        if len(stack) >= 2 and target == stack[-2]:
            return stack[:-1]
        if target in stack:
            return stack[: stack.index(target) + 1]
        if not ((visited >> target) & 1):
            if len(stack) < max_stack_len:
                return stack + [target]
            return stack[1:] + [target]
        if target == pos:
            return stack
        return [pos, target]

    if has_slot and pos == camp:
        packed = pack(
            visited, camp, banned, spins, total_gain, explored, degree_sum, camp_depth, stack
        )
        return (-1, packed)

    if has_slot and pos == banned:
        forward = [n for n in neighbors if n != last_pos] or neighbors
        target = pick(forward, 5)
        packed = pack(
            visited,
            camp,
            banned,
            spins,
            total_gain,
            explored,
            degree_sum,
            camp_depth,
            next_stack_for(target),
        )
        return (target, packed)

    if camp != no_target and camp in neighbors:
        packed = pack(
            visited,
            camp,
            banned,
            spins,
            total_gain,
            explored,
            degree_sum,
            camp_depth,
            next_stack_for(camp),
        )
        return (camp, packed)

    unseen = [n for n in neighbors if not ((visited >> n) & 1)]
    if unseen:
        if len(stack) >= 2:
            unseen_forward = [n for n in unseen if n != stack[-2]]
            if unseen_forward:
                unseen = unseen_forward
        target = pick(unseen, 1)
        packed = pack(
            visited,
            camp,
            banned,
            spins,
            total_gain,
            explored,
            degree_sum,
            camp_depth,
            next_stack_for(target),
        )
        return (target, packed)

    if len(stack) >= 2 and stack[-2] in neighbors:
        target = stack[-2]
        packed = pack(
            visited,
            camp,
            banned,
            spins,
            total_gain,
            explored,
            degree_sum,
            camp_depth,
            next_stack_for(target),
        )
        return (target, packed)

    forward = [n for n in neighbors if n != last_pos] or neighbors
    target = pick(forward, 3)
    packed = pack(
        visited,
        camp,
        banned,
        spins,
        total_gain,
        explored,
        degree_sum,
        camp_depth,
        next_stack_for(target),
    )
    return (target, packed)


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
