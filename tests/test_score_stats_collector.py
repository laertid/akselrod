"""Tests for pd.collectors.ScoreStatsCollector."""

from __future__ import annotations

import random
import statistics

import pytest

from pd import (
    AlwaysCooperate,
    AlwaysDefect,
    DealPayoff,
    Game,
    GameStats,
    Multigame,
    RandomDefect,
    ScoreStatsCollector,
    StaticGenerator,
    TitForTat,
)
from pd.collectors.score_stats import METRICS, PERCENTILES


CLASSIC = DealPayoff(
    payoff_cc_1=3.0, payoff_cc_2=3.0,
    payoff_cd_1=0.0, payoff_cd_2=5.0,
    payoff_dc_1=5.0, payoff_dc_2=0.0,
    payoff_dd_1=1.0, payoff_dd_2=1.0,
)


def _make_game(strategies: list, rounds: int, seed: int) -> Game:
    players = [cls() for cls in strategies]
    return Game(
        deal_generator=StaticGenerator(CLASSIC),
        players=players,
        total_rounds=rounds,
        rng=random.Random(seed),
    )


def _ctx(i: int, j: int, n_defect: int = 0, p: float = 0.0) -> dict:
    return {"i": i, "j": j, "n_defect": n_defect, "p": p}


# ---------------------------------------------------------------------------
# Basic collect
# ---------------------------------------------------------------------------


def test_collect_writes_one_row_per_game_with_all_metrics():
    game = _make_game([AlwaysCooperate, AlwaysCooperate], rounds=5, seed=1)
    game.play()

    collector = ScoreStatsCollector()
    collector.collect(game, _ctx(2, 3))

    assert len(collector.rows) == 1
    row = collector.rows[0]
    assert isinstance(row, GameStats)
    assert row.i == 2 and row.j == 3
    assert set(row.metrics.keys()) == set(METRICS)


def test_collect_reads_context_metadata():
    game = _make_game([AlwaysCooperate, AlwaysDefect], rounds=3, seed=1)
    game.play()

    collector = ScoreStatsCollector()
    collector.collect(game, _ctx(4, 5, n_defect=17, p=0.42))

    row = collector.rows[0]
    assert row.i == 4
    assert row.j == 5
    assert row.n_defect == 17
    assert row.p == 0.42


def test_context_missing_key_raises():
    game = _make_game([AlwaysCooperate, AlwaysDefect], rounds=1, seed=1)
    game.play()
    collector = ScoreStatsCollector()
    with pytest.raises(KeyError):
        collector.collect(game, {"i": 0, "j": 0})  # missing n_defect / p


# ---------------------------------------------------------------------------
# Metric correctness on a known game
# ---------------------------------------------------------------------------


def test_metrics_on_all_cooperators_are_all_equal_to_mean():
    """4 AllC players, 3 rounds. C(4,2)=6 pairs, each pair plays 3 deals,
    each deal awards R=3 to both -> per-player total = 6*3/2 * ...
    Actually simpler: each player plays against every other player for
    3 rounds. Each of those 3 deals gives them R=3. So total per player
    = 3 opponents * 3 rounds * 3 = 27."""
    game = _make_game(
        [AlwaysCooperate, AlwaysCooperate, AlwaysCooperate, AlwaysCooperate],
        rounds=3,
        seed=1,
    )
    game.play()

    collector = ScoreStatsCollector()
    collector.collect(game, _ctx(0, 0))
    m = collector.rows[0].metrics

    assert m["sum"] == 27.0 * 4
    assert m["avg"] == 27.0
    assert m["max"] == 27.0
    # All players identical -> every percentile == 27.
    for q in PERCENTILES:
        assert m[f"p{q}"] == 27.0


def test_metrics_on_allc_vs_alld_split():
    """3 AllC + 3 AllD, 2 rounds.
    - AllC vs AllC (C(3,2)=3 pairs): each AllC gets R=3 per deal.
      Each AllC plays 2 other AllCs, 2 rounds -> 2*2*3 = 12.
    - AllC vs AllD (3*3=9 pairs): AllC gets S=0, AllD gets T=5.
      Each AllC plays 3 AllDs, 2 rounds -> 3*2*0 = 0.
      Each AllD plays 3 AllCs, 2 rounds -> 3*2*5 = 30.
    - AllD vs AllD (3 pairs): both get P=1.
      Each AllD plays 2 other AllDs, 2 rounds -> 2*2*1 = 4.
    Totals: each AllC = 12, each AllD = 30 + 4 = 34.
    """
    game = _make_game(
        [
            AlwaysCooperate, AlwaysCooperate, AlwaysCooperate,
            AlwaysDefect, AlwaysDefect, AlwaysDefect,
        ],
        rounds=2,
        seed=1,
    )
    game.play()

    collector = ScoreStatsCollector()
    collector.collect(game, _ctx(0, 0))
    m = collector.rows[0].metrics

    scores_expected = [12.0, 12.0, 12.0, 34.0, 34.0, 34.0]
    assert m["sum"] == float(sum(scores_expected))
    assert m["avg"] == statistics.fmean(scores_expected)
    assert m["max"] == 34.0
    # Rough monotonicity: high percentiles among defectors, low among cooperators.
    assert m["p95"] == pytest.approx(34.0)
    assert m["p5"] == pytest.approx(12.0)


# ---------------------------------------------------------------------------
# merge()
# ---------------------------------------------------------------------------


def test_merge_extends_rows():
    a = ScoreStatsCollector()
    b = ScoreStatsCollector()

    game = _make_game([AlwaysCooperate, AlwaysDefect], rounds=1, seed=1)
    game.play()

    a.collect(game, _ctx(0, 0))
    b.collect(game, _ctx(1, 1))
    b.collect(game, _ctx(2, 2))

    a.merge(b)

    assert [(r.i, r.j) for r in a.rows] == [(0, 0), (1, 1), (2, 2)]
    # b unchanged.
    assert [(r.i, r.j) for r in b.rows] == [(1, 1), (2, 2)]


def test_merge_type_error_on_wrong_class():
    from pd.collector import Collector

    class Other(Collector):
        def collect(self, game, context):
            pass

    a = ScoreStatsCollector()
    with pytest.raises(TypeError, match="can only merge with itself"):
        a.merge(Other())


# ---------------------------------------------------------------------------
# Integration: run() vs run_parallel() produce the same rows
# ---------------------------------------------------------------------------


def _build_noisy_grid(size: int, master_seed: int, rounds: int) -> list[list[tuple[Game, dict]]]:
    master = random.Random(master_seed)

    def build(i: int, j: int) -> Game:
        n_def = i
        p = 0.1 * j
        players = [
            RandomDefect(p=p, rng=random.Random(master.getrandbits(63)))
            for _ in range(n_def)
        ]
        players += [TitForTat() for _ in range(size - n_def)]
        return Game(
            deal_generator=StaticGenerator(CLASSIC),
            players=players,
            total_rounds=rounds,
            rng=random.Random(master.getrandbits(63)),
        )

    return [
        [
            (build(i, j), {"i": i, "j": j, "n_defect": i, "p": 0.1 * j})
            for j in range(size)
        ]
        for i in range(size)
    ]


def test_score_stats_collector_run_sequential_and_parallel_match():
    grid_seq = _build_noisy_grid(size=3, master_seed=11, rounds=15)
    grid_par = _build_noisy_grid(size=3, master_seed=11, rounds=15)

    seq = ScoreStatsCollector()
    par = ScoreStatsCollector()

    Multigame(grid_seq, seq).run()
    Multigame(grid_par, par).run_parallel(max_workers=2)

    seq_by_key = {(r.i, r.j): r.metrics for r in seq.rows}
    par_by_key = {(r.i, r.j): r.metrics for r in par.rows}

    assert set(seq_by_key) == set(par_by_key)
    assert len(seq_by_key) == 9
    for key in seq_by_key:
        for m in METRICS:
            assert seq_by_key[key][m] == pytest.approx(par_by_key[key][m])
