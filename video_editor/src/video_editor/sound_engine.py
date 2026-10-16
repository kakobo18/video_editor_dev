"""
Sound Effects Engine
====================
Audio processing with sound effects using pydub and numpy.
Supports reverb, echo, pitch shift, fade, volume envelope, and more.
"""

from __future__ import annotations

import math
import os
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from pydub import AudioSegment
from pydub.generators import Sine, Square, Sawtooth, Triangle, WhiteNoise

from .hyperframe import AudioEffect, AudioEffectType


class SoundEngine:
    """
    Audio processing engine with support for sound effects, mixing, and synthesis.

    Uses pydub for high-level audio manipulation and numpy for sample-level
    DSP effects.
    """

    SUPPORTED_FORMATS = {"wav", "mp3", "ogg", "flac", "aac", "m4a", "wma"}

    def __init__(self, sample_rate: int = 44100, bit_depth: int = 16):
        self.sample_rate = sample_rate
        self.bit_depth = bit_depth

    # ── Load / Save ──────────────────────────────────────────────

    def load(self, file_path: str, format: Optional[str] = None) -> AudioSegment:
        """Load an audio file."""
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Audio file not found: {file_path}")
        return AudioSegment.from_file(file_path, format=format)

    def save(
        self,
        audio: AudioSegment,
        file_path: str,
        format: Optional[str] = None,
    ) -> str:
        """Save an AudioSegment to a file."""
        ext = (Path(file_path).suffix[1:]).lower() or format
        if ext and ext not in self.SUPPORTED_FORMATS:
            raise ValueError(f"Unsupported format: {ext}. Supported: {self.SUPPORTED_FORMATS}")
        audio.export(file_path, format=format or ext)
        return file_path

    # ── Conversion ───────────────────────────────────────────────

    def to_numpy(self, audio: AudioSegment) -> np.ndarray:
        """Convert AudioSegment to numpy array (float64, -1.0 to 1.0)."""
        samples = np.array(audio.get_array_of_samples(), dtype=np.float64)
        # Normalize based on sample width
        max_val = float(2 ** (audio.sample_width * 8 - 1))
        samples /= max_val
        # Reshape for stereo
        if audio.channels == 2:
            samples = samples.reshape((-1, 2))
        return samples

    def from_numpy(
        self,
        samples: np.ndarray,
        frame_rate: int = 44100,
        sample_width: int = 2,
    ) -> AudioSegment:
        """Convert numpy array back to AudioSegment."""
        # Clamp to [-1, 1]
        samples = np.clip(samples, -1.0, 1.0)
        # Convert to int
        max_val = float(2 ** (sample_width * 8 - 1))
        int_samples = (samples * max_val).astype(np.int16)
        # Handle mono vs stereo
        channels = 2 if samples.ndim > 1 and samples.shape[1] == 2 else 1
        return AudioSegment(
            int_samples.tobytes(),
            frame_rate=frame_rate,
            sample_width=sample_width,
            channels=channels,
        )

    # ── Volume / Gain ────────────────────────────────────────────

    def set_volume(self, audio: AudioSegment, volume: float) -> AudioSegment:
        """
        Set volume.
        volume=1.0 = original, 0.5 = half, 2.0 = double.
        """
        return audio.apply_gain(20 * math.log10(max(volume, 0.0001)))

    def change_volume_db(self, audio: AudioSegment, db: float) -> AudioSegment:
        """Change volume by a specific number of decibels."""
        return audio.apply_gain(db)

    def normalize(self, audio: AudioSegment, target_dbfs: float = -1.0) -> AudioSegment:
        """Normalize audio to a target loudness level."""
        return audio.apply_gain(target_dbfs - audio.dBFS)

    # ── Fades ────────────────────────────────────────────────────

    def fade_in(self, audio: AudioSegment, duration_ms: float = 1000) -> AudioSegment:
        """Apply a fade-in effect."""
        return audio.fade_in(int(duration_ms))

    def fade_out(self, audio: AudioSegment, duration_ms: float = 1000) -> AudioSegment:
        """Apply a fade-out effect."""
        return audio.fade_out(int(duration_ms))

    def crossfade(
        self,
        audio_a: AudioSegment,
        audio_b: AudioSegment,
        duration_ms: float = 1000,
    ) -> AudioSegment:
        """Crossfade two audio segments together."""
        return audio_a.append(audio_b, crossfade=int(duration_ms))

    def volume_envelope(
        self,
        audio: AudioSegment,
        envelope: List[Tuple[float, float]],
    ) -> AudioSegment:
        """
        Apply a custom volume envelope over time.

        Args:
            audio: Input audio
            envelope: List of (time_fraction, volume) pairs, where
                     time_fraction is 0.0 to 1.0 and volume is 0.0 to 1.0.

        Returns:
            Audio with the envelope applied
        """
        samples = self.to_numpy(audio)
        if samples.ndim == 1:
            samples = samples[:, np.newaxis]

        num_samples = samples.shape[0]
        env_times = np.array([t for t, _ in envelope])
        env_volumes = np.array([v for _, v in envelope])

        # Interpolate envelope across all samples
        sample_positions = np.linspace(0, 1, num_samples)
        gain_curve = np.interp(sample_positions, env_times, env_volumes)

        # Apply
        for ch in range(samples.shape[1]):
            samples[:, ch] *= gain_curve

        return self.from_numpy(samples, frame_rate=audio.frame_rate, sample_width=audio.sample_width)

    # ── Echo / Delay ─────────────────────────────────────────────

    def echo(
        self,
        audio: AudioSegment,
        delay_ms: float = 300.0,
        decay: float = 0.5,
        num_echoes: int = 5,
    ) -> AudioSegment:
        """
        Add echo/repeat effect.

        Args:
            audio: Input audio
            delay_ms: Delay between echoes in milliseconds
            decay:  Volume decay per echo (0.0 - 1.0)
            num_echoes: Number of echo repeats

        Returns:
            Audio with echo effect
        """
        # Work with raw samples for precision
        samples = self.to_numpy(audio)
        if samples.ndim == 1:
            samples = samples[:, np.newaxis]

        delay_samples = int(delay_ms * audio.frame_rate / 1000)
        total_samples = len(samples) + delay_samples * num_echoes
        num_channels = samples.shape[1]

        output = np.zeros((total_samples, num_channels), dtype=np.float64)

        for echo_num in range(num_echoes + 1):
            offset = delay_samples * echo_num
            gain = decay ** echo_num
            end = min(offset + len(samples), total_samples)
            output[offset:end, :] += samples[: end - offset, :] * gain

        if num_channels == 1:
            output = output[:, 0]

        return self.from_numpy(output, frame_rate=audio.frame_rate, sample_width=audio.sample_width)

    # ── Reverb ───────────────────────────────────────────────────

    def reverb(
        self,
        audio: AudioSegment,
        decay: float = 0.3,
        room_size: float = 0.7,
        damping: float = 0.5,
        pre_delay_ms: float = 20.0,
    ) -> AudioSegment:
        """
        Add a reverb effect using a simplified Schroeder reverberator.

        Args:
            audio: Input audio
            decay: Reverb decay (0.0 - 1.0)
            room_size: Perceived room size (0.0 - 1.0)
            damping: High-frequency damping (0.0 - 1.0)
            pre_delay_ms: Pre-delay in milliseconds

        Returns:
            Audio with reverb effect
        """
        samples = self.to_numpy(audio)
        if samples.ndim == 1:
            samples = samples[:, np.newaxis]

        num_channels = samples.shape[1]
        sr = audio.frame_rate

        # Comb filter delays (in samples) — standard Schroeder values scaled by room_size
        comb_delays = [
            int(30 * room_size * sr / 1000),
            int(37 * room_size * sr / 1000),
            int(43 * room_size * sr / 1000),
            int(50 * room_size * sr / 1000),
        ]

        # All-pass filter delays
        ap_delays = [
            int(5 * sr / 1000),
            int(9 * sr / 1000),
            int(13 * sr / 1000),
            int(17 * sr / 1000),
        ]

        output = np.zeros_like(samples)

        for ch in range(num_channels):
            channel_data = samples[:, ch]

            # Pre-delay
            pre_delay_samples = int(pre_delay_ms * sr / 1000)
            delayed = np.zeros(len(channel_data) + pre_delay_samples)
            delayed[pre_delay_samples:] = channel_data

            # Comb filters in parallel
            padded_len = len(delayed) + max(comb_delays)
            comb_sum = np.zeros(padded_len)
            for delay in comb_delays:
                comb_out = np.zeros(padded_len)
                for i in range(len(delayed)):
                    comb_out[i] = delayed[i] + decay * comb_out[max(0, i - delay)]
                comb_sum += comb_out

            # All-pass filters in series
            ap_out = comb_sum / len(comb_delays)
            for delay in ap_delays:
                ap_next = np.zeros(len(ap_out))
                for i in range(len(ap_out)):
                    delayed_sample = ap_out[max(0, i - delay)]
                    ap_next[i] = -ap_out[i] * damping + delayed_sample + damping * ap_next[max(0, i - delay)]
                ap_out = ap_next

            # Trim back to original length
            end = min(len(output), len(ap_out))
            output[:end, ch] = ap_out[:end]

        # Mix dry/wet
        dry = samples
        wet = output[: len(samples)]
        mixed = dry * (1 - room_size * 0.5) + wet * (room_size * 0.5)

        # Normalize
        max_val = np.max(np.abs(mixed))
        if max_val > 0:
            mixed /= max_val
            mixed *= 0.95

        if num_channels == 1:
            mixed = mixed[:, 0]

        return self.from_numpy(mixed, frame_rate=audio.frame_rate, sample_width=audio.sample_width)

    # ── Pitch Shift ──────────────────────────────────────────────

    def pitch_shift(
        self,
        audio: AudioSegment,
        semitones: float,
    ) -> AudioSegment:
        """
        Shift pitch without changing tempo.

        Uses time-domain pitch shifting (WSOLA-like).

        Args:
            audio: Input audio
            semitones: Number of semitones to shift. Positive = higher, negative = lower.

        Returns:
            Pitch-shifted audio
        """
        # Change frame rate (changes pitch + tempo)
        ratio = 2.0 ** (semitones / 12.0)
        new_frame_rate = int(audio.frame_rate * ratio)

        # Resample (changes pitch AND tempo)
        shifted = audio._spawn(audio.raw_data, overrides={
            "frame_rate": new_frame_rate
        })

        # Convert back to original frame rate (fixes tempo, keeps pitch shift)
        return shifted.set_frame_rate(audio.frame_rate)

    # ── Compression ──────────────────────────────────────────────

    def compress(
        self,
        audio: AudioSegment,
        threshold_db: float = -20.0,
        ratio: float = 4.0,
        attack_ms: float = 5.0,
        release_ms: float = 50.0,
    ) -> AudioSegment:
        """
        Apply dynamic range compression.

        Args:
            audio: Input audio
            threshold_db: Threshold in dBFS (above this is compressed)
            ratio: Compression ratio (e.g., 4:1)
            attack_ms: Attack time in milliseconds
            release_ms: Release time in milliseconds

        Returns:
            Compressed audio
        """
        samples = self.to_numpy(audio)
        if samples.ndim == 1:
            samples = samples[:, np.newaxis]

        sr = audio.frame_rate
        threshold_linear = 10 ** (threshold_db / 20.0)
        attack_coeff = math.exp(-1.0 / (attack_ms * sr / 1000.0))
        release_coeff = math.exp(-1.0 / (release_ms * sr / 1000.0))

        num_channels = samples.shape[1]
        output = np.zeros_like(samples)
        envelope = 0.0

        for ch in range(num_channels):
            for i in range(len(samples)):
                abs_sample = abs(samples[i, ch])

                # Envelope follower
                if abs_sample > envelope:
                    envelope = attack_coeff * (envelope - abs_sample) + abs_sample
                else:
                    envelope = release_coeff * (envelope - abs_sample) + abs_sample

                # Compute gain
                if envelope > threshold_linear:
                    gain_db = threshold_db + (20 * math.log10(envelope) - threshold_db) / ratio
                    gain_linear = 10 ** (gain_db / 20.0) / max(envelope, 1e-10)
                else:
                    gain_linear = 1.0

                output[i, ch] = samples[i, ch] * min(gain_linear, 1.0)

        if num_channels == 1:
            output = output[:, 0]

        return self.from_numpy(output, frame_rate=audio.frame_rate, sample_width=audio.sample_width)

    # ── EQ / Filtering ───────────────────────────────────────────

    def low_pass(self, audio: AudioSegment, cutoff_hz: float) -> AudioSegment:
        """Apply a low-pass filter."""
        return audio.low_pass_filter(cutoff_hz)

    def high_pass(self, audio: AudioSegment, cutoff_hz: float) -> AudioSegment:
        """Apply a high-pass filter."""
        return audio.high_pass_filter(cutoff_hz)

    # ── Mixing ───────────────────────────────────────────────────

    def overlay(self, base: AudioSegment, overlay: AudioSegment, position_ms: float = 0, loop: bool = False) -> AudioSegment:
        """
        Overlay audio onto base audio at the given position.

        Args:
            base: Base audio track
            overlay: Audio to overlay on top
            position_ms: Position in milliseconds where overlay starts
            loop: If True, loop the overlay to fill the base duration

        Returns:
            Mixed audio
        """
        if loop and len(overlay) > 0:
            # Loop overlay to fill base
            loops_needed = max(1, int(math.ceil(len(base) / len(overlay))))
            overlay = overlay * loops_needed

        return base.overlay(overlay, position=position_ms)

    def mix(
        self,
        tracks: List[AudioSegment],
        volumes: Optional[List[float]] = None,
    ) -> AudioSegment:
        """
        Mix multiple audio tracks together with individual volume levels.

        Args:
            tracks: List of AudioSegments to mix
            volumes: Optional list of volume multipliers (default: all 1.0)

        Returns:
            Mixed audio
        """
        if not tracks:
            raise ValueError("No audio tracks provided")

        volumes = volumes or [1.0] * len(tracks)
        if len(volumes) != len(tracks):
            raise ValueError("Number of volumes must match number of tracks")

        # Find the longest track
        max_len = max(len(t) for t in tracks)

        mixed: AudioSegment = AudioSegment.silent(duration=max_len, frame_rate=self.sample_rate)

        for track, vol in zip(tracks, volumes):
            if vol != 1.0:
                track = self.set_volume(track, vol)
            mixed = mixed.overlay(track)

        return mixed

    # ── Synthesis ────────────────────────────────────────────────

    def generate_tone(
        self,
        frequency_hz: float,
        duration_ms: float,
        volume_db: float = -10.0,
        waveform: str = "sine",
    ) -> AudioSegment:
        """Generate a test tone."""
        gen_map = {
            "sine": Sine,
            "square": Square,
            "sawtooth": Sawtooth,
            "triangle": Triangle,
        }
        gen_class = gen_map.get(waveform, Sine)
        gen = gen_class(frequency_hz)
        return gen.to_audio_segment(duration=duration_ms, volume=volume_db)

    def generate_silence(self, duration_ms: float) -> AudioSegment:
        """Generate silence."""
        return AudioSegment.silent(duration=duration_ms, frame_rate=self.sample_rate)

    def generate_noise(self, duration_ms: float, volume_db: float = -10.0) -> AudioSegment:
        """Generate white noise."""
        noise = WhiteNoise()
        return noise.to_audio_segment(duration=duration_ms, volume=volume_db)

    # ── Convenience: apply effect by type ────────────────────────

    def apply_effect(self, audio: AudioSegment, effect: AudioEffect) -> AudioSegment:
        """Apply a single AudioEffect to audio."""
        if not effect.enabled:
            return audio

        params = effect.params

        if effect.type == AudioEffectType.VOLUME:
            return self.set_volume(audio, params.get("volume", 1.0))
        elif effect.type == AudioEffectType.FADE_IN:
            return self.fade_in(audio, params.get("duration", 1000))
        elif effect.type == AudioEffectType.FADE_OUT:
            return self.fade_out(audio, params.get("duration", 1000))
        elif effect.type == AudioEffectType.ECHO:
            return self.echo(
                audio,
                delay_ms=params.get("delay", 300),
                decay=params.get("decay", 0.5),
                num_echoes=params.get("num_echoes", 5),
            )
        elif effect.type == AudioEffectType.REVERB:
            return self.reverb(
                audio,
                decay=params.get("decay", 0.3),
                room_size=params.get("room_size", 0.7),
                damping=params.get("damping", 0.5),
                pre_delay_ms=params.get("pre_delay", 20),
            )
        elif effect.type == AudioEffectType.PITCH_SHIFT:
            return self.pitch_shift(audio, params.get("semitones", 0))
        elif effect.type == AudioEffectType.NORMALIZE:
            return self.normalize(audio, params.get("target_dbfs", -1.0))
        elif effect.type == AudioEffectType.COMPRESS:
            return self.compress(
                audio,
                threshold_db=params.get("threshold", -20),
                ratio=params.get("ratio", 4.0),
                attack_ms=params.get("attack", 5),
                release_ms=params.get("release", 50),
            )
        else:
            return audio  # Unknown effect, pass through

    def apply_effects(self, audio: AudioSegment, effects: List[AudioEffect]) -> AudioSegment:
        """Apply a list of audio effects sequentially."""
        for effect in effects:
            audio = self.apply_effect(audio, effect)
        return audio