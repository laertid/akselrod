"""Smoke tests for the framework skeleton."""

import pytest

from pd import (
    Action,
    AlwaysCooperate,
    ClassicAxelrodGenerator,
    Deal,
    DealPayoff,
    Game,
    Player,
    create_rng,
    global_rng,
    set_seed,
)


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
    Game(gen, [a, b], total_rounds=1)  # binds ids
    deal = gen.generate(a, b, round_index=0)
    assert deal.payoff.payoff_cc_1 == 3
    assert deal.payoff.payoff_dc_1 == 5
    assert deal.payoff.payoff_cd_1 == 0
    assert deal.payoff.payoff_dd_1 == 1


def test_classic_generator_rejects_invalid_matrix():
    with pytest.raises(ValueError):
        ClassicAxelrodGenerator(temptation=2, reward=3, punishment=1, sucker=0)


def test_all_cooperate_game():
    set_seed(42)
    players = [AlwaysCooperate() for _ in range(4)]
    game = Game(ClassicAxelrodGenerator(), players, total_rounds=10)
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
    Game(ClassicAxelrodGenerator(), players, total_rounds=1)
    ids = [p.player_id for p in players]
    assert ids == [0, 1, 2]


def test_player_cannot_bind_twice():
    p = AlwaysCooperate()
    q = AlwaysCooperate()
    Game(ClassicAxelrodGenerator(), [p, q], total_rounds=1)
    with pytest.raises(RuntimeError):
        Game(ClassicAxelrodGenerator(), [p, q], total_rounds=1)


def test_players_do_not_play_themselves():
    set_seed(0)
    players = [AlwaysCooperate() for _ in range(3)]
    game = Game(ClassicAxelrodGenerator(), players, total_rounds=5)
    game.play()
    for deal in game.history:
        assert deal.player_1 is not deal.player_2


def test_history_with_opponent():
    set_seed(0)
    a, b, c = AlwaysCooperate(), AlwaysCooperate(), AlwaysCooperate()
    game = Game(ClassicAxelrodGenerator(), [a, b, c], total_rounds=4)
    game.play()
    assert len(a.history_with(b)) == 4
    assert len(a.history_with(c)) == 4
    # Sanity: a's history_with(b) is a subset of a.history
    for d in a.history_with(b):
        assert d in a.history


def test_deal_executes_only_once():
    a, b = AlwaysCooperate(), AlwaysCooperate()
    Game(ClassicAxelrodGenerator(), [a, b], total_rounds=1)
    payoff = DealPayoff(3, 3, 0, 5, 5, 0, 1, 1)
    deal = Deal(player_1=a, player_2=b, payoff=payoff, round_index=0)
    deal.execute()
    with pytest.raises(RuntimeError):
        deal.execute()


def test_reproducibility_via_seed():
    class Coinflip(Player):
        @staticmethod
        def name() -> str:
            return "Coinflip"

        def do_deal(self, opponent, payoff, self_is_player_1, round_index):
            return Action.COOPERATE if global_rng().random() < 0.5 else Action.DEFECT

    def run(seed):
        set_seed(seed)
        players = [Coinflip() for _ in range(4)]
        g = Game(ClassicAxelrodGenerator(), players, total_rounds=20)
        g.play()
        return [(d.action_1, d.action_2) for d in g.history]

    assert run(123) == run(123)
    assert run(123) != run(124)


def test_create_rng_none_returns_global():
    r = create_rng(None)
    assert r is global_rng()


def test_create_rng_with_seed_is_independent_and_reproducible():
    r1 = create_rng("hello")
    r2 = create_rng("hello")
    # Fresh instances, not the global one.
    assert r1 is not global_rng()
    assert r1 is not r2
    # Same seed -> same sequence.
    seq1 = [r1.random() for _ in range(5)]
    seq2 = [r2.random() for _ in range(5)]
    assert seq1 == seq2
    # Different seed -> different sequence.
    r3 = create_rng("world")
    seq3 = [r3.random() for _ in range(5)]
    assert seq3 != seq1


def test_create_rng_does_not_affect_global():
    set_seed(42)
    baseline = [global_rng().random() for _ in range(3)]
    set_seed(42)
    # Using create_rng in between must not touch the global stream.
    local = create_rng("noise")
    _ = [local.random() for _ in range(3)]
    after = [global_rng().random() for _ in range(3)]
    assert baseline == after


def test_simultaneous_choice_no_peeking():
    """A player looking at opponent's history for THIS deal must not see
    the opponent's current action, since choices are simultaneous."""

    seen_current_deal_from_opponent: list[bool] = []

    class Peeker(Player):
        @staticmethod
        def name() -> str:
            return "Peeker"

        def do_deal(self, opponent, payoff, self_is_player_1, round_index):
            # At decision time, no deal from THIS round should be in the
            # opponent's history yet.
            for d in opponent.history:
                if d.round_index == round_index and (
                    d.player_1 is self or d.player_2 is self
                ):
                    seen_current_deal_from_opponent.append(True)
            return Action.COOPERATE

    set_seed(1)
    players = [Peeker(), Peeker()]
    Game(ClassicAxelrodGenerator(), players, total_rounds=5).play()
    assert seen_current_deal_from_opponent == []
