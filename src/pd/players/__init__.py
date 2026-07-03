"""Concrete Player implementations.

Import strategies from here, e.g.:

    from pd.players import AlwaysCooperate

New strategies go in their own module in this package and get re-exported
below.
"""

from pd.players.always_cooperate import AlwaysCooperate

__all__ = ["AlwaysCooperate"]
