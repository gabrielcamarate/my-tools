"""Explicit registry: a catalog never chooses an arbitrary Python module."""
from . import siftr

ADAPTERS = {"siftr-v1": siftr}
