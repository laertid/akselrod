# Prisoner's Dilemma

Reproducible framework for iterated prisoner's dilemma tournaments in the
spirit of Axelrod, built for flexible experimentation with payoffs, rules,
and strategies.

## Layout

```
src/pd/
  deal.py                Deal, Action, DealPayoff (8-number asymmetric matrix)
  deal_generator.py      DealGenerator (abstract base only)
  deal_generators/       concrete DealGenerator implementations
    classic_axelrod.py     ClassicAxelrodGenerator
  player.py              Player (abstract base only)
  players/               concrete Player implementations
    always_cooperate.py    AlwaysCooperate
  game.py                Game: turn-based tournament orchestrator (owns rng)
tests/                   pytest smoke tests (Python 3.12+)
examples/                runnable examples
```

New strategies and deal generators go in their own module inside
`pd/players/` or `pd/deal_generators/` and are re-exported from the
package `__init__.py`.

## Design notes

- **Simultaneous choice.** `Deal.execute()` calls both players' `do_deal`
  before writing anything to either history, so neither player can peek at
  the other's current-deal action.
- **Full information for players.** Each player is bound to the game
  (`self.game`), knows its `player_id`, receives the opponent object (not
  just its id) and the current `round_index`, and stores its own history
  both chronologically and per opponent. Strategies that "don't use
  reputation" are just strategies that ignore the opponent's history.
- **Turn-based rounds.** In each of `total_rounds` rounds, every unordered
  pair of distinct players plays exactly one deal; pair order is shuffled
  per round via `Game.rng`. Players never play themselves.
- **Reproducibility.** `Game` is constructed with an explicit
  `random.Random(seed)` and exposes it as `self.rng`. Players that need
  their own random stream take a separate `random.Random(...)` in their
  constructor. There is no global RNG state.
- **History as raw Python.** `Game.history` is a `list[Deal]`; each `Deal`
  keeps players, payoff, actions, scores, and round index. Convert to a
  DataFrame later if needed.

## Run

```bash
cd akselrod
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
pytest
python examples/run_all_cooperate.py
```

## Notebooks

Experiments live in `notebooks/`. The template `experiment_template.ipynb`
shows a full run: config -> game -> cumulative-score multiline chart ->
dual-axis score-vs-cooperation chart -> pairwise heatmap.

One-shot setup after cloning (inside an activated venv):

```bash
scripts/setup_dev.sh
```

This installs the package with dev extras (JupyterLab, matplotlib, numpy,
nbstripout), registers a Jupyter kernel named `pd`, and installs the
[`nbstripout`](https://github.com/kynan/nbstripout) git filter so notebook
outputs are stripped from every commit automatically. `.gitattributes`
already declares the filter, so once `setup_dev.sh` has run, diffs and
commits stay clean.

Start JupyterLab:

```bash
jupyter lab notebooks/experiment_template.ipynb
```

Edits in `src/pd/` are picked up live because the template loads
`autoreload` — no kernel restart needed.

### Scratch work

The `junk/` directory is gitignored (except for the `.gitkeep` placeholder).
Use it for throwaway notebooks, quick scripts, or one-off data dumps that
shouldn't hit git.
