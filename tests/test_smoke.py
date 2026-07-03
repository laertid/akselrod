"""Smoke tests for the framework skeleton."""

import random

import pytest

from pd import (
    Action,
    AlwaysCooperate,
    ClassicAxelrodGenerator,
    Deal,
    DealPayoff,
    Game,
    Player,
)


def _rng(seed: int = 0) -> random.Random:
    return random.Random(seed)


def test_payoff_resolve():
    p = DealPayoff(3, 3, 0, 5, 5, 0, 1, 1)
    assert p.resolve(Action.COOPERATE, Action.COOPERATE) == (3, 3)
    assert p.resolve(Action.COOPERATE, Action.DEFECT) == (0, 5)
    assert p.resolve(Action.DEFECT, Action.COOPERATE) == (5, 0)
    assert p.resolve(Action.DEFECT, Action.DEFECT) == (1, 1)


def test_classic_generator_matrix():
    gen = ClassicAxelrodGenerator()
    a = AlwaysCooperate()
    b = AlwaysCooperate()
    Game(gen, [a, b], total_rounds=1, rng=_rng())  # binds ids
    deal = gen.generate(a, b, round_index=0)
    assert deal.payoff.payoff_cc_1 == 3
    assert deal.payoff.payoff_dc_1 == 5
    assert deal.payoff.payoff_cd_1 == 0
    assert deal.payoff.payoff_dd_1 == 1


def test_classic_generator_rejects_invalid_matrix():
    with pytest.raises(ValueError):
        ClassicAxelrodGenerator(temptation=2, reward=3, punishment=1, sucker=0)


def test_all_cooperate_game():
    players = [AlwaysCooperate() for _ in range(4)]
    game = Game(ClassicAxelrodGenerator(), players, total_rounds=10, rng=_rng(42))
    game.play()

    # 4 players, C(4,2)=6 pairs per round, 10 rounds = 60 deals
    assert len(game.history) == 60
    # Every deal is C/C, so score is R=3 for both
    for deal in game.history:
        assert deal.action_1 == Action.COOPERATE
        assert deal.action_2 == Action.COOPERATE
        assert deal.score_1 == 3 and deal.score_2 == 3
    # Each player played 3 opponents * 10 rounds = 30 deals, all giving 3
    for p in players:
        assert len(p.history) == 30
        assert p.total_score() == 90


def test_player_ids_are_assigned():
    players = [AlwaysCooperate(), AlwaysCooperate(), AlwaysCooperate()]
    Game(ClassicAxelrodGenerator(), players, total_rounds=1, rng=_rng())
    ids = [p.player_id for p in players]
    assert ids == [0, 1, 2]


def test_player_cannot_bind_twice():
    p = AlwaysCooperate()
    q = AlwaysCooperate()
    Game(ClassicAxelrodGenerator(), [p, q], total_rounds=1, rng=_rng())
    with pytest.raises(RuntimeError):
        Game(ClassicAxelrodGenerator(), [p, q], total_rounds=1, rng=_rng())


def test_players_do_not_play_themselves():
    players = [AlwaysCooperate() for _ in range(3)]
    game = Game(ClassicAxelrodGenerator(), players, total_rounds=5, rng=_rng())
    game.play()
    for deal in game.history:
        assert deal.player_1 is not deal.player_2


def test_history_with_opponent():
    a, b, c = AlwaysCooperate(), AlwaysCooperate(), AlwaysCooperate()
    game = Game(ClassicAxelrodGenerator(), [a, b, c], total_rounds=4, rng=_rng())
    game.play()
    assert len(a.history_with(b)) == 4
    assert len(a.history_with(c)) == 4
    for d in a.history_with(b):
        assert d in a.history


def test_deal_executes_only_once():
    a, b = AlwaysCooperate(), AlwaysCooperate()
    Game(ClassicAxelrodGenerator(), [a, b], total_rounds=1, rng=_rng())
    payoff = DealPayoff(3, 3, 0, 5, 5, 0, 1, 1)
    deal = Deal(player_1=a, player_2=b, payoff=payoff, round_index=0)
    deal.execute()
    with pytest.raises(RuntimeError):
        deal.execute()


def test_game_stores_rng_and_players_can_reach_it():
    """Any bound player sees the same Game and the same rng instance."""
    p = AlwaysCooperate()
    q = AlwaysCooperate()
    rng = _rng(7)
    game = Game(ClassicAxelrodGenerator(), [p, q], total_rounds=1, rng=rng)
    assert game.rng is rng
    assert p.game is game
    assert p.game.rng is rng
    assert q.game.rng is rng


def test_reproducibility_via_game_rng():
    """A stochastic player that pulls from self.game.rng gives the same
    sequence when both the shuffling rng and the game share a seed."""

    class Coinflip(Player):
        @staticmethod
        def name() -> str:
            return "Coinflip"

        def do_deal(self, opponent, payoff, self_is_player_1, round_index):
            return (
                Action.COOPERATE
                if self.game.rng.random() < 0.5
                else Action.DEFECT
            )

    def run(seed):
        players = [Coinflip() for _ in range(4)]
        g = Game(
            ClassicAxelrodGenerator(),
            players,
            total_rounds=20,
            rng=random.Random(seed),
        )
        g.play()
        return [(d.action_1, d.action_2) for d in g.history]

    assert run(123) == run(123)
    assert run(123) != run(124)


def test_simultaneous_choice_no_peeking():
    """A player looking at opponent's history for THIS deal must not see
    the opponent's current action, since choices are simultaneous."""

    seen_current_deal_from_opponent: list[bool] = []

    class Peeker(Player):
        @staticmethod
        def name() -> str:
            return "Peeker"

        def do_deal(self, opponent, payoff, self_is_player_1, round_index):
            for d in opponent.history:
                if d.round_index == round_index and (
                    d.player_1 is self or d.player_2 is self
                ):
                    seen_current_deal_from_opponent.append(True)
            return Action.COOPERATE

    players = [Peeker(), Peeker()]
    Game(ClassicAxelrodGenerator(), players, total_rounds=5, rng=_rng()).play()
    assert seen_current_deal_from_opponent == []
