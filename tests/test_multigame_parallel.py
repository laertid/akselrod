"""Tests for Multigame.run_parallel and Collector.merge."""

from __future__ import annotations

import random

import pytest

from pd import (
    AlwaysCooperate,
    AlwaysDefect,
    ClassicAxelrodGenerator,
    Collector,
    Game,
    Multigame,
    RandomDefect,
    TitForTat,
)


# ---------------------------------------------------------------------------
# Module-scope collector classes.
#
# They must be defined at module scope (and picklable) so ProcessPoolExecutor
# workers can import them. Nested-in-function collector classes cannot be
# pickled and would fail under run_parallel.
# ---------------------------------------------------------------------------


class RowsCollector(Collector):
    """Records one dict per finished game; merges by list concatenation."""

    def __init__(self) -> None:
        self.rows: list[dict] = []

    def collect(self, game: Game, context: dict) -> None:
        scores = [p.total_score() for p in game.players]
        self.rows.append(
            {
                "i": context.get("i"),
                "j": context.get("j"),
                "sum": float(sum(scores)),
                "max": float(max(scores)),
            }
        )

    def merge(self, other: Collector) -> None:  # type: ignore[override]
        assert isinstance(other, RowsCollector)
        self.rows.extend(other.rows)


class NoMergeCollector(Collector):
    """Collector that intentionally does NOT override merge."""

    def __init__(self) -> None:
        self.count = 0

    def collect(self, game: Game, context: dict) -> None:
        self.count += 1


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_game(strategies: list, rounds: int, seed: int) -> Game:
    players = [cls() for cls in strategies]
    return Game(
        deal_generator=ClassicAxelrodGenerator(),
        players=players,
        total_rounds=rounds,
        rng=random.Random(seed),
    )


def _make_noisy_grid(size: int, master_seed: int, rounds: int) -> list[list[tuple[Game, dict]]]:
    """Small grid of mixed RandomDefect + TitForTat games. Deterministic
    given `master_seed`."""
    master = random.Random(master_seed)

    def build(i: int, j: int) -> Game:
        n_def = i
        n_tft = size - n_def
        p = 0.1 * j
        players = [
            RandomDefect(p=p, rng=random.Random(master.getrandbits(63)))
            for _ in range(n_def)
        ]
        players += [TitForTat() for _ in range(n_tft)]
        return Game(
            deal_generator=ClassicAxelrodGenerator(),
            players=players,
            total_rounds=rounds,
            rng=random.Random(master.getrandbits(63)),
        )

    return [
        [(build(i, j), {"i": i, "j": j}) for j in range(size)]
        for i in range(size)
    ]


# ---------------------------------------------------------------------------
# Collector.merge default
# ---------------------------------------------------------------------------


def test_default_merge_raises_not_implemented():
    a = NoMergeCollector()
    b = NoMergeCollector()
    with pytest.raises(NotImplementedError, match="does not implement merge"):
        a.merge(b)


def test_run_parallel_raises_when_collector_lacks_merge():
    grid = [
        [
            (_make_game([AlwaysCooperate, AlwaysDefect], 3, seed=1), {"i": 0, "j": 0}),
        ]
    ]
    with pytest.raises(NotImplementedError, match="does not implement merge"):
        Multigame(grid, NoMergeCollector()).run_parallel(max_workers=2)


# ---------------------------------------------------------------------------
# run_parallel: empty grid
# ---------------------------------------------------------------------------


def test_run_parallel_empty_grid_is_noop():
    collector = RowsCollector()
    Multigame([], collector).run_parallel(max_workers=2)
    assert collector.rows == []


# ---------------------------------------------------------------------------
# run_parallel: parity with sequential run
# ---------------------------------------------------------------------------


def test_run_parallel_matches_sequential_on_simple_grid():
    grid_seq = [
        [
            (_make_game([AlwaysCooperate, AlwaysDefect], 4, seed=1), {"i": 0, "j": 0}),
            (_make_game([TitForTat, AlwaysDefect], 4, seed=2), {"i": 0, "j": 1}),
        ],
        [
            (_make_game([AlwaysCooperate, AlwaysCooperate], 4, seed=3), {"i": 1, "j": 0}),
        ],
    ]
    grid_par = [
        [
            (_make_game([AlwaysCooperate, AlwaysDefect], 4, seed=1), {"i": 0, "j": 0}),
            (_make_game([TitForTat, AlwaysDefect], 4, seed=2), {"i": 0, "j": 1}),
        ],
        [
            (_make_game([AlwaysCooperate, AlwaysCooperate], 4, seed=3), {"i": 1, "j": 0}),
        ],
    ]

    seq = RowsCollector()
    par = RowsCollector()

    Multigame(grid_seq, seq).run()
    Multigame(grid_par, par).run_parallel(max_workers=2)

    seq_by_key = {(r["i"], r["j"]): r for r in seq.rows}
    par_by_key = {(r["i"], r["j"]): r for r in par.rows}

    assert set(seq_by_key) == set(par_by_key) == {(0, 0), (0, 1), (1, 0)}
    for key in seq_by_key:
        assert seq_by_key[key] == par_by_key[key]


def test_run_parallel_matches_sequential_on_noisy_grid():
    """Two independently-built grids with the same master seed and the
    same pool of RandomDefect players should produce identical metrics
    under sequential and parallel runs.

    Uses a small 4x4 grid of 8-player games to keep the test fast.
    """
    grid_seq = _make_noisy_grid(size=4, master_seed=7, rounds=20)
    grid_par = _make_noisy_grid(size=4, master_seed=7, rounds=20)

    seq = RowsCollector()
    par = RowsCollector()

    Multigame(grid_seq, seq).run()
    Multigame(grid_par, par).run_parallel(max_workers=2)

    seq_by_key = {(r["i"], r["j"]): r for r in seq.rows}
    par_by_key = {(r["i"], r["j"]): r for r in par.rows}

    assert set(seq_by_key) == set(par_by_key)
    assert len(seq_by_key) == 16
    for key, seq_row in seq_by_key.items():
        par_row = par_by_key[key]
        # Metrics come from the same deterministic play, so they must
        # match exactly (no floating-point tolerance needed for sum/max
        # of small integers derived from the payoff matrix).
        assert seq_row == par_row, f"mismatch at {key}: {seq_row} vs {par_row}"


# ---------------------------------------------------------------------------
# run_parallel: exception propagation
# ---------------------------------------------------------------------------


class RaisingCollector(Collector):
    """collect() raises for context with 'boom': True."""

    def __init__(self) -> None:
        self.rows: list[dict] = []

    def collect(self, game: Game, context: dict) -> None:
        if context.get("boom"):
            raise RuntimeError("boom")
        self.rows.append({"i": context.get("i"), "j": context.get("j")})

    def merge(self, other: Collector) -> None:  # type: ignore[override]
        assert isinstance(other, RaisingCollector)
        self.rows.extend(other.rows)


def test_run_parallel_propagates_worker_exception():
    grid = [
        [
            (_make_game([AlwaysCooperate, AlwaysDefect], 2, seed=1), {"i": 0, "j": 0}),
            (_make_game([AlwaysCooperate, AlwaysDefect], 2, seed=2), {"i": 0, "j": 1, "boom": True}),
            (_make_game([AlwaysCooperate, AlwaysDefect], 2, seed=3), {"i": 0, "j": 2}),
        ]
    ]

    with pytest.raises(RuntimeError, match="boom"):
        Multigame(grid, RaisingCollector()).run_parallel(max_workers=2)


def test_run_parallel_wraps_worker_traceback_with_context():
    """When a worker raises, the parent should see a RuntimeError whose
    message includes the offending context and the original exception's
    class name and traceback -- not a bare BrokenProcessPool.
    """
    grid = [
        [
            (_make_game([AlwaysCooperate, AlwaysDefect], 2, seed=1), {"i": 3, "j": 7, "boom": True}),
        ]
    ]

    with pytest.raises(RuntimeError) as exc_info:
        Multigame(grid, RaisingCollector()).run_parallel(max_workers=1)

    msg = str(exc_info.value)
    assert "worker crashed" in msg
    assert "'i': 3" in msg and "'j': 7" in msg
    assert "RuntimeError" in msg  # original exception class
    assert "boom" in msg  # original message


# ---------------------------------------------------------------------------
# run_parallel: mp_context and max_workers=1 fallback
# ---------------------------------------------------------------------------


def test_run_parallel_with_spawn_context():
    """Explicit mp_context='spawn' should work on all platforms and
    produce the same results as the default context.
    """
    grid = [
        [
            (_make_game([AlwaysCooperate, AlwaysDefect], 3, seed=1), {"i": 0, "j": 0}),
            (_make_game([TitForTat, AlwaysDefect], 3, seed=2), {"i": 0, "j": 1}),
        ],
    ]

    collector = RowsCollector()
    Multigame(grid, collector).run_parallel(max_workers=2, mp_context="spawn")

    keys = {(r["i"], r["j"]) for r in collector.rows}
    assert keys == {(0, 0), (0, 1)}


def test_run_parallel_single_worker():
    """max_workers=1 is the debugging fallback -- it should still work
    and produce the full result set.
    """
    grid = [
        [
            (_make_game([AlwaysCooperate, AlwaysDefect], 3, seed=1), {"i": 0, "j": 0}),
            (_make_game([TitForTat, AlwaysDefect], 3, seed=2), {"i": 0, "j": 1}),
            (_make_game([AlwaysCooperate, AlwaysCooperate], 3, seed=3), {"i": 0, "j": 2}),
        ],
    ]

    collector = RowsCollector()
    Multigame(grid, collector).run_parallel(max_workers=1)

    keys = {(r["i"], r["j"]) for r in collector.rows}
    assert keys == {(0, 0), (0, 1), (0, 2)}
