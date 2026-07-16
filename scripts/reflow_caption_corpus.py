#!/usr/bin/env python3
"""Reflow fragmented WebVTT captions without changing their spoken meaning."""

from __future__ import annotations

import argparse
import json
import re
import sys
import textwrap
from dataclasses import dataclass
from pathlib import Path
from typing import Pattern

from validate_caption_corpus import Cue, parse_webvtt, video_duration


SENTENCE_END_RE = re.compile(r"[.!?][\"']?$")
VOICE_TAG_RE = re.compile(r"<v\s+[^>]+>")


@dataclass(frozen=True)
class ReflowedCue:
    start: float
    end: float
    lines: tuple[str, ...]
    voice_tag: str | None = None

    @property
    def text(self) -> str:
        return " ".join(self.lines)


def wrap_caption(text: str, width: int = 42) -> tuple[str, ...]:
    return tuple(
        textwrap.wrap(
            " ".join(text.split()),
            width=width,
            break_long_words=False,
            break_on_hyphens=False,
        )
    )


def load_glossary(path: Path | None) -> list[tuple[Pattern[str], str]]:
    if path is None:
        return []
    payload = json.loads(path.read_text(encoding="utf-8"))
    return [
        (re.compile(item["pattern"], re.IGNORECASE), item["replacement"])
        for item in payload.get("replacements", [])
    ]


def apply_glossary(
    text: str, replacements: list[tuple[Pattern[str], str]]
) -> tuple[str, int]:
    total = 0
    for pattern, replacement in replacements:
        text, count = pattern.subn(replacement, text)
        total += count
    return text, total


def cue_voice_tag(cue: Cue) -> str | None:
    match = VOICE_TAG_RE.search(" ".join(cue.lines))
    return match.group(0) if match else None


def can_merge(
    current: ReflowedCue,
    following: Cue,
    *,
    width: int,
    max_lines: int,
    max_duration: float,
    max_gap: float,
) -> bool:
    gap = following.start - current.end
    combined_text = f"{current.text} {following.text}".strip()
    return (
        not SENTENCE_END_RE.search(current.text)
        and -0.001 <= gap <= max_gap
        and following.end - current.start <= max_duration
        and cue_voice_tag(following) in {None, current.voice_tag}
        and len(wrap_caption(combined_text, width)) <= max_lines
    )


def reflow_cues(
    cues: list[Cue],
    *,
    width: int = 42,
    max_lines: int = 2,
    max_duration: float = 7.0,
    max_gap: float = 0.75,
    target_cps: float = 20.0,
    final_end: float | None = None,
) -> list[ReflowedCue]:
    if not cues:
        return []

    reflowed: list[ReflowedCue] = []
    current = ReflowedCue(
        start=cues[0].start,
        end=cues[0].end,
        lines=wrap_caption(cues[0].text, width),
        voice_tag=cue_voice_tag(cues[0]),
    )
    for cue in cues[1:]:
        if can_merge(
            current,
            cue,
            width=width,
            max_lines=max_lines,
            max_duration=max_duration,
            max_gap=max_gap,
        ):
            current = ReflowedCue(
                start=current.start,
                end=cue.end,
                lines=wrap_caption(f"{current.text} {cue.text}", width),
                voice_tag=current.voice_tag,
            )
            continue

        reflowed.append(current)
        current = ReflowedCue(
            start=cue.start,
            end=cue.end,
            lines=wrap_caption(cue.text, width),
            voice_tag=cue_voice_tag(cue),
        )
    reflowed.append(current)
    return extend_fast_cues(
        reflowed,
        max_duration=max_duration,
        target_cps=target_cps,
        final_end=final_end,
    )


def extend_fast_cues(
    cues: list[ReflowedCue],
    *,
    max_duration: float,
    target_cps: float,
    transition_margin: float = 0.04,
    final_end: float | None = None,
) -> list[ReflowedCue]:
    """Use available post-speech silence to make fast cues easier to read."""
    extended: list[ReflowedCue] = []
    for index, cue in enumerate(cues):
        if not cue.text:
            extended.append(cue)
            continue
        needed_end = cue.start + len(cue.text) / target_cps
        if index == len(cues) - 1:
            if final_end is None:
                extended.append(cue)
                continue
            next_boundary = final_end
        else:
            next_boundary = cues[index + 1].start
        available_end = min(
            next_boundary - transition_margin,
            cue.start + max_duration,
        )
        end = max(cue.end, min(needed_end, available_end))
        extended.append(
            ReflowedCue(
                start=cue.start,
                end=end,
                lines=cue.lines,
                voice_tag=cue.voice_tag,
            )
        )
    return extended


def timestamp(seconds: float) -> str:
    milliseconds = round(seconds * 1000)
    hours, remainder = divmod(milliseconds, 3_600_000)
    minutes, remainder = divmod(remainder, 60_000)
    whole_seconds, milliseconds = divmod(remainder, 1000)
    return f"{hours:02d}:{minutes:02d}:{whole_seconds:02d}.{milliseconds:03d}"


def render_webvtt(cues: list[ReflowedCue]) -> str:
    blocks = ["WEBVTT"]
    for number, cue in enumerate(cues, start=1):
        lines = list(cue.lines)
        if cue.voice_tag and lines:
            lines[0] = f"{cue.voice_tag}{lines[0]}"
        blocks.append(
            "\n".join(
                [
                    str(number),
                    f"{timestamp(cue.start)} --> {timestamp(cue.end)}",
                    *lines,
                ]
            )
        )
    return "\n\n".join(blocks) + "\n"


def reflow_file(
    source: Path,
    destination: Path,
    args: argparse.Namespace,
    replacements: list[tuple[Pattern[str], str]],
) -> dict:
    source_text, replacement_count = apply_glossary(
        source.read_text(encoding="utf-8-sig"), replacements
    )
    cues, errors = parse_webvtt(source_text)
    if errors:
        return {
            "file": source.as_posix(),
            "before": len(cues),
            "after": 0,
            "replacements": replacement_count,
            "errors": errors,
        }
    final_end = None
    if args.video_root is not None:
        relative = source.relative_to(args.input_root).with_suffix(".mp4")
        video_path = args.video_root / relative
        if not video_path.is_file():
            return {
                "file": source.as_posix(),
                "before": len(cues),
                "after": 0,
                "replacements": replacement_count,
                "errors": ["paired video is missing"],
            }
        final_end = video_duration(video_path, args.ffprobe)
    reflowed = reflow_cues(
        cues,
        width=args.width,
        max_lines=args.max_lines,
        max_duration=args.max_duration,
        max_gap=args.max_gap,
        target_cps=args.target_cps,
        final_end=final_end,
    )
    source_spoken_text = " ".join(cue.text for cue in cues)
    output_spoken_text = " ".join(cue.text for cue in reflowed)
    if source_spoken_text != output_spoken_text:
        return {
            "file": source.as_posix(),
            "before": len(cues),
            "after": len(reflowed),
            "replacements": replacement_count,
            "errors": ["reflow changed the spoken text"],
        }
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(render_webvtt(reflowed), encoding="utf-8")
    return {
        "file": source.as_posix(),
        "before": len(cues),
        "after": len(reflowed),
        "replacements": replacement_count,
        "spoken_text_preserved": True,
        "errors": [],
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-root", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--video-root", type=Path)
    parser.add_argument("--ffprobe", default="ffprobe")
    parser.add_argument("--width", type=int, default=42)
    parser.add_argument("--max-lines", type=int, default=2)
    parser.add_argument("--max-duration", type=float, default=7.0)
    parser.add_argument("--max-gap", type=float, default=0.75)
    parser.add_argument("--target-cps", type=float, default=20.0)
    parser.add_argument("--glossary", type=Path)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if args.input_root.resolve() == args.output_root.resolve():
        print("input and output roots must be different", file=sys.stderr)
        return 2
    replacements = load_glossary(args.glossary)
    sources = sorted(args.input_root.rglob("*.vtt"))
    results = [
        reflow_file(
            source,
            args.output_root / source.relative_to(args.input_root),
            args,
            replacements,
        )
        for source in sources
    ]
    report = {
        "files": len(results),
        "passed": sum(not result["errors"] for result in results),
        "failed": sum(bool(result["errors"]) for result in results),
        "cues_before": sum(result["before"] for result in results),
        "cues_after": sum(result["after"] for result in results),
        "replacements": sum(result["replacements"] for result in results),
        "results": results,
    }
    print(json.dumps(report, indent=2))
    return 1 if report["failed"] else 0


if __name__ == "__main__":
    sys.exit(main())
