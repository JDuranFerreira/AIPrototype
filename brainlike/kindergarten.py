"""Compatibility shim.

The reading engine moved to reading.py, where it is the LANGUAGE region's engine
(words, sentence frames, reading stories). Import from .reading in new code; this
module only keeps older imports working.
"""
from .reading import *            # noqa: F401,F403
from .reading import Reading as Kindergarten   # old name
