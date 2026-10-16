"""
FFmpeg Engine
=============
Wrapper around ffmpeg for video/audio encoding, decoding, filtering, and rendering.
Uses the ffmpeg-python library for programmatic FFmpeg control.
"""

from __future__ import annotations

import os
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import ffmpeg

from .hyperframe import (
    AudioEffect,
    AudioEffectType,
    Effect,
    Hyperframe,
    HyperframeSequence,
    Transition,
    TransitionType,
)


class FFmpegEngine:
    """
    High-level wrapper around FFmpeg for video processing operations.

    Handles probe, trim, cut, merge, transitions, filters, encoding, and export.
    """

    def __init__(self, ffmpeg_path: Optional[str] = None, ffprobe_path: Optional[str] = None):
        self.ffmpeg_path = ffmpeg_path or "ffmpeg"
        self.ffprobe_path = ffprobe_path or "ffprobe"
        self._check_ffmpeg()

    def _check_ffmpeg(self) -> None:
        """Verify FFmpeg is available."""
        try:
            subprocess.run(
                [self.ffmpeg_path, "-version"],
                capture_output=True,
                check=True,
            )
        except (subprocess.CalledProcessError, FileNotFoundError):
            raise RuntimeError(
                "FFmpeg not found. Please install FFmpeg and ensure it's in your PATH."
            )

    def probe(self, file_path: str) -> Dict[str, Any]:
        """Probe a media file and return its metadata."""
        try:
            probe = ffmpeg.probe(file_path, cmd=self.ffprobe_path)
            return probe
        except ffmpeg.Error as e:
            raise RuntimeError(f"Failed to probe {file_path}: {e.stderr.decode()}")

    def get_stream_info(self, file_path: str, stream_type: str = "video") -> Optional[Dict[str, Any]]:
        """Get info about a specific stream type from a media file."""
        probe = self.probe(file_path)
        for stream in probe.get("streams", []):
            if stream.get("codec_type") == stream_type:
                return stream
        return None

    def get_duration(self, file_path: str) -> float:
        """Get the duration of a media file in seconds."""
        info = self.get_stream_info(file_path, "video") or self.get_stream_info(file_path, "audio") or {}
        duration = info.get("duration") or "0"
        return float(duration)

    def get_resolution(self, file_path: str) -> Tuple[int, int]:
        """Get the resolution (width, height) of a video file."""
        info = self.get_stream_info(file_path, "video") or {}
        return (info.get("width", 0) or 0, info.get("height", 0) or 0)

    def get_fps(self, file_path: str) -> float:
        """Get the frame rate of a video file."""
        info = self.get_stream_info(file_path, "video") or {}
        r_frame_rate = info.get("r_frame_rate", "30/1") or "30/1"
        parts = r_frame_rate.split("/")
        if len(parts) == 2 and float(parts[1]) != 0:
            return float(parts[0]) / float(parts[1])
        return float(parts[0])

    def trim(
        self,
        input_path: str,
        output_path: str,
        start_time: float = 0.0,
        end_time: Optional[float] = None,
        duration: Optional[float] = None,
    ) -> str:
        """
        Trim a video/audio clip.

        Args:
            input_path: Source media file
            output_path: Destination file path
            start_time: Start time in seconds
            end_time: End time in seconds (optional)
            duration: Duration in seconds (optional, overrides end_time)

        Returns:
            Path to the output file
        """
        try:
            stream = ffmpeg.input(input_path, ss=start_time)

            if duration:
                stream = ffmpeg.input(input_path, ss=start_time, t=duration)
            elif end_time:
                stream = ffmpeg.input(input_path, ss=start_time, to=end_time)
            else:
                stream = ffmpeg.input(input_path, ss=start_time)

            stream = ffmpeg.output(stream, output_path, c="copy")
            ffmpeg.run(stream, overwrite_output=True, cmd=self.ffmpeg_path)
            return output_path
        except ffmpeg.Error as e:
            raise RuntimeError(f"Trim failed: {e.stderr.decode()}")

    def cut(
        self,
        input_path: str,
        output_path: str,
        start_time: float,
        end_time: float,
    ) -> str:
        """Alias for trim with explicit start and end times."""
        return self.trim(input_path, output_path, start_time, end_time)

    def merge_clips(
        self,
        input_paths: List[str],
        output_path: str,
        transitions: Optional[List[Optional[Transition]]] = None,
    ) -> str:
        """
        Merge multiple video clips into one, optionally with transitions.

        Args:
            input_paths: List of video file paths
            output_path: Destination file path
            transitions: Optional list of transitions between clips (one fewer than clips).
                         None means no transition (hard cut).

        Returns:
            Path to the output file
        """
        if len(input_paths) == 0:
            raise ValueError("No input files provided")
        if len(input_paths) == 1:
            return self._copy_file(input_paths[0], output_path)

        transitions = transitions or [None] * (len(input_paths) - 1)
        if len(transitions) != len(input_paths) - 1:
            raise ValueError(
                f"Expected {len(input_paths) - 1} transitions, got {len(transitions)}"
            )

        # For simple cuts, use concat demuxer
        use_transitions = any(t is not None and t.type != TransitionType.CUT for t in transitions)

        if not use_transitions:
            return self._concat_copy(input_paths, output_path)
        else:
            return self._concat_with_transitions(input_paths, output_path, transitions)

    def _copy_file(self, input_path: str, output_path: str) -> str:
        """Simple file copy."""
        try:
            stream = ffmpeg.input(input_path)
            stream = ffmpeg.output(stream, output_path, c="copy")
            ffmpeg.run(stream, overwrite_output=True, cmd=self.ffmpeg_path)
            return output_path
        except ffmpeg.Error as e:
            raise RuntimeError(f"Copy failed: {e.stderr.decode()}")

    def _concat_copy(self, input_paths: List[str], output_path: str) -> str:
        """Concatenate clips using stream copy (fast, no re-encode)."""
        # Create concat file
        concat_file = ""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            for path in input_paths:
                f.write(f"file '{Path(path).resolve()}'\n")
            concat_file = f.name

        try:
            stream = ffmpeg.input(concat_file, format="concat", safe=0)
            stream = ffmpeg.output(stream, output_path, c="copy")
            ffmpeg.run(stream, overwrite_output=True, cmd=self.ffmpeg_path)
            return output_path
        except ffmpeg.Error as e:
            raise RuntimeError(f"Concat failed: {e.stderr.decode()}")
        finally:
            if os.path.exists(concat_file):
                os.unlink(concat_file)

    def _concat_with_transitions(
        self,
        input_paths: List[str],
        output_path: str,
        transitions: List[Optional[Transition]],
    ) -> str:
        """Concatenate clips with transitions using filter complex."""
        streams = []
        filter_chains = []
        prev_label = None

        for i, (path, trans) in enumerate(zip(input_paths, [None] + transitions)):
            # Only process transitions that connect this clip to the next
            pass

        # Simplified: use overlay with crossfade for each transition
        # Build filter graph
        stream = ffmpeg.input(input_paths[0])
        current = stream.video
        current_audio = stream.audio

        for i in range(1, len(input_paths)):
            next_stream = ffmpeg.input(input_paths[i])
            next_video = next_stream.video
            next_audio = next_stream.audio

            trans = transitions[i - 1] if transitions else None
            if trans and trans.type == TransitionType.CROSSFADE and trans.duration > 0:
                # Crossfade transition
                current = ffmpeg.filter(
                    [current, next_video],
                    "crossfade",
                    duration=trans.duration,
                    offset_first=0,
                    transition="fade",
                )
            elif trans and trans.type == TransitionType.FADE_OUT and trans.duration > 0:
                # Fade out then cut
                current = ffmpeg.filter(current, "fade", type="out", duration=trans.duration)
                current = ffmpeg.concat(current, next_video, v=1, a=0)
            else:
                # Hard cut
                current = ffmpeg.concat(current, next_video, v=1, a=0)

            # Mix audio (simple concat for now)
            current_audio = ffmpeg.filter(
                [current_audio, next_audio], "acrossfade", duration=trans.duration if trans else 0
            ) if trans and trans.duration > 0 else ffmpeg.concat(current_audio, next_audio, v=0, a=1)

        stream = ffmpeg.output(current, current_audio, output_path)
        ffmpeg.run(stream, overwrite_output=True, cmd=self.ffmpeg_path)
        return output_path

    def apply_filter(
        self,
        input_path: str,
        output_path: str,
        filter_name: str,
        **filter_params: Any,
    ) -> str:
        """Apply an FFmpeg filter to a video."""
        try:
            stream = ffmpeg.input(input_path)
            video = stream.video.filter(filter_name, **filter_params)
            stream = ffmpeg.output(video, stream.audio, output_path)
            ffmpeg.run(stream, overwrite_output=True, cmd=self.ffmpeg_path)
            return output_path
        except ffmpeg.Error as e:
            raise RuntimeError(f"Filter '{filter_name}' failed: {e.stderr.decode()}")

    def speed_change(
        self,
        input_path: str,
        output_path: str,
        speed: float,
    ) -> str:
        """Change playback speed (1.0 = normal, 2.0 = double speed)."""
        try:
            stream = ffmpeg.input(input_path)
            video = stream.video.filter("setpts", f"{1.0/speed}*PTS")
            audio = stream.audio.filter("atempo", speed)
            stream = ffmpeg.output(video, audio, output_path)
            ffmpeg.run(stream, overwrite_output=True, cmd=self.ffmpeg_path)
            return output_path
        except ffmpeg.Error as e:
            raise RuntimeError(f"Speed change failed: {e.stderr.decode()}")

    def add_audio_track(
        self,
        video_path: str,
        audio_path: str,
        output_path: str,
        volume: float = 1.0,
        mix: bool = False,
    ) -> str:
        """
        Add or replace audio on a video.

        Args:
            video_path: Input video file
            audio_path: Audio file to add
            output_path: Output file path
            volume: Volume level for the new audio (0.0-1.0)
            mix: If True, mix with existing audio. If False, replace.

        Returns:
            Path to the output file
        """
        try:
            video = ffmpeg.input(video_path)
            audio = ffmpeg.input(audio_path)

            if mix:
                # Mix with existing audio
                existing_audio = video.audio.filter("volume", 0.3)  # lower original
                new_audio = audio.filter("volume", volume)
                mixed = ffmpeg.filter([existing_audio, new_audio], "amix", inputs=2, duration="first")
                stream = ffmpeg.output(video.video, mixed, output_path)
            else:
                # Replace audio entirely
                audio_adjusted = audio.filter("volume", volume)
                stream = ffmpeg.output(video.video, audio_adjusted, output_path)

            ffmpeg.run(stream, overwrite_output=True, cmd=self.ffmpeg_path)
            return output_path
        except ffmpeg.Error as e:
            raise RuntimeError(f"Add audio failed: {e.stderr.decode()}")

    def extract_audio(
        self,
        input_path: str,
        output_path: str,
        format: str = "wav",
    ) -> str:
        """Extract audio from a video file."""
        try:
            stream = ffmpeg.input(input_path)
            stream = ffmpeg.output(stream, output_path, acodec="pcm_s16le" if format == "wav" else None)
            ffmpeg.run(stream, overwrite_output=True, cmd=self.ffmpeg_path)
            return output_path
        except ffmpeg.Error as e:
            raise RuntimeError(f"Audio extraction failed: {e.stderr.decode()}")

    def render_sequence(
        self,
        sequence: HyperframeSequence,
        output_path: str,
        temp_dir: Optional[str] = None,
        preset: str = "medium",
        crf: int = 23,
        codec: str = "libx264",
        pixel_format: str = "yuv420p",
    ) -> str:
        """
        Render a full HyperframeSequence to a video file.

        This is the main render pipeline — processes each hyperframe,
        applies effects and transitions, then concatenates.

        Args:
            sequence: The HyperframeSequence to render
            output_path: Output file path
            temp_dir: Temporary directory for intermediate files
            preset: x264 preset (ultrafast, fast, medium, slow, veryslow)
            crf: Constant Rate Factor (0-51, lower = better quality)
            codec: Video codec
            pixel_format: Output pixel format

        Returns:
            Path to the rendered file
        """
        temp_dir = temp_dir or tempfile.mkdtemp(prefix="video_editor_")

        try:
            rendered_clips: List[str] = []

            for i, hf in enumerate(sequence.frames):
                clip_path = self._render_hyperframe(hf, temp_dir, i)
                if clip_path:
                    rendered_clips.append(clip_path)

            if not rendered_clips:
                raise RuntimeError("No clips to render")

            if len(rendered_clips) == 1:
                # Single clip — just copy
                stream = ffmpeg.input(rendered_clips[0])
                stream = ffmpeg.output(stream, output_path, vcodec=codec, preset=preset, crf=crf, pix_fmt=pixel_format)
                ffmpeg.run(stream, overwrite_output=True, cmd=self.ffmpeg_path)
            else:
                # Build filter complex for transitions
                transitions = [
                    hf.transition_in for hf in sequence.frames[1:]
                ]
                return self.merge_clips(
                    rendered_clips,
                    output_path,
                    transitions=transitions,
                )

            return output_path

        finally:
            # Cleanup temp files
            if os.path.exists(temp_dir):
                for f in os.listdir(temp_dir):
                    try:
                        os.unlink(os.path.join(temp_dir, f))
                    except OSError:
                        pass
                try:
                    os.rmdir(temp_dir)
                except OSError:
                    pass

    def _render_hyperframe(
        self,
        hf: Hyperframe,
        temp_dir: str,
        index: int,
    ) -> Optional[str]:
        """Render a single hyperframe to a temp file."""
        if not hf.source or not os.path.exists(hf.source):
            return None

        output = os.path.join(temp_dir, f"clip_{index:04d}.mp4")

        if hf.frame_range.start_time > 0 or hf.frame_range.end_time is not None:
            # Trim
            stream = ffmpeg.input(hf.source, ss=hf.frame_range.start_time)
            if hf.frame_range.end_time is not None:
                dur = hf.frame_range.end_time - hf.frame_range.start_time
                stream = ffmpeg.input(hf.source, ss=hf.frame_range.start_time, t=dur)
        else:
            stream = ffmpeg.input(hf.source)

        video = stream.video
        audio = stream.audio

        # Apply video effects
        video = self._apply_video_effects(video, hf.effects)

        # Apply audio effects
        audio = self._apply_ffmpeg_audio_effects(audio, hf.audio_effects)

        stream = ffmpeg.output(video, audio, output)
        ffmpeg.run(stream, overwrite_output=True, cmd=self.ffmpeg_path)
        return output

    def _apply_video_effects(self, video_stream, effects: List[Effect]):
        """Apply a list of video effects to an ffmpeg stream."""
        for effect in effects:
            if not effect.enabled:
                continue

            if effect.type == "color_grade":
                brightness = effect.params.get("brightness", 0)
                contrast = effect.params.get("contrast", 1.0)
                saturation = effect.params.get("saturation", 1.0)
                gamma = effect.params.get("gamma", 1.0)
                video_stream = video_stream.filter(
                    "eq",
                    brightness=brightness,
                    contrast=contrast,
                    saturation=saturation,
                    gamma=gamma,
                )
            elif effect.type == "blur":
                radius = effect.params.get("radius", 5)
                video_stream = video_stream.filter("gblur", sigma=radius)
            elif effect.type == "rotation":
                angle = effect.params.get("angle", 0)
                video_stream = video_stream.filter("rotate", angle * 3.14159 / 180)
            elif effect.type == "crop":
                x = effect.params.get("x", 0)
                y = effect.params.get("y", 0)
                w = effect.params.get("width", 1920)
                h = effect.params.get("height", 1080)
                video_stream = video_stream.filter("crop", w, h, x, y)
            elif effect.type == "fade_in":
                duration = effect.params.get("duration", 1.0)
                video_stream = video_stream.filter("fade", type="in", duration=duration)
            elif effect.type == "fade_out":
                duration = effect.params.get("duration", 1.0)
                video_stream = video_stream.filter("fade", type="out", duration=duration)

        return video_stream

    def _apply_ffmpeg_audio_effects(self, audio_stream, effects: List[AudioEffect]):
        """Apply audio effects that can be handled natively by FFmpeg."""
        for effect in effects:
            if not effect.enabled:
                continue

            if effect.type == AudioEffectType.VOLUME:
                volume = effect.params.get("volume", 1.0)
                audio_stream = audio_stream.filter("volume", volume)
            elif effect.type == AudioEffectType.FADE_IN:
                duration = effect.params.get("duration", 1.0)
                audio_stream = audio_stream.filter("afade", type="in", duration=duration)
            elif effect.type == AudioEffectType.FADE_OUT:
                duration = effect.params.get("duration", 1.0)
                audio_stream = audio_stream.filter("afade", type="out", duration=duration)
            elif effect.type == AudioEffectType.ECHO:
                delay = effect.params.get("delay", 0.5)
                decay = effect.params.get("decay", 0.5)
                audio_stream = audio_stream.filter("aecho", 0.8, 0.9, delay * 1000, decay)
            elif effect.type == AudioEffectType.NORMALIZE:
                audio_stream = audio_stream.filter("loudnorm")

        return audio_stream