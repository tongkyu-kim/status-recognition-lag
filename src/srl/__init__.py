"""Research code for *Status Proximity and Recognition Lag in Changing Economic Hierarchies*.

Import name ``srl`` (status-recognition-lag). Subpackages:

- ``acquisition``  source registry and raw-file inventory (no automated downloading)
- ``cleaning``     source-specific tables -> canonical schemas
- ``trade``        interdependence and competitive-overlap measures
- ``status``       objective status and status-proximity measures
- ``text``         language handling, entity matching, segmentation, corpus assembly
- ``attention``    government-attention measures
- ``recognition``  recognition frames, indices, validation and recognition-lag variants
- ``panel``        partner-year panel assembly
- ``models``       econometric specifications and estimation
- ``figures``      figure styling and export
- ``utils``        configuration, paths, I/O guards, logging, validation, seeds
"""

__version__ = "0.1.0"
