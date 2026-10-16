"""
Hyperframe System
=================
A class-based system for representing video as hyperframes — frames or frame ranges
with rich metadata, effects, transitions, and keyframe-aware data structures.
"""

from __future__ import annotations

import copy
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Protocol, Tuple


class FrameEffectType(str, Enum):
    """Types of effects that can be applied to a hyperframe or sequence."""

    COLOR_GRADE = "color_grade"
    BLUR = "blur"
    SPEED_CHANGE = "speed_change"
    ROTATION = "rotation"
    CROP = "crop"
    TEXT_OVERLAY = "text_overlay"
    WATERMARK = "watermark"
    CUSTOM = "custom"


class TransitionType(str, Enum):
    """Supported transition types between hyperframes."""

    CUT = "cut"
    FADE_IN = "fade_in"
    FADE_OUT = "fade_out"
    CROSSFADE = "crossfade"
    DISSOLVE = "dissolve"
    WIPE_LEFT = "wipe_left"
    WIPE_RIGHT = "wipe_right"
    WIPE_UP = "wipe_up"
    WIPE_DOWN = "wipe_down"
    SLIDE_LEFT = "slide_left"
    SLIDE_RIGHT = "slide_right"
    ZOOM_IN = "zoom_in"
    ZOOM_OUT = "zoom_out"
    CUSTOM = "custom"


class AudioEffectType(str, Enum):
    """Types of audio effects applicable to hyperframes."""

    VOLUME = "volume"
    FADE_IN = "fade_in"
    FADE_OUT = "fade_out"
    ECHO = "echo"
    REVERB = "reverb"
    PITCH_SHIFT = "pitch_shift"
    NORMALIZE = "normalize"
    COMPRESS = "compress"
    CUSTOM = "custom"


@dataclass
class FrameRange:
    """Represents a range of frames in the source media."""

    start_frame: int = 0
    end_frame: Optional[int] = None  # None means until end of source
    start_time: float = 0.0  # seconds
    end_time: Optional[float] = None  # seconds

    @property
    def duration(self) -> Optional[float]:
        """Get duration in seconds."""
        if self.end_time is not None:
            return self.end_time - self.start_time
        return None

    @property
    def frame_count(self) -> Optional[int]:
        """Get number of frames."""
        if self.end_frame is not None and self.start_frame is not None:
            return self.end_frame - self.start_frame
        return None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "start_frame": self.start_frame,
            "end_frame": self.end_frame,
            "start_time": self.start_time,
            "end_time": self.end_time,
        }


@dataclass
class Effect:
    """A single effect applied to a hyperframe or sequence."""

    type: str
    params: Dict[str, Any] = field(default_factory=dict)
    enabled: bool = True
    name: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.type,
            "params": self.params.copy(),
            "enabled": self.enabled,
            "name": self.name,
        }


@dataclass
class Transition:
    """A transition between two clips or hyperframes."""

    type: TransitionType = TransitionType.CUT
    duration: float = 0.0  # seconds
    params: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.type.value,
            "duration": self.duration,
            "params": self.params.copy(),
        }


@dataclass
class AudioEffect:
    """An audio effect applied to a hyperframe."""

    type: AudioEffectType
    params: Dict[str, Any] = field(default_factory=dict)
    enabled: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.type.value,
            "params": self.params.copy(),
            "enabled": self.enabled,
        }


@dataclass
class HyperframeMetadata:
    """Metadata attached to a hyperframe."""

    source_file: Optional[str] = None
    source_clip_name: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    notes: str = ""
    custom: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source_file": self.source_file,
            "source_clip_name": self.source_clip_name,
            "tags": self.tags.copy(),
            "notes": self.notes,
            "custom": self.custom.copy(),
        }


class Hyperframe:
    """
    Represents a segment of video with associated metadata, effects, and transitions.

    A hyperframe can represent a single frame, a range of frames from a source clip,
    or a composition of multiple sub-hyperframes.
    """

    def __init__(
        self,
        source: Optional[str] = None,
        frame_range: Optional[FrameRange] = None,
        effects: Optional[List[Effect]] = None,
        audio_effects: Optional[List[AudioEffect]] = None,
        metadata: Optional[HyperframeMetadata] = None,
        transition_in: Optional[Transition] = None,
        transition_out: Optional[Transition] = None,
        children: Optional[List[Hyperframe]] = None,
    ):
        self.id: str = uuid.uuid4().hex[:12]
        self.source = source
        self.frame_range = frame_range or FrameRange()
        self.effects = effects or []
        self.audio_effects = audio_effects or []
        self.metadata = metadata or HyperframeMetadata()
        self.transition_in = transition_in
        self.transition_out = transition_out
        self.children = children  # For compositions

    @property
    def duration(self) -> Optional[float]:
        """Get duration in seconds."""
        return self.frame_range.duration

    @property
    def is_composition(self) -> bool:
        """Whether this hyperframe is composed of child hyperframes."""
        return self.children is not None and len(self.children) > 0

    def add_effect(self, effect_type: str, **params: Any) -> Effect:
        """Add a video effect to this hyperframe."""
        effect = Effect(type=effect_type, params=params)
        self.effects.append(effect)
        return effect

    def add_audio_effect(
        self, effect_type: AudioEffectType, **params: Any
    ) -> AudioEffect:
        """Add an audio effect to this hyperframe."""
        effect = AudioEffect(type=effect_type, params=params)
        self.audio_effects.append(effect)
        return effect

    def set_transition_in(self, transition_type: TransitionType, duration: float = 0.0, **params: Any) -> None:
        """Set the incoming transition for this hyperframe."""
        self.transition_in = Transition(type=transition_type, duration=duration, params=params)

    def set_transition_out(self, transition_type: TransitionType, duration: float = 0.0, **params: Any) -> None:
        """Set the outgoing transition for this hyperframe."""
        self.transition_out = Transition(type=transition_type, duration=duration, params=params)

    def clone(self) -> Hyperframe:
        """Create a deep copy of this hyperframe."""
        return copy.deepcopy(self)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "source": self.source,
            "frame_range": self.frame_range.to_dict(),
            "effects": [e.to_dict() for e in self.effects],
            "audio_effects": [ae.to_dict() for ae in self.audio_effects],
            "metadata": self.metadata.to_dict(),
            "transition_in": self.transition_in.to_dict() if self.transition_in else None,
            "transition_out": self.transition_out.to_dict() if self.transition_out else None,
            "children": [c.to_dict() for c in self.children] if self.children else None,
        }

    def __repr__(self) -> str:
        src = self.metadata.source_clip_name or self.source or "?"
        dur = f"{self.duration:.2f}s" if self.duration else "?"
        return f"Hyperframe(id={self.id}, src={src}, dur={dur})"


class HyperframeSequence:
    """
    A timeline/sequence of hyperframes that can be manipulated.

    Represents an ordered collection of hyperframes forming a complete video
    timeline with support for insert, remove, reorder, split, and merge operations.
    """

    def __init__(self, name: str = "Untitled"):
        self.name = name
        self.frames: List[Hyperframe] = []
        self.global_effects: List[Effect] = []
        self.global_audio_effects: List[AudioEffect] = []
        self.fps: float = 30.0
        self.width: int = 1920
        self.height: int = 1080
        self.metadata: Dict[str, Any] = {}

    @property
    def total_duration(self) -> float:
        """Calculate total duration of all hyperframes including transitions."""
        total = 0.0
        for hf in self.frames:
            if hf.duration is not None:
                total += hf.duration
                # Account for transition overlaps
                if hf.transition_in and hf.transition_in.duration > 0:
                    pass  # Overlap is handled at render
        return total

    @property
    def count(self) -> int:
        return len(self.frames)

    def append(self, hyperframe: Hyperframe) -> None:
        """Add a hyperframe to the end of the sequence."""
        self.frames.append(hyperframe)

    def insert(self, index: int, hyperframe: Hyperframe) -> None:
        """Insert a hyperframe at the given index."""
        self.frames.insert(index, hyperframe)

    def remove(self, index: int) -> Optional[Hyperframe]:
        """Remove and return the hyperframe at the given index."""
        if 0 <= index < len(self.frames):
            return self.frames.pop(index)
        return None

    def remove_by_id(self, hf_id: str) -> Optional[Hyperframe]:
        """Remove a hyperframe by its ID."""
        for i, hf in enumerate(self.frames):
            if hf.id == hf_id:
                return self.frames.pop(i)
        return None

    def get(self, index: int) -> Optional[Hyperframe]:
        """Get hyperframe at index."""
        if 0 <= index < len(self.frames):
            return self.frames[index]
        return None

    def split(self, index: int, time_seconds: float) -> Tuple[Optional[Hyperframe], Optional[Hyperframe]]:
        """
        Split a hyperframe at the given time offset.
        Returns (left_part, right_part).
        """
        if index < 0 or index >= len(self.frames):
            return (None, None)

        hf = self.frames[index]
        if hf.frame_range.end_time is None or hf.frame_range.start_time is None:
            return (None, None)

        split_point = hf.frame_range.start_time + time_seconds
        if time_seconds <= 0 or split_point >= hf.frame_range.end_time:
            return (None, None)

        # Left part
        left = hf.clone()
        left.frame_range.end_time = split_point
        if hf.frame_range.start_frame is not None and hf.frame_range.end_frame is not None:
            mid_frame = hf.frame_range.start_frame + int(
                time_seconds * self.fps
            )
            left.frame_range.end_frame = mid_frame

        # Right part
        right = hf.clone()
        right.frame_range.start_time = split_point
        right.frame_range.start_frame = (
            left.frame_range.end_frame if left.frame_range.end_frame else None
        )
        right.transition_in = None  # Remove incoming transition from right part

        # Replace original with the two parts
        self.frames.pop(index)
        self.frames.insert(index, right)
        self.frames.insert(index, left)

        return (left, right)

    def reorder(self, from_index: int, to_index: int) -> None:
        """Move a hyperframe from one position to another."""
        if (
            from_index < 0 or from_index >= len(self.frames)
            or to_index < 0 or to_index >= len(self.frames)
        ):
            return
        hf = self.frames.pop(from_index)
        self.frames.insert(to_index, hf)

    def add_global_effect(self, effect_type: str, **params: Any) -> Effect:
        """Add a global effect applied to the entire sequence."""
        effect = Effect(type=effect_type, params=params)
        self.global_effects.append(effect)
        return effect

    def add_global_audio_effect(self, effect_type: AudioEffectType, **params: Any) -> AudioEffect:
        """Add a global audio effect applied to the entire sequence."""
        effect = AudioEffect(type=effect_type, params=params)
        self.global_audio_effects.append(effect)
        return effect

    def clear(self) -> None:
        """Remove all hyperframes from the sequence."""
        self.frames.clear()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "fps": self.fps,
            "width": self.width,
            "height": self.height,
            "frames": [hf.to_dict() for hf in self.frames],
            "global_effects": [e.to_dict() for e in self.global_effects],
            "global_audio_effects": [ae.to_dict() for ae in self.global_audio_effects],
            "metadata": self.metadata,
        }

    def __repr__(self) -> str:
        return f"HyperframeSequence(name='{self.name}', clips={self.count}, duration={self.total_duration:.2f}s)"

    def __getitem__(self, index: int) -> Hyperframe:
        return self.frames[index]

    def __len__(self) -> int:
        return len(self.frames)

    def __iter__(self):
        return iter(self.frames)


class Keyframe:
    """
    Represents a keyframe — a specific point in the timeline with defined
    property values for interpolation.
    """

    def __init__(
        self,
        time: float,
        properties: Dict[str, Any],
        interpolation: str = "linear",
    ):
        self.time = time
        self.properties = properties.copy()
        self.interpolation = interpolation  # linear, ease_in, ease_out, ease_in_out, step

    def to_dict(self) -> Dict[str, Any]:
        return {
            "time": self.time,
            "properties": self.properties.copy(),
            "interpolation": self.interpolation,
        }

    def __repr__(self) -> str:
        return f"Keyframe(time={self.time:.2f}s, props={list(self.properties.keys())})"


class TimelineTrack:
    """
    A track on the timeline containing hyperframes, parallel to other tracks.
    Useful for picture-in-picture, overlay, multi-track audio, etc.
    """

    def __init__(self, name: str = "Track", track_type: str = "video", index: int = 0):
        self.name = name
        self.track_type = track_type  # video, audio, overlay, text
        self.index = index
        self.frames: List[Hyperframe] = []
        self.keyframes: List[Keyframe] = []
        self.muted: bool = False
        self.visible: bool = True
        self.opacity: float = 1.0

    def add(self, hyperframe: Hyperframe) -> None:
        self.frames.append(hyperframe)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "track_type": self.track_type,
            "index": self.index,
            "frames": [hf.to_dict() for hf in self.frames],
            "keyframes": [kf.to_dict() for kf in self.keyframes],
            "muted": self.muted,
            "visible": self.visible,
            "opacity": self.opacity,
        }

    def __repr__(self) -> str:
        return f"TimelineTrack(name='{self.name}', type={self.track_type}, clips={len(self.frames)})"


class MultiTrackTimeline:
    """
    A full multi-track timeline supporting parallel tracks for video, audio,
    overlays, and text.
    """

    def __init__(self, name: str = "Timeline"):
        self.name = name
        self.tracks: List[TimelineTrack] = []
        self.fps: float = 30.0
        self.width: int = 1920
        self.height: int = 1080

    def add_track(self, track: TimelineTrack) -> None:
        track.index = len(self.tracks)
        self.tracks.append(track)

    def get_track(self, index: int) -> Optional[TimelineTrack]:
        if 0 <= index < len(self.tracks):
            return self.tracks[index]
        return None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "fps": self.fps,
            "width": self.width,
            "height": self.height,
            "tracks": [t.to_dict() for t in self.tracks],
        }

    def __repr__(self) -> str:
        return f"MultiTrackTimeline(name='{self.name}', tracks={len(self.tracks)})"