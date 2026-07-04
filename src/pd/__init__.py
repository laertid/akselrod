"""Prisoner's Dilemma tournament framework."""

from pd.deal import Deal, Action, DealPayoff
from pd.deal_generator import DealGenerator
from pd.deal_generators import ClassicAxelrodGenerator, StaticGenerator
from pd.player import Player
from pd.players import (
    AlwaysCooperate,
    AlwaysDefect,
    RandomDefect,
    RandomDefectTft,
    TitForTat,
)
from pd.game import Game
from pd.collector import Collector
from pd.multigame import Multigame

__all__ = [
    "Deal",
    "Action",
    "DealPayoff",
    "DealGenerator",
    "ClassicAxelrodGenerator",
    "StaticGenerator",
    "Player",
    "AlwaysCooperate",
    "AlwaysDefect",
    "RandomDefect",
    "RandomDefectTft",
    "TitForTat",
    "Game",
    "Collector",
    "Multigame",
]
