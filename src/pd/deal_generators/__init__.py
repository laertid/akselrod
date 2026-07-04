"""Concrete DealGenerator implementations.

Import generators from here, e.g.:

    from pd.deal_generators import ClassicAxelrodGenerator

New generators go in their own module in this package and get re-exported
below.
"""

from pd.deal_generators.classic_axelrod import ClassicAxelrodGenerator
from pd.deal_generators.static import StaticGenerator

__all__ = ["ClassicAxelrodGenerator", "StaticGenerator"]
