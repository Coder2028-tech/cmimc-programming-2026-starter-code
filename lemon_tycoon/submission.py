from collections import defaultdict
from typing import Dict, List, Tuple
import math

from players.player import Player


class SubmissionPlayer(Player):
    def __init__(
        self,
        player_id: int,
        num_players: int,
        factory_bit_width: int,
        sell_price: float,
        buy_price: float,
        sabotage_cost: float,
        initial_lemons: float,
        goal_lemons: float,
        max_rounds: int,
    ):
        self.player_id = player_id
        self.num_players = num_players
        self.sell_price = sell_price
        self.buy_price = buy_price
        self.sabotage_cost = sabotage_cost
        self.goal_lemons = goal_lemons
        self.max_rounds = max_rounds
        self.max_factory_id = 2 ** factory_bit_width

        self.production_rates = {
            factory_id: 2.0 * math.log2(factory_id)
            for factory_id in range(1, self.max_factory_id + 1)
        }
        self.tracked_ids = list(
            range(max(2, self.max_factory_id - 5), self.max_factory_id + 1)
        )
        self.public_heat = {
            factory_id: 0.0 for factory_id in range(1, self.max_factory_id + 1)
        }
        self.inferred_focus = {pid: None for pid in range(num_players)}
        self.last_observed_round = -1

    def _observe_public_state(
        self,
        round_number: int,
        all_lemons: List[float],
        destroyed_factory_counts: Dict[int, int],
        sabotages_by_player: List[List[int]],
    ) -> None:
        if round_number == self.last_observed_round:
            return

        for factory_id in range(1, self.max_factory_id + 1):
            self.public_heat[factory_id] *= 0.7

        for factory_id, destroyed in destroyed_factory_counts.items():
            if 1 <= factory_id <= self.max_factory_id:
                self.public_heat[factory_id] += 1.5 + 0.2 * destroyed

        for sabotage_list in sabotages_by_player:
            for factory_id in sabotage_list:
                if 1 <= factory_id <= self.max_factory_id:
                    self.public_heat[factory_id] += 0.8

        if round_number == 2:
            for pid, lemons in enumerate(all_lemons):
                if pid == self.player_id:
                    continue
                inferred_rate = max(0.0, lemons / 2.0)
                self.inferred_focus[pid] = min(
                    self.tracked_ids,
                    key=lambda factory_id: abs(
                        self.production_rates[factory_id] - inferred_rate
                    ),
                )

        self.last_observed_round = round_number

    def _buy_order(self) -> List[int]:
        focus_counts = defaultdict(int)
        for pid, factory_id in self.inferred_focus.items():
            if pid != self.player_id and factory_id is not None:
                focus_counts[factory_id] += 1

        return sorted(
            self.tracked_ids,
            key=lambda factory_id: (
                self.production_rates[factory_id]
                - 0.9 * focus_counts[factory_id]
                - 0.55 * self.public_heat[factory_id],
                factory_id,
            ),
            reverse=True,
        )

    def play(
        self,
        round_number: int,
        your_lemons: float,
        your_factories: List[int],
        all_lemons: List[float],
        destroyed_factory_counts: Dict[int, int],
        sabotages_by_player: List[List[int]],
    ) -> Tuple[List[int], List[int], List[int]]:
        self._observe_public_state(
            round_number,
            all_lemons,
            destroyed_factory_counts,
            sabotages_by_player,
        )

        buy_order = self._buy_order()
        leader_id = max(range(self.num_players), key=lambda pid: all_lemons[pid])
        leader_focus = self.inferred_focus.get(leader_id)
        leader_last_sabotages = (
            set(sabotages_by_player[leader_id])
            if leader_id < len(sabotages_by_player)
            else set()
        )

        if leader_focus in leader_last_sabotages:
            alternatives = [
                factory_id
                for factory_id in buy_order
                if factory_id not in leader_last_sabotages
            ]
            leader_focus = alternatives[0] if alternatives else None

        sells: List[int] = []
        sabotages: List[int] = []
        spendable_lemons = your_lemons

        if leader_id != self.player_id and round_number >= 4:
            sabotage_target = leader_focus
            if sabotage_target is None:
                viable_targets = [
                    factory_id
                    for factory_id in self.tracked_ids
                    if factory_id not in leader_last_sabotages
                ]
                sabotage_target = max(
                    viable_targets if viable_targets else self.tracked_ids,
                    key=lambda factory_id: self.public_heat[factory_id] + 0.4 * factory_id,
                )

            leader_gap = all_lemons[leader_id] - your_lemons
            should_sabotage = (
                spendable_lemons >= self.sabotage_cost
                and (
                    leader_gap >= 30
                    or all_lemons[leader_id] >= self.goal_lemons - 200
                    or self.public_heat[sabotage_target] >= 2.0
                )
            )

            if should_sabotage:
                owned_target_count = your_factories[sabotage_target - 1]
                if owned_target_count > 0:
                    sells = [sabotage_target] * owned_target_count
                    spendable_lemons += self.sell_price * owned_target_count
                sabotages = [sabotage_target]
                spendable_lemons -= self.sabotage_cost

        projected_factories = your_factories[:]
        if sells:
            projected_factories[sells[0] - 1] = 0

        buys: List[int] = []
        num_to_buy = int(spendable_lemons // self.buy_price)
        for _ in range(num_to_buy):
            best_factory_id = max(
                buy_order,
                key=lambda factory_id: (
                    self.production_rates[factory_id]
                    - 0.25 * projected_factories[factory_id - 1]
                    - 0.5 * (factory_id in sabotages)
                    - 0.55 * self.public_heat[factory_id]
                ),
            )
            buys.append(best_factory_id)
            projected_factories[best_factory_id - 1] += 1

        return buys, sells, sabotages


SubmissionStrategy = SubmissionPlayer
