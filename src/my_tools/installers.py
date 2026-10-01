"""Explicit lifecycle registry; never dispatches agent operations."""
from . import siftr, pruner

INSTALLERS = {"siftr-source-v1": siftr, "jev-pruner-source-v1": pruner}
