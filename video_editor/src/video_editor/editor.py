"""
Video Editor
============
High-level orchestrator that combines the hyperframe system, FFmpeg engine,
and sound effects engine into a unified video editing interface.
"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .ffmpeg_engine import FFmpegEngine
from .hyperframe import (
    AudioEffect,
    AudioEffectType,
    Effect,
    FrameRange,
    Hyperframe,
    HyperframeMetadata,
    HyperframeSequence,
    MultiTrackTimeline,
    TimelineTrack,
    Transition,
    TransitionType,
)
from .sound_engine import SoundEngine


class VideoEditor:
    """
    High-level video editor that ties together hyperframes, FFmpeg, and sound effects.

    Provides a simplified API for common editing operations:
      - Import media
      - Build timelines
      - Apply effects and transitions
      - Mix audio and apply sound effects
      - Export rendered video
    """

    def __init__(
        self,
        ffmpeg_path: Optional[str] = None,
        ffprobe_path: Optional[str] = None,
        temp_dir: Optional[str] = None,
    ):
        self.ffmpeg = FFmpegEngine(ffmpeg_path=ffmpeg_path, ffprobe_path=ffprobe_path)
        self.sound = SoundEngine()
        self.temp_dir = temp_dir or tempfile.mkdtemp(prefix="video_editor_")
        self.project_name: str = "Untitled Project"
        self.sequences: Dict[str, HyperframeSequence] = {}
        self.timelines: Dict[str, MultiTrackTimeline] = {}
        self.active_sequence: Optional[HyperframeSequence] = None
        self.active_timeline: Optional[MultiTrackTimeline] = None

    # ── Project Management ───────────────────────────────────────

    def new_project(self, name: str = "Untitled Project") -> None:
        """Create a new editing project."""
        self.project_name = name
        self.sequences = {}
        self.timelines = {}
        seq = HyperframeSequence(name="Main Sequence")
        self.sequences["main"] = seq
        self.active_sequence = seq

    def create_sequence(self, name: str, fps: float = 30.0, width: int = 1920, height: int = 1080) -> HyperframeSequence:
        """Create a new sequence."""
        seq = HyperframeSequence(name=name)
        seq.fps = fps
        seq.width = width
        seq.height = height
        self.sequences[name] = seq
        self.active_sequence = seq
        return seq

    # ── Import / Add Media ───────────────────────────────────────

    def import_clip(
        self,
        file_path: str,
        clip_name: Optional[str] = None,
        sequence_name: Optional[str] = None,
    ) -> Hyperframe:
        """
        Import a media file as a hyperframe and add it to a sequence.

        Args:
            file_path: Path to the media file
            clip_name: Optional friendly name for the clip
            sequence_name: Target sequence (defaults to active)

        Returns:
            The created Hyperframe
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")

        # Probe the file
        duration = self.ffmpeg.get_duration(file_path)
        width, height = 0, 0
        try:
            width, height = self.ffmpeg.get_resolution(file_path)
        except Exception:
            pass

        # Create hyperframe
        frame_range = FrameRange(
            start_frame=0,
            end_time=duration,
            start_time=0.0,
        )

        metadata = HyperframeMetadata(
            source_file=file_path,
            source_clip_name=clip_name or Path(file_path).stem,
            tags=["imported"],
        )

        hf = Hyperframe(
            source=file_path,
            frame_range=frame_range,
            metadata=metadata,
        )

        # Add to sequence
        seq = self._resolve_sequence(sequence_name)
        if seq:
            if width > 0 and height > 0:
                seq.width = max(seq.width, width)
                seq.height = max(seq.height, height)
            seq.append(hf)

        return hf

    def import_clips(self, file_paths: List[str], sequence_name: Optional[str] = None) -> List[Hyperframe]:
        """Import multiple media files."""
        return [self.import_clip(fp, sequence_name=sequence_name) for fp in file_paths]

    def add_to_timeline(
        self,
        file_path: str,
        track_index: int = 0,
        timeline_name: Optional[str] = None,
    ) -> Hyperframe:
        """Add a media file to a specific track in the timeline."""
        hf = self.import_clip(file_path)
        timeline = self._resolve_timeline(timeline_name)
        if timeline:
            track = timeline.get_track(track_index)
            if track is None:
                track = TimelineTrack(name=f"Track {track_index}", index=track_index)
                timeline.add_track(track)
            track.add(hf)
        return hf

    # ── Clips / Sequence Editing ─────────────────────────────────

    def trim_clip(
        self,
        sequence_name: str,
        clip_index: int,
        start_time: float,
        end_time: float,
    ) -> None:
        """Trim a clip in the sequence to a new start/end time."""
        seq = self.sequences.get(sequence_name)
        if not seq:
            raise ValueError(f"Sequence '{sequence_name}' not found")
        hf = seq.get(clip_index)
        if not hf:
            raise IndexError(f"Clip index {clip_index} out of range")
        hf.frame_range.start_time = start_time
        hf.frame_range.end_time = end_time

    def split_clip(self, sequence_name: str, clip_index: int, time_seconds: float) -> Tuple[Hyperframe, Hyperframe]:
        """Split a clip at a given time."""
        seq = self.sequences.get(sequence_name)
        if not seq:
            raise ValueError(f"Sequence '{sequence_name}' not found")
        left, right = seq.split(clip_index, time_seconds)
        if left is None or right is None:
            raise ValueError(f"Cannot split clip at time {time_seconds}s")
        return left, right

    def remove_clip(self, sequence_name: str, clip_index: int) -> None:
        """Remove a clip from the sequence."""
        seq = self.sequences.get(sequence_name)
        if not seq:
            raise ValueError(f"Sequence '{sequence_name}' not found")
        seq.remove(clip_index)

    def reorder_clip(self, sequence_name: str, from_index: int, to_index: int) -> None:
        """Reorder a clip in the sequence."""
        seq = self.sequences.get(sequence_name)
        if not seq:
            raise ValueError(f"Sequence '{sequence_name}' not found")
        seq.reorder(from_index, to_index)

    # ── Effects ──────────────────────────────────────────────────

    def add_video_effect(
        self,
        sequence_name: str,
        clip_index: int,
        effect_type: str,
        **params: Any,
    ) -> Effect:
        """Add a video effect to a specific clip."""
        seq = self._get_sequence(sequence_name)
        hf = seq.get(clip_index)
        if not hf:
            raise IndexError(f"Clip index {clip_index} out of range")
        return hf.add_effect(effect_type, **params)

    def add_audio_effect(
        self,
        sequence_name: str,
        clip_index: int,
        effect_type: AudioEffectType,
        **params: Any,
    ) -> AudioEffect:
        """Add an audio effect to a specific clip."""
        seq = self._get_sequence(sequence_name)
        hf = seq.get(clip_index)
        if not hf:
            raise IndexError(f"Clip index {clip_index} out of range")
        return hf.add_audio_effect(effect_type, **params)

    def add_global_audio_effect(
        self,
        sequence_name: str,
        effect_type: AudioEffectType,
        **params: Any,
    ) -> AudioEffect:
        """Add a global audio effect to the entire sequence."""
        seq = self._get_sequence(sequence_name)
        return seq.add_global_audio_effect(effect_type, **params)

    # ── Transitions ──────────────────────────────────────────────

    def set_transition(
        self,
        sequence_name: str,
        clip_index: int,
        transition_type: TransitionType,
        duration: float = 1.0,
        side: str = "in",
        **params: Any,
    ) -> None:
        """
        Set a transition for a clip.

        Args:
            sequence_name: Name of the sequence
            clip_index: Index of the clip
            transition_type: Type of transition
            duration: Duration in seconds
            side: 'in' for incoming, 'out' for outgoing transition
        """
        seq = self._get_sequence(sequence_name)
        hf = seq.get(clip_index)
        if not hf:
            raise IndexError(f"Clip index {clip_index} out of range")

        trans = Transition(type=transition_type, duration=duration, params=params)
        if side == "in":
            hf.transition_in = trans
        else:
            hf.transition_out = trans

    # ── Sound Effects ────────────────────────────────────────────

    def apply_sound_effect_to_clip(
        self,
        sequence_name: str,
        clip_index: int,
        effect: AudioEffect,
    ) -> None:
        """Apply a sound effect to a specific clip (registers it for render)."""
        seq = self._get_sequence(sequence_name)
        hf = seq.get(clip_index)
        if not hf:
            raise IndexError(f"Clip index {clip_index} out of range")
        hf.audio_effects.append(effect)

    def generate_sound_effect(
        self,
        output_path: str,
        effect_type: str = "tone",
        frequency: float = 440.0,
        duration_ms: float = 1000.0,
        volume_db: float = -10.0,
        **kwargs: Any,
    ) -> str:
        """
        Generate and save a synthesized sound effect.

        Args:
            output_path: Where to save the generated sound
            effect_type: 'tone', 'noise', 'sweep', 'silence'
            frequency: Frequency in Hz (for tone/sweep)
            duration_ms: Duration in milliseconds
            volume_db: Volume in dBFS

        Returns:
            Path to the generated file
        """
        if effect_type == "tone":
            audio = self.sound.generate_tone(frequency, duration_ms, volume_db)
        elif effect_type == "noise":
            audio = self.sound.generate_noise(duration_ms, volume_db)
        elif effect_type == "silence":
            audio = self.sound.generate_silence(duration_ms)
        else:
            audio = self.sound.generate_tone(frequency, duration_ms, volume_db)

        return self.sound.save(audio, output_path)

    # ── Export / Render ──────────────────────────────────────────

    def export_sequence(
        self,
        output_path: str,
        sequence_name: str = "main",
        preset: str = "medium",
        crf: int = 23,
        codec: str = "libx264",
    ) -> str:
        """
        Export a sequence to a video file.

        Args:
            output_path: Output file path
            sequence_name: Name of the sequence to render
            preset: x264 preset
            crf: Quality (0-51, lower = better)
            codec: Video codec

        Returns:
            Path to rendered video
        """
        seq = self._get_sequence(sequence_name)
        return self.ffmpeg.render_sequence(
            seq,
            output_path,
            temp_dir=self.temp_dir,
            preset=preset,
            crf=crf,
            codec=codec,
        )

    def export_with_audio_effects(
        self,
        input_path: str,
        output_path: str,
        effects: List[AudioEffect],
    ) -> str:
        """
        Apply audio effects to a video file and export.

        Extracts audio, processes with pydub, then re-muxes with video.
        """
        # Extract audio
        temp_audio = os.path.join(self.temp_dir, "temp_audio.wav")
        if os.path.exists(temp_audio):
            os.unlink(temp_audio)
        self.ffmpeg.extract_audio(input_path, temp_audio)

        # Apply sound effects
        audio = self.sound.load(temp_audio)
        audio = self.sound.apply_effects(audio, effects)

        # Save processed audio
        processed_audio = os.path.join(self.temp_dir, "processed_audio.wav")
        self.sound.save(audio, processed_audio)

        # Re-mux
        return self.ffmpeg.add_audio_track(input_path, processed_audio, output_path, volume=1.0, mix=False)

    def export_audio(
        self,
        output_path: str,
        source_path: Optional[str] = None,
        effects: Optional[List[AudioEffect]] = None,
        sequence_name: Optional[str] = None,
    ) -> str:
        """
        Export audio from a video file or sequence.

        Args:
            output_path: Output audio file path
            source_path: Input video file (if exporting from single file)
            effects: Optional audio effects to apply
            sequence_name: Sequence name to export audio from

        Returns:
            Path to exported audio
        """
        if source_path:
            audio_path = self.ffmpeg.extract_audio(source_path, output_path)
            if effects:
                audio = self.sound.load(audio_path)
                audio = self.sound.apply_effects(audio, effects)
                self.sound.save(audio, audio_path)
            return audio_path

        if sequence_name:
            # Render sequence to temp video, then extract audio
            temp_video = os.path.join(self.temp_dir, "temp_render.mp4")
            self.export_sequence(temp_video, sequence_name=sequence_name)
            return self.ffmpeg.extract_audio(temp_video, output_path)

        raise ValueError("Either source_path or sequence_name is required")

    # ── Info / Probe ─────────────────────────────────────────────

    def probe_file(self, file_path: str) -> Dict[str, Any]:
        """Probe a media file and return metadata."""
        duration = self.ffmpeg.get_duration(file_path)
        info = {"file": file_path, "duration": duration}

        try:
            width, height = self.ffmpeg.get_resolution(file_path)
            info["width"] = width
            info["height"] = height
        except Exception:
            pass

        try:
            info["fps"] = self.ffmpeg.get_fps(file_path)
        except Exception:
            pass

        info["streams"] = self.ffmpeg.probe(file_path).get("streams", [])
        return info

    # ── Save / Load Project ──────────────────────────────────────

    def save_project(self, file_path: str) -> str:
        """Save the project to a JSON file."""
        project_data = {
            "name": self.project_name,
            "sequences": {name: seq.to_dict() for name, seq in self.sequences.items()},
            "timelines": {
                name: tl.to_dict() for name, tl in self.timelines.items()
            },
        }
        with open(file_path, "w") as f:
            json.dump(project_data, f, indent=2)
        return file_path

    def load_project(self, file_path: str) -> None:
        """Load a project from a JSON file."""
        # Simplified loader — reconstructs hyperframe structure
        with open(file_path) as f:
            data = json.load(f)

        self.project_name = data.get("name", "Loaded Project")
        self.sequences = {}
        self.timelines = {}

        for seq_name, seq_data in data.get("sequences", {}).items():
            seq = HyperframeSequence(name=seq_name)
            seq.fps = seq_data.get("fps", 30.0)
            seq.width = seq_data.get("width", 1920)
            seq.height = seq_data.get("height", 1080)

            for hf_data in seq_data.get("frames", []):
                hf = self._hyperframe_from_dict(hf_data)
                seq.frames.append(hf)

            self.sequences[seq_name] = seq

        self.active_sequence = self.sequences.get("main")

    # ── Internal Helpers ─────────────────────────────────────────

    def _resolve_sequence(self, name: Optional[str] = None) -> Optional[HyperframeSequence]:
        if name:
            return self.sequences.get(name)
        return self.active_sequence

    def _resolve_timeline(self, name: Optional[str] = None) -> Optional[MultiTrackTimeline]:
        if name:
            return self.timelines.get(name)
        if not self.active_timeline and "main" in self.timelines:
            self.active_timeline = self.timelines["main"]
        return self.active_timeline

    def _get_sequence(self, name: str) -> HyperframeSequence:
        seq = self.sequences.get(name)
        if not seq:
            raise ValueError(f"Sequence '{name}' not found. Available: {list(self.sequences.keys())}")
        return seq

    def _hyperframe_from_dict(self, data: Dict[str, Any]) -> Hyperframe:
        """Reconstruct a Hyperframe from a dictionary."""
        fr_data = data.get("frame_range", {})
        frame_range = FrameRange(
            start_frame=fr_data.get("start_frame", 0),
            end_frame=fr_data.get("end_frame"),
            start_time=fr_data.get("start_time", 0.0),
            end_time=fr_data.get("end_time"),
        )

        meta_data = data.get("metadata", {})
        metadata = HyperframeMetadata(
            source_file=meta_data.get("source_file"),
            source_clip_name=meta_data.get("source_clip_name"),
            tags=meta_data.get("tags", []),
            notes=meta_data.get("notes", ""),
            custom=meta_data.get("custom", {}),
        )

        hf = Hyperframe(
            source=data.get("source"),
            frame_range=frame_range,
            metadata=metadata,
        )
        hf.id = data.get("id", hf.id)

        for eff_data in data.get("effects", []):
            hf.effects.append(Effect(
                type=eff_data.get("type", ""),
                params=eff_data.get("params", {}),
                enabled=eff_data.get("enabled", True),
            ))

        for ae_data in data.get("audio_effects", []):
            hf.audio_effects.append(AudioEffect(
                type=AudioEffectType(ae_data.get("type", "volume")),
                params=ae_data.get("params", {}),
                enabled=ae_data.get("enabled", True),
            ))

        return hf