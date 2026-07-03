# Prisoner's Dilemma

Reproducible framework for iterated prisoner's dilemma tournaments in the
spirit of Axelrod, built for flexible experimentation with payoffs, rules,
and strategies.

## Layout

```
src/pd/
  rng.py                 global reproducible RNG (set_seed / global_rng / create_rng)
  deal.py                Deal, Action, DealPayoff (8-number asymmetric matrix)
  deal_generator.py      DealGenerator (abstract base only)
  deal_generators/       concrete DealGenerator implementations
    classic_axelrod.py     ClassicAxelrodGenerator
  player.py              Player (abstract base only)
  players/               concrete Player implementations
    always_cooperate.py    AlwaysCooperate
  game.py                Game: turn-based tournament orchestrator
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
  per round via the global RNG. Players never play themselves.
- **Reproducibility.** All randomness must go through `get_rng()`. Call
  `set_seed(seed)` once at the start of a run.
- **History as raw Python.** `Game.history` is a `list[Deal]`; each `Deal`
  keeps players, payoff, actions, scores, and round index. Convert to a
  DataFrame later if needed.

## Run

```bash
cd prisoner_dilemma
pip install -e .
pytest
python examples/run_all_cooperate.py
```
