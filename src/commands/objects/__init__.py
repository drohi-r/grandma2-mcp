"""
Object Keywords for grandMA2 Command Builder

This module contains implementations of all grandMA2 Object Keywords.
Object Keywords are "nouns" in grandMA2 command syntax used to specify the objects to operate on.

According to the classification in grandMA2 User Manual section 10.1.2, Object Keywords are divided into:

Fixture/Channel related:
- fixture: Access fixtures using Fixture ID
- channel: Access fixtures using Channel ID

Group/Selection related:
- group: Select fixture groups

Preset related:
- preset: Select or apply presets
- preset_type: Call or select preset types

Cue/Sequence related:
- cue: Reference cues
- cue_part: Reference cue parts
- sequence: Reference sequences

Executor related:
- executor: Reference executors

Layout/View related:
- layout: Select layouts

DMX related:
- dmx: Reference DMX addresses
- dmx_universe: Reference DMX universes

Time related:
- timecode: Reference timecode shows
- timecode_slot: Reference timecode slots
- timer: Reference timers
"""

# Fixture/Channel related
# Attribute/Feature related
from .attributes import attribute, feature

# Cue/Sequence related
from .cues import cue, cue_part, sequence

# DMX related
from .dmx import dmx, dmx_universe

# Executor related
from .executors import executor
from .fixtures import channel, fixture

# Group/Selection related
from .groups import group

# Layout/View related
from .layouts import layout

# Preset related
from .presets import preset, preset_type

# Time related
from .time import timecode, timecode_slot, timer

__all__ = [
    # Fixture/Channel
    "fixture",
    "channel",
    # Group/Selection
    "group",
    # Preset
    "preset",
    "preset_type",
    # Attribute/Feature
    "attribute",
    "feature",
    # Cue/Sequence
    "cue",
    "cue_part",
    "sequence",
    # Executor
    "executor",
    # Layout/View
    "layout",
    # DMX
    "dmx",
    "dmx_universe",
    # Time
    "timecode",
    "timecode_slot",
    "timer",
]
