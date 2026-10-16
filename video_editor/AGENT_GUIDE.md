# Video Editot — Agent User Guide

How to use the Copilot agent to edit videos for you using natural language.

---

## Table of Contents

1. [How It Works](#1-how-it-works)
2. [What You Can Ask](#2-what-you-can-ask)
3. [Triggering the Agent](#3-triggering-the-agent)
4. [Skill File Location](#4-skill-file-location)
5. [Step-by-Step Editing Workflow](#5-step-by-step-editing-workflow)
6. [CLI Commands Reference](#6-cli-commands-reference)
7. [Audio Effects Reference](#7-audio-effects-reference)
8. [Video Effects Reference](#8-video-effects-reference)
9. [Transitions Reference](#9-transitions-reference)
10. [Example Conversations](#10-example-conversations)
11. [Troubleshooting](#11-troubleshooting)

---

## 1. How It Works

The **video-editor agent skill** is a customization file that tells the Copilot agent:

> *"Hey, when the user talks about editing videos, load these instructions and use these tools!"*

When you type something like *"edit this video"* or *"trim my clip"* the agent:
1. **Reads** the skill file to know what commands and effects are available
2. **Asks** you for the file paths and details if needed
3. **Runs** the CLI commands (`video-editor import`, `video-editor trim`, etc.) in the terminal
4. **Tells you** when it's done and where the output file is

You get the result as a playable `.mp4` file on your computer.

---

## 2. What You Can Ask

You can ask anything related to video editing:

| Category | Examples |
|----------|----------|
| **Import** | "Import my video.mp4" / "Load these 3 clips" |
| **Trim / Cut** | "Trim it to the first 30 seconds" / "Cut from 10s to 45s" |
| **Split** | "Split the video at 15 seconds" |
| **Video Effects** | "Add a fade in" / "Apply a blur" / "Crop to 1280x720" |
| **Audio Effects** | "Add reverb" / "Apply echo" / "Pitch shift up 5 semitones" |
| **Transitions** | "Crossfade between clip 1 and 2" / "Add a fade transition" |
| **Generate Sound** | "Make a 440Hz beep for 1 second" / "Create white noise" |
| **Export** | "Export it to final.mp4" / "Render and save" |
| **Advice** | "What transitions would look good for a travel montage?" |
| **Full workflow** | "Take intro.mp4 and main.mp4, trim the intro to 5s, crossfade between them, add reverb, export to out.mp4" |

---

## 3. Triggering the Agent

There are **two ways** to trigger the video editing agent:

### Method A: Just type naturally (automatic detection)

The agent will automatically activate when you say things like:
- *"Edit this video"*
- *"Cut it"*
- *"Trim"*
- *"Add effects"*
- *"Export video"*
- *"Process my video"*
- *"Apply sound effect"*
- *"Make a video"*
- *"I need editing advice"*
- Or describe any video editing task in plain language

### Method B: Type `/edit-video` in chat (slash command)

Type `/edit-video` in the chat box and press Enter. A prompt will appear asking you for:
- **Path to your video file(s)**
- **What edits you want** (trim, effects, transitions, etc.)
- **Sound effects** you'd like to add
- **Output file name**

### Method C: Mention the skill by name

You can also say:
- *"Use the video-editor skill"*
- *"Can you run video-editor on this?"*

---

## 4. Skill File Location

The skill file is stored at:

```
C:\Users\kakob\.agents\skills\video-editor\SKILL.md
```

**What this means:**
- It's a **personal** skill (installed just for you, not shared with a team)
- It lives under `%USERPROFILE%\.agents\skills\` — your personal `agents` folder
- It loads automatically when the agent detects video editing keywords
- It's available **across all VS Code workspaces**, not just this project

### The prompt file (slash command):

```
C:\Users\kakob\AppData\Roaming\Code\User\prompts\edit-video.prompt.md
```

This is what makes `/edit-video` appear as a slash command in chat.

---

## 5. Step-by-Step Editing Workflow

### Basic workflow:

```
1. Tell the agent what to do
         │
         ▼
2. Agent imports your video(s)
         │
         ▼
3. Agent shows you the timeline
         │
         ▼
4. Agent applies your edits (trim, effects, etc.)
         │
         ▼
5. Agent confirms with you before exporting
         │
         ▼
6. Agent exports the video
         │
         ▼
7. You play the output file
```

### Example full session:

**You say:** *"Import intro.mp4 and main.mp4, trim intro to first 5 seconds, crossfade between them, export to final.mp4"*

**The agent does:**
```bash
video-editor import intro.mp4 main.mp4
video-editor trim 0 0 5
video-editor transition 1 crossfade -d 1.0 --side in
video-editor export final.mp4
```

**Agent replies:** *"Done! Your video is saved at C:\Users\kakob\...\final.mp4"*

---

## 6. CLI Commands Reference

These are the commands the agent runs behind the scenes. You don't need to type them — the agent does it for you.

| Command | What it does | Example |
|---------|-------------|---------|
| `video-editor info <file>` | Show media file info | `video-editor info intro.mp4` |
| `video-editor import <files...>` | Import media into project | `video-editor import clip1.mp4 clip2.mp4` |
| `video-editor list` | Show timeline with all clips | `video-editor list` |
| `video-editor trim <idx> <start> <end>` | Trim a clip | `video-editor trim 0 5 15` |
| `video-editor split <idx> <time>` | Split a clip at a time point | `video-editor split 0 10` |
| `video-editor effect <idx> <type> [k=v...]` | Add a video effect | `video-editor effect 0 fade_in duration=1.0` |
| `video-editor audio-effect <idx> <type> [k=v...]` | Add audio effect | `video-editor audio-effect 0 reverb room_size=0.7` |
| `video-editor transition <idx> <type> [-d dur] [--side]` | Add transition | `video-editor transition 1 crossfade -d 1.0 --side in` |
| `video-editor generate-sound <out> [opts]` | Generate a sound | `video-editor generate-sound beep.wav --type tone --frequency 440` |
| `video-editor export <output>` | Render final video | `video-editor export final.mp4` |
| `video-editor export-audio <out> [opts]` | Export only audio | `video-editor export-audio audio.wav --source video.mp4` |
| `video-editor save <file>` | Save project as JSON | `video-editor save project.json` |
| `video-editor load <file>` | Load a saved project | `video-editor load project.json` |

**Note:** `<idx>` is the clip index number (0 = first clip, 1 = second clip, etc.) shown in the `list` output.

---

## 7. Audio Effects Reference

These can be applied to any clip by telling the agent.

| Effect | What it does | Parameters | Example |
|--------|-------------|------------|---------|
| `volume` | Change volume | `volume=0.5` (half), `volume=2.0` (double) | "Make it half as loud" |
| `fade_in` | Fade audio in | `duration=1000` (milliseconds) | "Fade the audio in over 1 second" |
| `fade_out` | Fade audio out | `duration=2000` (milliseconds) | "Fade the audio out over 2 seconds" |
| `echo` | Add echo/delay | `delay=0.3` (seconds), `decay=0.5` (volume per echo) | "Add echo with 300ms delay" |
| `reverb` | Add reverb | `room_size=0.7`, `decay=0.3`, `damping=0.5` | "Make it sound like a large room" |
| `pitch_shift` | Shift pitch | `semitones=5` (positive = higher, negative = lower) | "Make the voice sound higher" |
| `normalize` | Normalize loudness | `target_dbfs=-1.0` | "Make it as loud as possible without clipping" |
| `compress` | Compress dynamics | `threshold=-20`, `ratio=4.0`, `attack=5`, `release=50` | "Even out the volume levels" |

### Quick parameters reference:

```
echo       delay=0.3  decay=0.5
reverb     room_size=0.7  decay=0.3  damping=0.5
pitch_shift semitones=5
compress   threshold=-20  ratio=4.0
```

---

## 8. Video Effects Reference

| Effect | What it does | Parameters | Example |
|--------|-------------|------------|---------|
| `fade_in` | Fade video in from black | `duration=1.0` (seconds) | "Fade in over 1 second" |
| `fade_out` | Fade video out to black | `duration=1.5` | "Fade out over 1.5 seconds" |
| `color_grade` | Adjust colors | `brightness=0`, `contrast=1.0`, `saturation=1.0` | "Boost saturation to 1.5" |
| `blur` | Blur the image | `radius=5` | "Blur the video slightly" |
| `rotation` | Rotate the video | `angle=90` (degrees) | "Rotate 90 degrees" |
| `crop` | Crop a portion | `x=0 y=0 width=1280 height=720` | "Crop to 1280x720" |

---

## 9. Transitions Reference

| Transition | Description | Default duration |
|-----------|-------------|-----------------|
| `cut` | Hard cut (instant) | 0s |
| `fade_in` | Fade in from black | 1s |
| `fade_out` | Fade out to black | 1s |
| `crossfade` | Smooth crossfade between clips | 1s |
| `dissolve` | Dissolve transition | 1s |
| `wipe_left` / `wipe_right` | Wipe across the screen | 1s |
| `wipe_up` / `wipe_down` | Wipe vertically | 1s |
| `slide_left` / `slide_right` | Slide transition | 1s |
| `zoom_in` / `zoom_out` | Zoom transition | 1s |

**Side:** `--side in` means the transition happens when this clip appears. `--side out` means when this clip ends.

---

## 10. Example Conversations

### Simple trim and export

> **You:** *"Import my_video.mp4, trim it to start at 5 seconds and end at 30 seconds, then export to trimmed.mp4"*
>
> **Agent:** *"Got it. Importing, trimming from 5s to 30s, exporting..."*
>
> **Agent:** *"Done! Saved to trimmed.mp4"*

### Multi-clip with effects

> **You:** *"I have intro.mp4 and scene.mp4. I want a crossfade between them, and add echo to the intro's audio. Export as video.mp4"*
>
> **Agent:** *"OK. I'll import both, add crossfade transition to the second clip, and apply echo to the first. Proceed with export?"*
>
> **You:** *"Yes"*
>
> **Agent:** *"Done! Saved to video.mp4"*

### Sound effect generation

> **You:** *"Generate a 440Hz tone for 2 seconds and save it as beep.wav"*
>
> **Agent:** *"Done! Generated beep.wav (440Hz sine wave, 2 seconds)"*

### Asking for advice

> **You:** *"I'm making a travel montage with 3 clips. What transitions would you recommend?"*
>
> **Agent:** *"For a slow travel montage, I'd suggest: crossfade transitions (1-2 seconds) for a smooth, cinematic feel. Add a fade in on the first clip and fade out on the last. You could also boost saturation slightly for a more vibrant look. Want me to set this up?"*

### Full creative workflow

> **You:** *"I have a gaming highlight clip that's 10 minutes long. I want to cut it down to just the best 2 minutes, add some echo on the audio for dramatic moments, and export at high quality."*
>
> **Agent:** *"Let's start by importing the clip and looking at what we have... Please tell me the file path."*
>
> **You:** *"C:\Videos\gaming.mp4"*
>
> **Agent:** *"Great, I've imported it. Tell me the time ranges you want to keep (e.g., 0:30-1:00, 3:00-3:30), and I'll trim accordingly."*

---

## 11. Troubleshooting

### Agent doesn't respond to video editing requests

- Make sure you type in **VS Code's chat** panel, not elsewhere
- Try typing "use the video-editor skill to..." at the start
- Try `/edit-video` as a slash command

### "FFmpeg not found" error

FFmpeg is installed (v8.1) and in your PATH, so this shouldn't happen. If it does:
- Run `ffmpeg -version` in a terminal to verify
- Restart VS Code

### Export takes too long

- Longer videos with many effects take more time
- Try requesting `--preset ultrafast` for quicker (but lower quality) exports
- The agent can set this for you — just say "export fast"

### "File not found" when importing

- Provide the **full path** to the video file (e.g., `C:\Videos\clip.mp4`)
- Or make sure you're running from the correct directory

### Still stuck?

Just ask the agent for help:
- *"The export failed, can you help me debug?"*
- *"Why can't I import this file?"*
- *"The video looks wrong after export"**

---

## Quick Start (TL;DR)

```
1. Open VS Code chat
2. Say:  "Import my_video.mp4 and export it after trimming to 10-30 seconds"
3. Wait
4. Play the output file
```

That's it. The agent handles everything in between.