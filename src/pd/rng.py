"""Global reproducible random number generator.

Any code that needs randomness must call `get_rng()` instead of the stdlib
`random` module. Tests and experiments call `set_seed(seed)` once at start
to make the whole run deterministic.
"""

import random

_rng: random.Random = random.Random()


def set_seed(seed: int) -> None:
    """Reset the global RNG to a deterministic state.

    Call this once at the start of an experiment. All players and generators
    that use `get_rng()` will then produce reproducible sequences.
    """
    global _rng
    _rng = random.Random(seed)


def get_rng() -> random.Random:
    """Return the global RNG instance.

    The instance itself is stable across calls until `set_seed()` is called.
    """
    return _rng
