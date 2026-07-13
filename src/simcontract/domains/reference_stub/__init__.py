"""reference_stub: Layer-1 contract testbed (spec 7.0). NOT a research model."""
from .adapter import ReferenceStubAdapter, catalog, observation, schema
from .manifest import DOMAIN_ID, MANIFEST

__all__ = ["DOMAIN_ID", "MANIFEST", "ReferenceStubAdapter", "catalog",
           "observation", "schema"]
