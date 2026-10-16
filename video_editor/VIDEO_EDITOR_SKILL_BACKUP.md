---
name: video-editor
description: 'Process natural-language video editing requests using the video-editor system. Use whenever the user says "edit this video", "cut it", "trim", "add effects", "export video", "process my video", "apply sound effect", "make a video", or describes video editing tasks in plain language.'
user-invocable: true
---

# Video Editor — Natural Language Video Editing

Processes your video editing requests described in plain English. Just tell me what you want to do and I'll handle the CLI commands.

## Requirements

- **Project**: `video_editor` package installed (`pip install -e "C:\Users\kakob\OneDrive - dividebyzero.art\IT\Video Editor\video_editor"`)
- **FFmpeg**: Must be in PATH (already installed: v8.1)
- **Working directory**: `C:\Users\kakob\OneDrive - dividebyzero.art\IT\Video Editor\video_editor`

## When to Use

- User says "edit this video", "cut it", "trim", "add effects"
- User describes a video editing task in natural language
- User wants to apply sound effects, transitions, or export
- User asks to process video files

## Available CLI Commands

| Command | Purpose | Example |
|---------|---------|---------|
| `video-editor info <file>` | Show media file info | `video-editor info intro.mp4` |
| `video-editor import <files...>` | Import media into project | `video-editor import clip1.mp4 clip2.mp4` |
| `video-editor list` | Show timeline | `video-editor list` |
| `video-editor trim <idx> <start> <end>` | Trim clip | `video-editor trim 0 5 15` |
| `video-editor split <idx> <time>` | Split clip at time | `video-editor split 0 10` |
| `video-editor effect <idx> <type> [k=v...]` | Add video effect | `video-editor effect 0 fade_in duration=1.0` |
| `video-editor audio-effect <idx> <type> [k=v...]` | Add audio effect | `video-editor audio-effect 0 reverb room_size=0.7` |
| `video-editor transition <idx> <type> [-d dur] [--side]` | Add transition | `video-editor transition 1 crossfade -d 1.0 --side in` |
| `video-editor generate-sound <out> [opts]` | Generate sound | `video-editor generate-sound beep.wav --type tone --frequency 440` |
| `video-editor export <output>` | Render video | `video-editor export final.mp4` |
| `video-editor save <file>` | Save project | `video-editor save project.json` |

## Audio Effect Types

- `volume` — params: `volume=0.5`
- `fade_in` — params: `duration=1000`
- `fade_out` — params: `duration=1000`
- `echo` — params: `delay=0.3`, `decay=0.5`
- `reverb` — params: `room_size=0.7`, `decay=0.3`, `damping=0.5`
- `pitch_shift` — params: `semitones=5`
- `normalize` — params: `target_dbfs=-1.0`
- `compress` — params: `threshold=-20`, `ratio=4.0`

## Video Effect Types

- `fade_in` — params: `duration=1.0`
- `fade_out` — params: `duration=1.0`
- `color_grade` — params: `brightness=0`, `contrast=1.0`, `saturation=1.0`
- `blur` — params: `radius=5`
- `rotation` — params: `angle=90`
- `crop` — params: `x=0`, `y=0`, `width=1280`, `height=720`
- `speed_change` — handled by separate FFmpeg pipeline

## Transition Types

- `cut`, `fade_in`, `fade_out`, `crossfade`, `dissolve`, `wipe_left`, `wipe_right`, `slide_left`, `slide_right`, `zoom_in`, `zoom_out`

## Coordinate Grid Reference Image

When the user asks for a **grid**, **coordinates**, **percentage positions**, or a **dimension reference** for a video, generate a PNG reference image using the following approved layout:

1. Probe the source video to obtain its width $W$ and height $H$.
2. Use its first frame as the image content.
3. Draw opaque orange grid lines at every 10% interval from 10% through 90%:
   - Vertical line $x = \operatorname{round}(W \times p / 100)$
   - Horizontal line $y = \operatorname{round}(H \times p / 100)$
4. Add a black **left margin** for Y labels and a compact black **bottom margin** for X labels.
5. Draw Y labels in the left margin as horizontal orange text, in exactly this format: `10% (48px)`.
6. Draw X labels in the bottom margin as orange, transparent-background text rotated to read **from bottom upward**, centered exactly below the matching vertical line. Use exactly this format: `10% (85px)`.
7. Do **not** use opaque text boxes or backgrounds behind the labels. A thin dark outline is allowed for contrast.
8. Keep the bottom margin compact: labels should begin directly below the video frame, without unnecessary blank space.

For the current standard 854×480 test video, the key grid values are:

| Percent | X coordinate | Y coordinate |
|---:|---:|---:|
| 10% | 85px | 48px |
| 20% | 171px | 96px |
| 30% | 256px | 144px |
| 40% | 342px | 192px |
| 50% | 427px | 240px |
| 60% | 512px | 288px |
| 70% | 598px | 336px |
| 80% | 683px | 384px |
| 90% | 769px | 432px |

Save the result as `video_grid_labeled.png` in the active project folder unless the user supplies another output path.

## Procedure

1. **Ask the user** for the path to their video file(s) if not provided
2. **Import** the files using `video-editor import <paths...>`
3. **Show the timeline** with `video-editor list`
4. **Process edits** based on user's natural language instructions:
   - Trimming → `video-editor trim <idx> <start> <end>`
   - Splitting → `video-editor split <idx> <time>`
   - Effects → `video-editor effect <idx> <type> <params>` or `video-editor audio-effect <idx> <type> <params>`
   - Transitions → `video-editor transition <idx> <type> -d <duration> --side <in|out>`
   - Sound generation → `video-editor generate-sound <output>`
5. **Confirm** with user before exporting
6. **Export** with `video-editor export <output.mp4>`
7. **Tell the user** where the output file is saved so they can play it

## Python API Reference

For complex workflows, use Python directly:

```python
from video_editor import VideoEditor, AudioEffectType, TransitionType

editor = VideoEditor()
editor.new_project("My Edit")

# Import and process
editor.import_clip(r"path\to\video.mp4")
editor.trim_clip("main", 0, 5, 20)
editor.add_video_effect("main", 0, "fade_in", duration=1.0)
editor.add_audio_effect("main", 0, AudioEffectType.REVERB, room_size=0.7)
editor.export_sequence("output.mp4")
```

Always show the output path to the user when done.
