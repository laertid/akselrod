"""Global reproducible random number generator.

Any code that needs randomness must call `global_rng()` instead of the stdlib
`random` module. Tests and experiments call `set_seed(seed)` once at start
to make the whole run deterministic.

Use `create_rng(seed)` when a component wants its own independent RNG (for
example, a player that wants a private stream so its randomness does not
interfere with the game's shuffling). Passing `seed=None` returns the shared
global RNG.
"""

import random

_rng: random.Random = random.Random()


def set_seed(seed: int) -> None:
    """Reset the global RNG to a deterministic state.

    Call this once at the start of an experiment. All players and generators
    that use `global_rng()` will then produce reproducible sequences.
    """
    global _rng
    _rng = random.Random(seed)


def global_rng() -> random.Random:
    """Return the global RNG instance.

    The instance itself is stable across calls until `set_seed()` is called.
    """
    return _rng


def create_rng(seed: str | None) -> random.Random:
    """Return an RNG.

    If `seed` is None, returns the shared global RNG (same instance as
    `global_rng()`). Otherwise returns a fresh, independent `random.Random`
    seeded with the given string.
    """
    if seed is None:
        return _rng
    return random.Random(seed)
