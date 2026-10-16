"""
Video Editor
============
Hyperframe-based video editing system using FFmpeg and sound effects processing.

Entry point for the package.
"""

from .editor import VideoEditor
from .ffmpeg_engine import FFmpegEngine
from .hyperframe import (
    AudioEffect,
    AudioEffectType,
    Effect,
    FrameRange,
    Hyperframe,
    HyperframeMetadata,
    HyperframeSequence,
    Keyframe,
    MultiTrackTimeline,
    TimelineTrack,
    Transition,
    TransitionType,
)
from .sound_engine import SoundEngine

__all__ = [
    "VideoEditor",
    "FFmpegEngine",
    "SoundEngine",
    "Hyperframe",
    "HyperframeSequence",
    "HyperframeMetadata",
    "FrameRange",
    "Effect",
    "Transition",
    "TransitionType",
    "AudioEffect",
    "AudioEffectType",
    "Keyframe",
    "TimelineTrack",
    "MultiTrackTimeline",
]

__version__ = "0.1.0"