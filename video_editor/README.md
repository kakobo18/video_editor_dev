# Video Editor

A hyperframe-based video editing system built with Python, FFmpeg, and a powerful sound effects engine.

## Features

- **Hyperframe System** — Frame-aware data structures with metadata, effects, transitions, multi-track timelines, and keyframes
- **FFmpeg Integration** — Programmatic video/audio processing via `ffmpeg-python` (trim, cut, merge, filter, encode, render)
- **Sound Effects Engine** — pydub + numpy DSP for reverb, echo, pitch shift, compression, EQ, volume envelopes, crossfades, and audio synthesis
- **Multi-Track Timeline** — Parallel video, audio, and overlay tracks with per-track keyframes
- **CLI Interface** — Full command-line interface with progress bars, tables, and color output
- **Project Save/Load** — JSON-based project serialization

## Requirements

- Python 3.10+
- [FFmpeg](https://ffmpeg.org/) installed and available in your PATH

## Installation

```bash
# Install from source
cd video_editor
pip install -e .

# Or install with dev dependencies
pip install -e ".[dev]"
```

## Quick Start

### CLI Usage

```bash
# Show info about a media file
video-editor info my_video.mp4

# Import clips into the project
video-editor import clip1.mp4 clip2.mp4 clip3.mp4

# List all clips in the active sequence
video-editor list

# Trim a clip (index 0) to a specific range
video-editor trim 0 5.0 15.0

# Split a clip at a time offset
video-editor split 0 10.0

# Add a video effect (e.g., fade in)
video-editor effect 0 fade_in duration=1.0

# Add a crossfade transition between clips
video-editor transition 1 crossfade --duration 1.0 --side in

# Add an audio effect (e.g., echo)
video-editor audio-effect 0 echo delay=0.3 decay=0.5

# Generate a synthesized sound effect
video-editor generate-sound beep.wav --type tone --frequency 440 --duration 500

# Export the final video
video-editor export output.mp4

# Export only audio
video-editor export-audio output.wav --source video.mp4 --effect echo delay=300

# Save / Load project
video-editor save my_project.json
video-editor load my_project.json
```

### Python API

```python
from video_editor import VideoEditor, AudioEffectType

# Create an editor
editor = VideoEditor()
editor.new_project("My Edit")

# Import clips
editor.import_clip("intro.mp4")
editor.import_clip("main.mp4")

# Trim the first clip
editor.trim_clip("main", 0, 0.0, 10.0)

# Add effects
editor.add_video_effect("main", 0, "fade_in", duration=1.0)
editor.add_audio_effect("main", 0, AudioEffectType.ECHO, delay=0.3, decay=0.5)

# Add a transition
from video_editor import TransitionType
editor.set_transition("main", 1, TransitionType.CROSSFADE, duration=1.0, side="in")

# Export
editor.export_sequence("final_output.mp4")
```

### Sound Effects (Python API)

```python
from video_editor import SoundEngine, AudioEffect, AudioEffectType

sound = SoundEngine()

# Load audio
audio = sound.load("input.wav")

# Apply effects
reverb = AudioEffect(AudioEffectType.REVERB, params={"room_size": 0.8, "decay": 0.4})
echo = AudioEffect(AudioEffectType.ECHO, params={"delay": 300, "decay": 0.5})
pitch = AudioEffect(AudioEffectType.PITCH_SHIFT, params={"semitones": 3})

# Chain effects
processed = sound.apply_effects(audio, [reverb, echo, pitch])

# Save
sound.save(processed, "output.wav")

# Mix multiple tracks
from pydub import AudioSegment
track1 = sound.load("vocals.wav")
track2 = sound.load("music.wav")
mixed = sound.mix([track1, track2], volumes=[1.0, 0.5])
```

## Project Structure

```
video_editor/
├── src/
│   └── video_editor/
│       ├── __init__.py       # Package entry point
│       ├── hyperframe.py     # Hyperframe data structures
│       ├── ffmpeg_engine.py  # FFmpeg wrapper
│       ├── sound_engine.py   # Sound effects engine
│       ├── editor.py         # High-level editor orchestrator
│       └── cli.py            # CLI interface
├── pyproject.toml
├── requirements.txt
└── README.md
```

## Architecture

| Component | Description |
|-----------|-------------|
| **Hyperframe** | A segment of video with metadata, effects, transitions. Can be a single frame, range, or composition. |
| **HyperframeSequence** | Ordered timeline of hyperframes; supports split, reorder, insert, remove. |
| **MultiTrackTimeline** | Parallel tracks (video, audio, overlay) with per-track keyframes. |
| **FFmpegEngine** | Wraps FFmpeg for probe, trim, merge, filter, encode, render. |
| **SoundEngine** | pydub + numpy DSP: reverb, echo, pitch shift, compression, EQ, fades, synthesis. |
| **VideoEditor** | High-level orchestrator combining all components with project save/load. |

## License

MIT