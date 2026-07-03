"""Concrete Player implementations.

Import strategies from here, e.g.:

    from pd.players import AlwaysCooperate

New strategies go in their own module in this package and get re-exported
below.
"""

from pd.players.always_cooperate import AlwaysCooperate
from pd.players.tit_for_tat import TitForTat

__all__ = ["AlwaysCooperate", "TitForTat"]
