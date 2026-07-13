"""Evidence layer: bundle writer and failure register. Imports contracts only."""
from .bundle import build_register, write_bundle

__all__ = ["build_register", "write_bundle"]
