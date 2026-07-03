"""Tests for the TitForTat strategy."""

import pytest

from pd import (
    Action,
    AlwaysCooperate,
    ClassicAxelrodGenerator,
    DealPayoff,
    Game,
    Player,
    TitForTat,
    set_seed,
)


# ---- helper strategies used only in tests -----------------------------------


class AlwaysDefect(Player):
    @staticmethod
    def name() -> str:
        return "AlwaysDefect"

    def do_deal(self, opponent, payoff, self_is_player_1, round_index):
        return Action.DEFECT


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
    set_seed(0)
    tft = TitForTat()
    coop = AlwaysCooperate()
    game = Game(ClassicAxelrodGenerator(), [tft, coop], total_rounds=1)
    game.play()

    # Exactly one deal; TFT's action is COOPERATE regardless of role.
    (deal,) = game.history
    tft_action = deal.action_1 if deal.player_1 is tft else deal.action_2
    assert tft_action == Action.COOPERATE


def test_mirrors_cooperator_forever():
    set_seed(0)
    tft = TitForTat()
    coop = AlwaysCooperate()
    game = Game(ClassicAxelrodGenerator(), [tft, coop], total_rounds=20)
    game.play()

    for deal in game.history:
        tft_action = deal.action_1 if deal.player_1 is tft else deal.action_2
        assert tft_action == Action.COOPERATE
    # Full C/C -> R=3 per round -> 60 total for each.
    assert tft.total_score() == 60
    assert coop.total_score() == 60


def test_retaliates_against_defector_from_round_two():
    set_seed(0)
    tft = TitForTat()
    ad = AlwaysDefect()
    game = Game(ClassicAxelrodGenerator(), [tft, ad], total_rounds=5)
    game.play()

    # TFT plays C once (round 0), then D forever (rounds 1..4).
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
    # Scores: (S=0) + 4*(P=1) = 4 for TFT; (T=5) + 4*(P=1) = 9 for AllD.
    assert tft.total_score() == 4
    assert ad.total_score() == 9


def test_forgives_when_opponent_returns_to_cooperation():
    """If the opponent defects once and then cooperates, TFT should punish
    exactly once and then return to cooperation on the very next round."""
    set_seed(0)
    tft = TitForTat()
    # 5 rounds: C, D, C, C, C
    scripted = Scripted([
        Action.COOPERATE,
        Action.DEFECT,
        Action.COOPERATE,
        Action.COOPERATE,
        Action.COOPERATE,
    ])
    game = Game(ClassicAxelrodGenerator(), [tft, scripted], total_rounds=5)
    game.play()

    tft_actions = [
        d.action_1 if d.player_1 is tft else d.action_2 for d in game.history
    ]
    assert tft_actions == [
        Action.COOPERATE,  # first move
        Action.COOPERATE,  # mirrors opponent's round-0 C
        Action.DEFECT,     # mirrors opponent's round-1 D (retaliation)
        Action.COOPERATE,  # mirrors opponent's round-2 C (forgiven)
        Action.COOPERATE,
    ]


def test_pairwise_history_is_isolated_between_opponents():
    """TFT should not carry grudges from opponent A into games with opponent B."""
    set_seed(1)
    tft = TitForTat()
    ad = AlwaysDefect()
    coop = AlwaysCooperate()
    game = Game(ClassicAxelrodGenerator(), [tft, ad, coop], total_rounds=10)
    game.play()

    # Against AllD: first C then all D.
    vs_ad = tft.history_with(ad)
    tft_actions_vs_ad = [
        d.action_1 if d.player_1 is tft else d.action_2 for d in vs_ad
    ]
    assert tft_actions_vs_ad[0] == Action.COOPERATE
    assert all(a == Action.DEFECT for a in tft_actions_vs_ad[1:])

    # Against AllC: always C, unaffected by the AllD grudge.
    vs_coop = tft.history_with(coop)
    tft_actions_vs_coop = [
        d.action_1 if d.player_1 is tft else d.action_2 for d in vs_coop
    ]
    assert all(a == Action.COOPERATE for a in tft_actions_vs_coop)


def test_tft_vs_tft_stays_in_mutual_cooperation():
    set_seed(0)
    a, b = TitForTat(), TitForTat()
    game = Game(ClassicAxelrodGenerator(), [a, b], total_rounds=50)
    game.play()

    for deal in game.history:
        assert deal.action_1 == Action.COOPERATE
        assert deal.action_2 == Action.COOPERATE
    assert a.total_score() == 150
    assert b.total_score() == 150


def test_name_is_stable_and_distinct():
    assert TitForTat.name() == "TitForTat"
    assert TitForTat.name() != AlwaysCooperate.name()
