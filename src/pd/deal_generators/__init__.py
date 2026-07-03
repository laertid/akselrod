"""Concrete DealGenerator implementations.

Import generators from here, e.g.:

    from pd.deal_generators import ClassicAxelrodGenerator

New generators go in their own module in this package and get re-exported
below.
"""

from pd.deal_generators.classic_axelrod import ClassicAxelrodGenerator

__all__ = ["ClassicAxelrodGenerator"]
