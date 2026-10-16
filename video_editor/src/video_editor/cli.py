"""
CLI Interface
=============
Command-line interface for the video editor using click and rich.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import click
from rich.console import Console
from rich.panel import Panel
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TextColumn,
    TimeElapsedColumn,
)
from rich.table import Table
from rich.tree import Tree

from .editor import VideoEditor
from .hyperframe import (
    AudioEffect,
    AudioEffectType,
    Hyperframe,
    HyperframeSequence,
    TransitionType,
)

console = Console()


# ── Main CLI Group ───────────────────────────────────────────────

@click.group()
@click.version_option(version="0.1.0", prog_name="video-editor")
@click.option("--ffmpeg", "ffmpeg_path", help="Path to FFmpeg executable")
@click.option("--ffprobe", "ffprobe_path", help="Path to FFprobe executable")
@click.option("-v", "--verbose", is_flag=True, help="Enable verbose output")
@click.pass_context
def cli(ctx: click.Context, ffmpeg_path: Optional[str], ffprobe_path: Optional[str], verbose: bool) -> None:
    """Video Editor — Hyperframe-based video editing with FFmpeg and sound effects."""
    ctx.ensure_object(dict)
    ctx.obj["verbose"] = verbose
    editor = VideoEditor(ffmpeg_path=ffmpeg_path, ffprobe_path=ffprobe_path)
    editor.new_project()
    ctx.obj["editor"] = editor


# ── Info / Probe ─────────────────────────────────────────────────

@cli.command()
@click.argument("file_path", type=click.Path(exists=True))
@click.pass_context
def info(ctx: click.Context, file_path: str) -> None:
    """Show information about a media file."""
    editor: VideoEditor = ctx.obj["editor"]
    try:
        info = editor.probe_file(file_path)
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        return

    table = Table(title=f"File Info: {Path(file_path).name}")
    table.add_column("Property", style="cyan")
    table.add_column("Value", style="green")

    table.add_row("File", file_path)
    table.add_row("Duration", f"{info.get('duration', 0):.2f}s")
    if "width" in info:
        table.add_row("Resolution", f"{info['width']}x{info['height']}")
    if "fps" in info:
        table.add_row("FPS", f"{info['fps']:.2f}")

    streams = info.get("streams", [])
    for stream in streams:
        codec_type = stream.get("codec_type", "?")
        codec = stream.get("codec_name", "?")
        table.add_row(f"Stream ({codec_type})", codec)

    console.print(table)


# ── Import ───────────────────────────────────────────────────────

@cli.command()
@click.argument("files", nargs=-1, required=True, type=click.Path(exists=True))
@click.option("--sequence", "-s", "sequence_name", default="main", help="Target sequence")
@click.pass_context
def import_cmd(ctx: click.Context, files: Tuple[str, ...], sequence_name: str) -> None:
    """Import media files into the project."""
    editor: VideoEditor = ctx.obj["editor"]

    if sequence_name not in editor.sequences:
        editor.create_sequence(sequence_name)

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TimeElapsedColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("Importing files...", total=len(files))
        imported = []
        for fp in files:
            try:
                hf = editor.import_clip(fp, sequence_name=sequence_name)
                imported.append((Path(fp).name, hf))
            except Exception as e:
                console.print(f"[red]Failed to import {fp}:[/red] {e}")
            progress.advance(task)

    table = Table(title=f"Imported {len(imported)} files")
    table.add_column("Clip", style="cyan")
    table.add_column("Duration", style="green")
    table.add_column("HF ID", style="dim")

    for name, hf in imported:
        dur = f"{hf.duration:.2f}s" if hf.duration else "?"
        table.add_row(name, dur, hf.id)

    console.print(table)


# ── Sequence ─────────────────────────────────────────────────────

@cli.command()
@click.argument("name", default="main")
@click.option("--fps", default=30.0, type=float, help="Frame rate")
@click.option("--width", default=1920, type=int, help="Width in pixels")
@click.option("--height", default=1080, type=int, help="Height in pixels")
@click.pass_context
def sequence(ctx: click.Context, name: str, fps: float, width: int, height: int) -> None:
    """Create or switch to a sequence."""
    editor: VideoEditor = ctx.obj["editor"]

    if name in editor.sequences:
        editor.active_sequence = editor.sequences[name]
        console.print(f"[green]Switched to sequence:[/green] {name}")
    else:
        seq = editor.create_sequence(name, fps=fps, width=width, height=height)
        console.print(f"[green]Created sequence:[/green] {name} ({width}x{height} @ {fps}fps)")


@cli.command(name="list")
@click.pass_context
def list_cmd(ctx: click.Context) -> None:
    """List all sequences and their clips."""
    editor: VideoEditor = ctx.obj["editor"]

    if not editor.sequences:
        console.print("[yellow]No sequences in project.[/yellow]")
        return

    for seq_name, seq in editor.sequences.items():
        panel = Panel(
            f"FPS: {seq.fps}  |  Resolution: {seq.width}x{seq.height}  |  "
            f"Duration: {seq.total_duration:.2f}s",
            title=f"[bold cyan]Sequence: {seq_name}[/]",
            title_align="left",
        )
        console.print(panel)

        if not seq.frames:
            console.print("  [dim](empty)[/dim]")
            continue

        table = Table(box=None)
        table.add_column("#", style="dim", width=4)
        table.add_column("Clip", style="cyan")
        table.add_column("Duration", style="green", width=10)
        table.add_column("Source", style="white", no_wrap=True)
        table.add_column("Effects", style="yellow", width=16)

        for i, hf in enumerate(seq.frames):
            src = hf.metadata.source_clip_name or Path(hf.source or "?").name if hf.source else "?"
            dur = f"{hf.duration:.2f}s" if hf.duration else "?"
            eff_count = f"{len(hf.effects)}v, {len(hf.audio_effects)}a"
            table.add_row(str(i), src, dur, src, eff_count)

        console.print(table)


# ── Effects ──────────────────────────────────────────────────────

@cli.command()
@click.argument("clip_index", type=int)
@click.argument("effect_type")
@click.option("--sequence", "-s", default="main", help="Sequence name")
@click.option("--param", "-p", "params", multiple=True, help="Parameters as key=value")
@click.pass_context
def effect(ctx: click.Context, clip_index: int, effect_type: str, sequence: str, params: Tuple[str, ...]) -> None:
    """Add a video effect to a clip."""
    editor: VideoEditor = ctx.obj["editor"]
    parsed_params: Dict[str, str] = {}
    for p in params:
        if "=" in p:
            k, v = p.split("=", 1)
            parsed_params[k] = v

    try:
        eff = editor.add_video_effect(sequence, clip_index, effect_type, **parsed_params)
        console.print(f"[green]Added effect:[/green] {eff.type} to clip #{clip_index}")
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")


@cli.command()
@click.argument("clip_index", type=int)
@click.argument("effect_type", type=click.Choice([e.value for e in AudioEffectType]))
@click.option("--sequence", "-s", default="main", help="Sequence name")
@click.option("--param", "-p", "params", multiple=True, help="Parameters as key=value")
@click.pass_context
def audio_effect(ctx: click.Context, clip_index: int, effect_type: str, sequence: str, params: Tuple[str, ...]) -> None:
    """Add an audio effect to a clip."""
    editor: VideoEditor = ctx.obj["editor"]
    parsed_params: Dict[str, str] = {}
    for p in params:
        if "=" in p:
            k, v = p.split("=", 1)
            parsed_params[k] = v

    try:
        ae_type = AudioEffectType(effect_type)
        ae = editor.add_audio_effect(sequence, clip_index, ae_type, **parsed_params)
        console.print(f"[green]Added audio effect:[/green] {ae.type.value} to clip #{clip_index}")
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")


# ── Transitions ──────────────────────────────────────────────────

@cli.command()
@click.argument("clip_index", type=int)
@click.argument("transition_type", type=click.Choice([t.value for t in TransitionType]))
@click.option("--duration", "-d", default=1.0, type=float, help="Transition duration (seconds)")
@click.option("--side", type=click.Choice(["in", "out"]), default="in", help="Transition side")
@click.option("--sequence", "-s", default="main", help="Sequence name")
@click.pass_context
def transition(
    ctx: click.Context,
    clip_index: int,
    transition_type: str,
    duration: float,
    side: str,
    sequence: str,
) -> None:
    """Set a transition on a clip."""
    editor: VideoEditor = ctx.obj["editor"]
    try:
        editor.set_transition(sequence, clip_index, TransitionType(transition_type), duration, side)
        console.print(f"[green]Set {transition_type} transition ({side}) on clip #{clip_index}, {duration}s[/green]")
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")


# ── Split ────────────────────────────────────────────────────────

@cli.command()
@click.argument("clip_index", type=int)
@click.argument("time", type=float)
@click.option("--sequence", "-s", default="main", help="Sequence name")
@click.pass_context
def split(ctx: click.Context, clip_index: int, time: float, sequence: str) -> None:
    """Split a clip at the given time (seconds)."""
    editor: VideoEditor = ctx.obj["editor"]
    try:
        left, right = editor.split_clip(sequence, clip_index, time)
        console.print(f"[green]Split clip #{clip_index} at {time}s[/green]")
        console.print(f"  Left:  {left.id} ({left.duration:.2f}s)")
        console.print(f"  Right: {right.id} ({right.duration:.2f}s)")
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")


# ── Audio / Sound Generation ─────────────────────────────────────

@cli.command()
@click.argument("output", type=click.Path())
@click.option("--type", "effect_type", default="tone", help="Sound type: tone, noise, silence")
@click.option("--frequency", "-freq", default=440.0, type=float, help="Frequency in Hz")
@click.option("--duration", "-dur", default=1000.0, type=float, help="Duration in ms")
@click.option("--volume", "-vol", default=-10.0, type=float, help="Volume in dBFS")
@click.pass_context
def generate_sound(ctx: click.Context, output: str, effect_type: str, frequency: float, duration: float, volume: float) -> None:
    """Generate a synthesized sound effect."""
    editor: VideoEditor = ctx.obj["editor"]
    try:
        path = editor.generate_sound_effect(output, effect_type, frequency, duration, volume)
        console.print(f"[green]Generated sound:[/green] {path}")
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")


# ── Export ───────────────────────────────────────────────────────

@cli.command()
@click.argument("output", type=click.Path())
@click.option("--sequence", "-s", default="main", help="Sequence to export")
@click.option("--preset", default="medium", type=click.Choice(["ultrafast", "fast", "medium", "slow", "veryslow"]), help="x264 preset")
@click.option("--crf", default=23, type=int, help="Quality (0-51, lower = better)")
@click.option("--codec", default="libx264", help="Video codec")
@click.pass_context
def export(ctx: click.Context, output: str, sequence: str, preset: str, crf: int, codec: str) -> None:
    """Render and export the sequence to a video file."""
    editor: VideoEditor = ctx.obj["editor"]

    if sequence not in editor.sequences:
        console.print(f"[red]Sequence '{sequence}' not found.[/red]")
        return

    seq = editor.sequences[sequence]
    console.print(f"[cyan]Rendering sequence '{sequence}'...[/cyan]")
    console.print(f"  Clips: {seq.count}  |  Duration: {seq.total_duration:.2f}s")
    console.print(f"  Preset: {preset}  |  CRF: {crf}  |  Codec: {codec}")
    console.print(f"  Output: {output}")

    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            progress.add_task("[cyan]Rendering...[/cyan]", total=None)
            result = editor.export_sequence(output, sequence, preset=preset, crf=crf, codec=codec)

        console.print(f"[green]✓ Exported to:[/green] {result}")

        # Show file size
        file_size = os.path.getsize(result)
        if file_size > 1024 * 1024:
            console.print(f"  Size: {file_size / (1024*1024):.1f} MB")
        else:
            console.print(f"  Size: {file_size / 1024:.1f} KB")

    except Exception as e:
        console.print(f"[red]Export failed:[/red] {e}")


@cli.command()
@click.argument("output", type=click.Path())
@click.argument("source", type=click.Path(exists=True), required=False)
@click.option("--sequence", "-s", help="Sequence name (alternative to source file)")
@click.option("--effect", "-e", "effects", multiple=True, help="Audio effects (e.g., echo delay=300)")
@click.pass_context
def export_audio(ctx: click.Context, output: str, source: Optional[str], sequence: Optional[str], effects: Tuple[str, ...]) -> None:
    """Export audio from a video file or sequence."""
    editor: VideoEditor = ctx.obj["editor"]

    parsed_effects: List[AudioEffect] = []
    for eff_str in effects:
        parts = eff_str.split()
        if parts:
            ae = AudioEffect(type=AudioEffectType(parts[0]))
            for param in parts[1:]:
                if "=" in param:
                    k, v = param.split("=", 1)
                    try:
                        ae.params[k] = float(v)
                    except ValueError:
                        ae.params[k] = v
            parsed_effects.append(ae)

    try:
        result = editor.export_audio(output, source_path=source, effects=parsed_effects or None, sequence_name=sequence)
        console.print(f"[green]✓ Exported audio:[/green] {result}")
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")


# ── Project Save / Load ──────────────────────────────────────────

@cli.command()
@click.argument("file_path", type=click.Path())
@click.pass_context
def save(ctx: click.Context, file_path: str) -> None:
    """Save the current project to a JSON file."""
    editor: VideoEditor = ctx.obj["editor"]
    try:
        result = editor.save_project(file_path)
        console.print(f"[green]✓ Project saved:[/green] {result}")
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")


@cli.command()
@click.argument("file_path", type=click.Path(exists=True))
@click.pass_context
def load(ctx: click.Context, file_path: str) -> None:
    """Load a project from a JSON file."""
    editor: VideoEditor = ctx.obj["editor"]
    try:
        editor.load_project(file_path)
        console.print(f"[green]✓ Project loaded:[/green] {file_path}")
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")


# ── Trim ─────────────────────────────────────────────────────────

@cli.command()
@click.argument("clip_index", type=int)
@click.argument("start", type=float)
@click.argument("end", type=float)
@click.option("--sequence", "-s", default="main", help="Sequence name")
@click.pass_context
def trim(ctx: click.Context, clip_index: int, start: float, end: float, sequence: str) -> None:
    """Trim a clip to a new start/end time (seconds)."""
    editor: VideoEditor = ctx.obj["editor"]
    try:
        editor.trim_clip(sequence, clip_index, start, end)
        console.print(f"[green]Trimmed clip #{clip_index} to [{start}s - {end}s][/green]")
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")


if __name__ == "__main__":
    cli()