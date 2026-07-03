"""Tests for the TitForTat strategy."""

import random

from pd import (
    Action,
    AlwaysCooperate,
    AlwaysDefect,
    ClassicAxelrodGenerator,
    Game,
    Player,
    TitForTat,
)


def _rng(seed: int = 0) -> random.Random:
    return random.Random(seed)


# ---- helper strategy used only in tests -------------------------------------


class Scripted(Player):
    """Plays a fixed sequence of actions, one per round-with-this-caller."""

    def __init__(self, script: list[Action]) -> None:
        super().__init__()
        self._script = script
        self._i = 0

    @staticmethod
    def name() -> str:
        return "Scripted"

    def do_deal(self, opponent, payoff, self_is_player_1, round_index):
        a = self._script[self._i]
        self._i += 1
        return a


# ---- tests ------------------------------------------------------------------


def test_first_move_is_cooperate():
    tft = TitForTat()
    coop = AlwaysCooperate()
    game = Game(ClassicAxelrodGenerator(), [tft, coop], total_rounds=1, rng=_rng())
    game.play()

    (deal,) = game.history
    tft_action = deal.action_1 if deal.player_1 is tft else deal.action_2
    assert tft_action == Action.COOPERATE


def test_mirrors_cooperator_forever():
    tft = TitForTat()
    coop = AlwaysCooperate()
    game = Game(ClassicAxelrodGenerator(), [tft, coop], total_rounds=20, rng=_rng())
    game.play()

    for deal in game.history:
        tft_action = deal.action_1 if deal.player_1 is tft else deal.action_2
        assert tft_action == Action.COOPERATE
    assert tft.total_score() == 60
    assert coop.total_score() == 60


def test_retaliates_against_defector_from_round_two():
    tft = TitForTat()
    ad = AlwaysDefect()
    game = Game(ClassicAxelrodGenerator(), [tft, ad], total_rounds=5, rng=_rng())
    game.play()

    tft_actions = [
        d.action_1 if d.player_1 is tft else d.action_2 for d in game.history
    ]
    assert tft_actions == [
        Action.COOPERATE,
        Action.DEFECT,
        Action.DEFECT,
        Action.DEFECT,
        Action.DEFECT,
    ]
    assert tft.total_score() == 4
    assert ad.total_score() == 9


def test_forgives_when_opponent_returns_to_cooperation():
    tft = TitForTat()
    scripted = Scripted([
        Action.COOPERATE,
        Action.DEFECT,
        Action.COOPERATE,
        Action.COOPERATE,
        Action.COOPERATE,
    ])
    game = Game(
        ClassicAxelrodGenerator(), [tft, scripted], total_rounds=5, rng=_rng()
    )
    game.play()

    tft_actions = [
        d.action_1 if d.player_1 is tft else d.action_2 for d in game.history
    ]
    assert tft_actions == [
        Action.COOPERATE,
        Action.COOPERATE,
        Action.DEFECT,
        Action.COOPERATE,
        Action.COOPERATE,
    ]


def test_pairwise_history_is_isolated_between_opponents():
    tft = TitForTat()
    ad = AlwaysDefect()
    coop = AlwaysCooperate()
    game = Game(
        ClassicAxelrodGenerator(), [tft, ad, coop], total_rounds=10, rng=_rng(1)
    )
    game.play()

    vs_ad = tft.history_with(ad)
    tft_actions_vs_ad = [
        d.action_1 if d.player_1 is tft else d.action_2 for d in vs_ad
    ]
    assert tft_actions_vs_ad[0] == Action.COOPERATE
    assert all(a == Action.DEFECT for a in tft_actions_vs_ad[1:])

    vs_coop = tft.history_with(coop)
    tft_actions_vs_coop = [
        d.action_1 if d.player_1 is tft else d.action_2 for d in vs_coop
    ]
    assert all(a == Action.COOPERATE for a in tft_actions_vs_coop)


def test_tft_vs_tft_stays_in_mutual_cooperation():
    a, b = TitForTat(), TitForTat()
    game = Game(ClassicAxelrodGenerator(), [a, b], total_rounds=50, rng=_rng())
    game.play()

    for deal in game.history:
        assert deal.action_1 == Action.COOPERATE
        assert deal.action_2 == Action.COOPERATE
    assert a.total_score() == 150
    assert b.total_score() == 150


def test_name_is_stable_and_distinct():
    assert TitForTat.name() == "TitForTat"
    assert TitForTat.name() != AlwaysCooperate.name()
