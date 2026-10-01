"""Explicit lifecycle registry; never dispatches agent operations."""
from . import siftr, pruner, test_filter

INSTALLERS = {"siftr-source-v1": siftr, "jev-pruner-source-v1": pruner, "jev-test-filter-source-v1": test_filter}
