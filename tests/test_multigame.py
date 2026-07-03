"""Tests for Collector + Multigame."""

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
    TitForTat,
)


class _RecordingCollector(Collector):
    """Collects (context, scores_dict, history_len) for every game."""

    def __init__(self) -> None:
        self.rows: list[dict] = []

    def collect(self, game: Game, context: dict) -> None:
        self.rows.append(
            {
                "context": context,
                "scores": game.scores(),
                "history_len": len(game.history),
            }
        )


def _make_game(strategies: list, rounds: int, seed: int) -> Game:
    players = [cls() for cls in strategies]
    return Game(
        deal_generator=ClassicAxelrodGenerator(),
        players=players,
        total_rounds=rounds,
        rng=random.Random(seed),
    )


# ---------------------------------------------------------------------------
# Collector abstract base
# ---------------------------------------------------------------------------


def test_collector_is_abstract():
    with pytest.raises(TypeError):
        Collector()  # type: ignore[abstract]


def test_collector_subclass_must_implement_collect():
    class Empty(Collector):
        pass

    with pytest.raises(TypeError):
        Empty()  # type: ignore[abstract]


# ---------------------------------------------------------------------------
# Multigame: basic behavior
# ---------------------------------------------------------------------------


def test_multigame_calls_collect_once_per_cell_row_major():
    collector = _RecordingCollector()

    grid = [
        [
            (_make_game([AlwaysCooperate, AlwaysCooperate], 3, seed=1), {"cell": (0, 0)}),
            (_make_game([AlwaysCooperate, AlwaysDefect], 3, seed=2), {"cell": (0, 1)}),
        ],
        [
            (_make_game([TitForTat, AlwaysDefect], 3, seed=3), {"cell": (1, 0)}),
        ],
    ]

    Multigame(grid, collector).run()

    # 3 cells total, in row-major order.
    assert [row["context"]["cell"] for row in collector.rows] == [
        (0, 0),
        (0, 1),
        (1, 0),
    ]


def test_multigame_plays_each_game_before_collecting():
    """collect must see a fully-played game (history populated)."""

    class HistoryCheckingCollector(Collector):
        def __init__(self) -> None:
            self.observed_history_lens: list[int] = []

        def collect(self, game: Game, context: dict) -> None:
            self.observed_history_lens.append(len(game.history))

    collector = HistoryCheckingCollector()

    grid = [
        [
            (_make_game([AlwaysCooperate, AlwaysCooperate], 5, seed=1), {}),
            (_make_game([AlwaysCooperate, AlwaysCooperate], 7, seed=1), {}),
        ]
    ]

    Multigame(grid, collector).run()

    # 2 players -> 1 pair -> total_rounds deals per game.
    assert collector.observed_history_lens == [5, 7]


def test_multigame_run_returns_none():
    collector = _RecordingCollector()
    grid = [[(_make_game([AlwaysCooperate, AlwaysDefect], 2, seed=1), {"i": 0})]]
    result = Multigame(grid, collector).run()
    assert result is None


def test_multigame_forwards_context_by_reference():
    """The context dict handed to collect is the same object the caller
    passed in -- no copying, no rewriting."""
    collector = _RecordingCollector()
    ctx = {"tag": "alpha"}
    grid = [[(_make_game([AlwaysCooperate, AlwaysDefect], 1, seed=1), ctx)]]

    Multigame(grid, collector).run()

    assert collector.rows[0]["context"] is ctx


def test_multigame_does_not_touch_context():
    """Multigame does not inject i/j or any framework key into context."""
    collector = _RecordingCollector()
    ctx_a = {"only": "mine"}
    ctx_b = {"only": "mine-too"}
    grid = [
        [
            (_make_game([AlwaysCooperate, AlwaysDefect], 1, seed=1), ctx_a),
        ],
        [
            (_make_game([AlwaysCooperate, AlwaysDefect], 1, seed=2), ctx_b),
        ],
    ]

    Multigame(grid, collector).run()

    assert ctx_a == {"only": "mine"}
    assert ctx_b == {"only": "mine-too"}


def test_multigame_handles_empty_grid():
    collector = _RecordingCollector()
    Multigame([], collector).run()
    assert collector.rows == []


def test_multigame_handles_ragged_rows():
    """Rows of different lengths are fine -- 2D is just a grouping."""
    collector = _RecordingCollector()

    grid = [
        [
            (_make_game([AlwaysCooperate, AlwaysDefect], 1, seed=1), {"c": "0,0"}),
            (_make_game([AlwaysCooperate, AlwaysDefect], 1, seed=2), {"c": "0,1"}),
            (_make_game([AlwaysCooperate, AlwaysDefect], 1, seed=3), {"c": "0,2"}),
        ],
        [],  # empty row -- skipped
        [
            (_make_game([AlwaysCooperate, AlwaysDefect], 1, seed=4), {"c": "2,0"}),
        ],
    ]

    Multigame(grid, collector).run()

    assert [row["context"]["c"] for row in collector.rows] == [
        "0,0",
        "0,1",
        "0,2",
        "2,0",
    ]


def test_multigame_snapshots_grid_shape():
    """Mutating the caller's outer or inner lists after construction must
    not change what Multigame runs -- both levels are shallow-copied."""
    collector = _RecordingCollector()

    row0 = [(_make_game([AlwaysCooperate, AlwaysDefect], 1, seed=1), {"c": "0,0"})]
    grid = [row0]

    mg = Multigame(grid, collector)
    # Post-construction mutations at both levels -- Multigame ignores both.
    grid.append([(_make_game([AlwaysCooperate, AlwaysDefect], 1, seed=99), {"c": "late-outer"})])
    row0.append((_make_game([AlwaysCooperate, AlwaysDefect], 1, seed=98), {"c": "late-inner"}))

    mg.run()

    contexts = [row["context"]["c"] for row in collector.rows]
    assert contexts == ["0,0"]


# ---------------------------------------------------------------------------
# Multigame: propagation of exceptions
# ---------------------------------------------------------------------------


def test_multigame_propagates_collector_exceptions_and_stops():
    class Boom(Collector):
        def __init__(self) -> None:
            self.seen: list[dict] = []

        def collect(self, game: Game, context: dict) -> None:
            self.seen.append(context)
            if context.get("boom"):
                raise RuntimeError("nope")

    collector = Boom()

    grid = [
        [
            (_make_game([AlwaysCooperate, AlwaysDefect], 1, seed=1), {"c": "ok"}),
            (_make_game([AlwaysCooperate, AlwaysDefect], 1, seed=2), {"c": "boom", "boom": True}),
            (_make_game([AlwaysCooperate, AlwaysDefect], 1, seed=3), {"c": "never"}),
        ]
    ]

    with pytest.raises(RuntimeError, match="nope"):
        Multigame(grid, collector).run()

    # First two cells were visited; the third was never played.
    assert [ctx["c"] for ctx in collector.seen] == ["ok", "boom"]


# ---------------------------------------------------------------------------
# End-to-end: a realistic scoreboard collector
# ---------------------------------------------------------------------------


class _ScoreboardCollector(Collector):
    """Groups scores by a caller-provided 'label' key in context."""

    def __init__(self) -> None:
        self.by_label: dict[str, list[dict[int, float]]] = {}

    def collect(self, game: Game, context: dict) -> None:
        label = context["label"]
        self.by_label.setdefault(label, []).append(game.scores())


def test_multigame_end_to_end_scoreboard():
    collector = _ScoreboardCollector()

    # Two independent groups ("cooperators", "defector-mix") x two seeds.
    def coop_game(seed: int) -> Game:
        return _make_game([AlwaysCooperate, AlwaysCooperate], rounds=4, seed=seed)

    def mix_game(seed: int) -> Game:
        return _make_game([AlwaysCooperate, AlwaysDefect], rounds=4, seed=seed)

    grid = [
        [
            (coop_game(1), {"label": "cooperators", "seed": 1}),
            (coop_game(2), {"label": "cooperators", "seed": 2}),
        ],
        [
            (mix_game(1), {"label": "defector-mix", "seed": 1}),
            (mix_game(2), {"label": "defector-mix", "seed": 2}),
        ],
    ]

    Multigame(grid, collector).run()

    assert set(collector.by_label.keys()) == {"cooperators", "defector-mix"}
    assert len(collector.by_label["cooperators"]) == 2
    assert len(collector.by_label["defector-mix"]) == 2

    # ClassicAxelrod: R=3 per mutual cooperation, 4 rounds -> 12 each.
    for scores in collector.by_label["cooperators"]:
        assert scores == {0: 12.0, 1: 12.0}

    # AlwaysCooperate vs AlwaysDefect: S=0 for cooperator, T=5 for defector,
    # 4 rounds -> 0 and 20.
    for scores in collector.by_label["defector-mix"]:
        assert scores == {0: 0.0, 1: 20.0}
