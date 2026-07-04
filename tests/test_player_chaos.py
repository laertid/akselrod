"""Tests for the base-class `Player.chaos` feature.

Chaos is orthogonal to any subclass strategy: with probability `chaos`
the base class returns a uniformly random Action (50/50) instead of
delegating to `do_deal`. Verified here at the Player level (isolated)
and at the Game level (integration).
"""

from __future__ import annotations

import random

import pytest

from pd import (
    AlwaysCooperate,
    AlwaysDefect,
    DealPayoff,
    Game,
    RandomDefect,
    StaticGenerator,
    TitForTat,
)
from pd.deal import Action, Deal


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


CLASSIC = DealPayoff(
    payoff_cc_1=3.0, payoff_cc_2=3.0,
    payoff_cd_1=0.0, payoff_cd_2=5.0,
    payoff_dc_1=5.0, payoff_dc_2=0.0,
    payoff_dd_1=1.0, payoff_dd_2=1.0,
)


def _decide(player, opponent, round_index: int = 0) -> Action:
    return player.decide(
        opponent=opponent,
        payoff=CLASSIC,
        self_is_player_1=True,
        round_index=round_index,
    )


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def test_chaos_default_is_zero():
    p = AlwaysCooperate()
    assert p.chaos == 0.0


def test_chaos_valid_range():
    assert AlwaysCooperate(chaos=0.0).chaos == 0.0
    assert AlwaysCooperate(chaos=0.5).chaos == 0.5
    assert AlwaysCooperate(chaos=1.0).chaos == 1.0


@pytest.mark.parametrize("bad", [-0.1, -1.0, 1.1, 2.0])
def test_chaos_out_of_range_raises(bad):
    with pytest.raises(ValueError, match=r"chaos must be in \[0.0, 1.0\]"):
        AlwaysCooperate(chaos=bad)


# ---------------------------------------------------------------------------
# chaos == 0: strategy is untouched
# ---------------------------------------------------------------------------


def test_chaos_zero_never_touches_strategy():
    """With chaos=0, `decide` must always delegate to `do_deal` -- for
    AlwaysCooperate that means COOPERATE every time.
    """
    p = AlwaysCooperate(chaos=0.0, chaos_rng=random.Random(1))
    other = AlwaysDefect()
    for _ in range(200):
        assert _decide(p, other) is Action.COOPERATE


# ---------------------------------------------------------------------------
# chaos == 1: strategy is always overridden
# ---------------------------------------------------------------------------


def test_chaos_one_always_overrides_strategy():
    """With chaos=1, `decide` must NEVER call `do_deal`. We prove that
    by asserting the returned distribution is ~50/50 rather than the
    subclass output (100% COOPERATE would happen for AlwaysCooperate
    without chaos).
    """
    p = AlwaysCooperate(chaos=1.0, chaos_rng=random.Random(42))
    other = AlwaysDefect()
    n = 2000
    defects = sum(1 for _ in range(n) if _decide(p, other) is Action.DEFECT)
    # Expect ~n/2 defects. Allow wide slack for randomness.
    assert 0.4 * n < defects < 0.6 * n, defects


def test_chaos_one_never_calls_do_deal():
    """Verify by monkey-patching `do_deal` to fail loudly."""

    class Sentinel(AlwaysCooperate):
        def do_deal(self, *args, **kwargs):  # type: ignore[override]
            raise AssertionError("do_deal must not be called when chaos=1")

    p = Sentinel(chaos=1.0, chaos_rng=random.Random(7))
    other = AlwaysDefect()
    for _ in range(50):
        _decide(p, other)  # must not raise


# ---------------------------------------------------------------------------
# 0 < chaos < 1: mix rate matches expectation
# ---------------------------------------------------------------------------


def test_chaos_mixes_with_strategy_alwaysdefect():
    """AlwaysDefect(chaos=0.4): the strategy outputs DEFECT, chaos flips
    a coin (50/50). Expected P(DEFECT) = 0.6 * 1.0 + 0.4 * 0.5 = 0.8.
    """
    p = AlwaysDefect(chaos=0.4, chaos_rng=random.Random(2026))
    other = AlwaysCooperate()
    n = 5000
    defects = sum(1 for _ in range(n) if _decide(p, other) is Action.DEFECT)
    # Expected ~0.8 * n = 4000. 3σ range is comfortably within ±100.
    assert 3800 < defects < 4200, defects


def test_chaos_mixes_with_strategy_randomdefect():
    """RandomDefect(p=0.3, chaos=0.2): expected P(DEFECT) =
    0.8 * 0.3 + 0.2 * 0.5 = 0.34.
    """
    p = RandomDefect(
        p=0.3,
        rng=random.Random(11),
        chaos=0.2,
        chaos_rng=random.Random(13),
    )
    other = AlwaysCooperate()
    n = 5000
    defects = sum(1 for _ in range(n) if _decide(p, other) is Action.DEFECT)
    # Expected ~0.34 * n = 1700. Allow ±150.
    assert 1550 < defects < 1850, defects


# ---------------------------------------------------------------------------
# Reproducibility: same chaos_rng seed => same decisions
# ---------------------------------------------------------------------------


def test_chaos_reproducible_with_seeded_rng():
    a = AlwaysCooperate(chaos=0.5, chaos_rng=random.Random(2026))
    b = AlwaysCooperate(chaos=0.5, chaos_rng=random.Random(2026))
    other = AlwaysDefect()
    seq_a = [_decide(a, other) for _ in range(200)]
    seq_b = [_decide(b, other) for _ in range(200)]
    assert seq_a == seq_b


# ---------------------------------------------------------------------------
# Isolation: chaos_rng is independent of any strategy rng
# ---------------------------------------------------------------------------


def test_chaos_rng_independent_of_strategy_rng():
    """RandomDefect draws from `rng`. Its chaos coin draws from
    `chaos_rng`. Changing chaos_rng must NOT change the sequence of
    strategy draws for the deals where chaos does not fire.
    """
    # Both players: same p / same strategy rng seed, different chaos_rng.
    # Verify their per-deal strategy decisions coincide *when neither
    # gets chaos-perturbed*.
    p1 = RandomDefect(
        p=0.5,
        rng=random.Random(100),
        chaos=0.0,  # never fires
        chaos_rng=random.Random(1),
    )
    p2 = RandomDefect(
        p=0.5,
        rng=random.Random(100),
        chaos=0.0,  # never fires
        chaos_rng=random.Random(999),
    )
    other = AlwaysCooperate()
    seq_1 = [_decide(p1, other) for _ in range(500)]
    seq_2 = [_decide(p2, other) for _ in range(500)]
    assert seq_1 == seq_2


# ---------------------------------------------------------------------------
# Integration: Game routes through decide, so chaos affects gameplay
# ---------------------------------------------------------------------------


def test_game_uses_decide_and_chaos_changes_outcomes():
    """Two TitForTat players with chaos > 0 must sometimes defect even
    though the pure-TFT trajectory (starting from mutual cooperation)
    stays in all-C. Under chaos, we expect at least one D across many
    deals.
    """
    a = TitForTat(chaos=0.3, chaos_rng=random.Random(2026))
    b = TitForTat(chaos=0.3, chaos_rng=random.Random(2027))
    game = Game(
        deal_generator=StaticGenerator(CLASSIC),
        players=[a, b],
        total_rounds=50,
        rng=random.Random(0),
    )
    game.play()

    actions = [d.action_1 for d in game.history] + [d.action_2 for d in game.history]
    assert Action.DEFECT in actions, "chaos=0.3 for 50 rounds should produce some defects"


def test_game_chaos_zero_matches_pure_strategy():
    """Two TFTs with chaos=0 stay in mutual cooperation forever."""
    a = TitForTat(chaos=0.0)
    b = TitForTat(chaos=0.0)
    game = Game(
        deal_generator=StaticGenerator(CLASSIC),
        players=[a, b],
        total_rounds=20,
        rng=random.Random(0),
    )
    game.play()
    for deal in game.history:
        assert deal.action_1 is Action.COOPERATE
        assert deal.action_2 is Action.COOPERATE
