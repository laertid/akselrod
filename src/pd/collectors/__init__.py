"""Concrete Collector implementations.

Import collectors from here, e.g.:

    from pd.collectors import ScoreStatsCollector

New collectors go in their own module in this package and get re-exported
below. Placing them at module scope (rather than defining them inline in
notebooks) is a prerequisite for using them with
`Multigame.run_parallel(...)`, because worker processes need to be able
to pickle-import the collector class.
"""

from pd.collectors.score_stats import ScoreStatsCollector, GameStats

__all__ = ["ScoreStatsCollector", "GameStats"]
