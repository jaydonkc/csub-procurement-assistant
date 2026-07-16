#!/usr/bin/env python3
"""Validate the approved WebVTT corpus paired with public training videos."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path, PurePosixPath
from typing import Any


TIMING_RE = re.compile(
    r"^(?P<start>(?:\d{2}:)?\d{2}:\d{2}\.\d{3})\s+-->\s+"
    r"(?P<end>(?:\d{2}:)?\d{2}:\d{2}\.\d{3})(?:\s+.*)?$"
)
VOICE_RE = re.compile(r"<v\s+[^>]+>|^(?:[A-Z][A-Z0-9 .'-]{1,30}):")
SOUND_RE = re.compile(r"\[[^\]]+\]")
TAG_RE = re.compile(r"<[^>]+>")


@dataclass(frozen=True)
class Cue:
    start: float
    end: float
    lines: tuple[str, ...]

    @property
    def text(self) -> str:
        return " ".join(TAG_RE.sub("", line).strip() for line in self.lines).strip()


@dataclass
class CaptionResult:
    video: str
    caption: str
    cues: int = 0
    speaker_cues: int = 0
    sound_cues: int = 0
    caption_end: float | None = None
    video_duration: float | None = None
    errors: list[str] | None = None
    warnings: list[str] | None = None

    def __post_init__(self) -> None:
        self.errors = [] if self.errors is None else self.errors
        self.warnings = [] if self.warnings is None else self.warnings


def timestamp_seconds(value: str) -> float:
    parts = value.split(":")
    if len(parts) == 2:
        hours = 0
        minutes, seconds = parts
    elif len(parts) == 3:
        hours, minutes, seconds = parts
    else:
        raise ValueError(f"invalid timestamp: {value}")
    return int(hours) * 3600 + int(minutes) * 60 + float(seconds)


def parse_webvtt(text: str) -> tuple[list[Cue], list[str]]:
    lines = text.lstrip("\ufeff").replace("\r\n", "\n").split("\n")
    errors: list[str] = []
    if not lines or lines[0].strip() != "WEBVTT":
        return [], ["missing WEBVTT header"]

    cues: list[Cue] = []
    index = 1
    while index < len(lines):
        line = lines[index].strip()
        if not line:
            index += 1
            continue
        if line.startswith(("NOTE", "STYLE", "REGION")):
            index += 1
            while index < len(lines) and lines[index].strip():
                index += 1
            continue

        timing = TIMING_RE.match(line)
        if timing is None and index + 1 < len(lines):
            index += 1
            line = lines[index].strip()
            timing = TIMING_RE.match(line)
        if timing is None:
            errors.append(f"line {index + 1}: invalid cue timing")
            index += 1
            continue

        start = timestamp_seconds(timing.group("start"))
        end = timestamp_seconds(timing.group("end"))
        index += 1
        cue_lines: list[str] = []
        while index < len(lines) and lines[index].strip():
            cue_lines.append(lines[index].strip())
            index += 1
        cues.append(Cue(start=start, end=end, lines=tuple(cue_lines)))

    return cues, errors


def policy_video_paths(policy_path: Path) -> list[PurePosixPath]:
    policy = json.loads(policy_path.read_text(encoding="utf-8"))
    resources = [
        resource
        for statement in policy.get("Statement", [])
        for resource in statement.get("Resource", [])
        if resource.endswith(".mp4") and "/media/videos/" in resource
    ]
    return sorted(
        PurePosixPath(resource.split("/media/videos/", 1)[1])
        for resource in resources
    )


def local_path(root: Path, relative: PurePosixPath) -> Path:
    return root.joinpath(*relative.parts)


def video_duration(video_path: Path, ffprobe: str) -> float:
    completed = subprocess.run(
        [
            ffprobe,
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(video_path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    return float(completed.stdout.strip())


def validate_pair(
    video_relative: PurePosixPath,
    caption_root: Path,
    video_root: Path | None = None,
    ffprobe: str = "ffprobe",
) -> CaptionResult:
    caption_relative = video_relative.with_suffix(".vtt")
    caption_path = local_path(caption_root, caption_relative)
    result = CaptionResult(video=str(video_relative), caption=str(caption_relative))
    if not caption_path.is_file():
        result.errors.append("caption file is missing")
        return result

    cues, parse_errors = parse_webvtt(caption_path.read_text(encoding="utf-8-sig"))
    result.errors.extend(parse_errors)
    result.cues = len(cues)
    if not cues:
        result.errors.append("caption file contains no cues")
        return result

    previous_start = -1.0
    for number, cue in enumerate(cues, start=1):
        if cue.end <= cue.start:
            result.errors.append(f"cue {number}: end must follow start")
        if cue.start < previous_start:
            result.errors.append(f"cue {number}: cues are not time ordered")
        if not cue.text:
            result.errors.append(f"cue {number}: caption text is empty")
        duration = cue.end - cue.start
        if duration > 7:
            result.warnings.append(f"cue {number}: duration exceeds 7 seconds")
        if len(cue.lines) > 2:
            result.warnings.append(f"cue {number}: more than two lines")
        if any(len(TAG_RE.sub("", line)) > 42 for line in cue.lines):
            result.warnings.append(f"cue {number}: line exceeds 42 characters")
        if duration > 0 and len(cue.text) / duration > 20 + 1e-6:
            result.warnings.append(f"cue {number}: reading speed exceeds 20 cps")
        if VOICE_RE.search(" ".join(cue.lines)):
            result.speaker_cues += 1
        if SOUND_RE.search(cue.text):
            result.sound_cues += 1
        previous_start = cue.start

    result.caption_end = cues[-1].end
    if video_root is not None:
        video_path = local_path(video_root, video_relative)
        if not video_path.is_file():
            result.errors.append("video file is missing")
        else:
            try:
                result.video_duration = video_duration(video_path, ffprobe)
                if result.caption_end > result.video_duration + 0.5:
                    result.errors.append("caption cues extend beyond the video duration")
            except (OSError, subprocess.CalledProcessError, ValueError) as error:
                result.errors.append(f"could not inspect video duration: {error}")
    return result


def build_report(args: argparse.Namespace) -> dict[str, Any]:
    if args.all_discovered:
        if args.video_root is None:
            raise ValueError("--all-discovered requires --video-root")
        videos = sorted(
            PurePosixPath(path.relative_to(args.video_root).as_posix())
            for path in args.video_root.rglob("*.mp4")
        )
    else:
        videos = policy_video_paths(args.policy)
    results = [
        validate_pair(video, args.caption_root, args.video_root, args.ffprobe)
        for video in videos
    ]
    warnings = [warning for result in results for warning in result.warnings]
    return {
        "videos": len(results),
        "scope": "all_discovered" if args.all_discovered else "public_allowlist",
        "passed": sum(not result.errors for result in results),
        "failed": sum(bool(result.errors) for result in results),
        "manual_audio_review_required": True,
        "summary": {
            "cues": sum(result.cues for result in results),
            "line_length_warnings": sum(
                "line exceeds 42 characters" in warning for warning in warnings
            ),
            "reading_speed_warnings": sum(
                "reading speed exceeds 20 cps" in warning for warning in warnings
            ),
            "duration_warnings": sum(
                "duration exceeds 7 seconds" in warning for warning in warnings
            ),
            "speaker_cues": sum(result.speaker_cues for result in results),
            "sound_cues": sum(result.sound_cues for result in results),
        },
        "results": [asdict(result) for result in results],
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--caption-root", type=Path, required=True)
    parser.add_argument("--video-root", type=Path)
    parser.add_argument(
        "--policy",
        type=Path,
        default=Path("infra/public-training-video-policy.json"),
    )
    parser.add_argument("--ffprobe", default="ffprobe")
    parser.add_argument("--report", type=Path)
    parser.add_argument("--all-discovered", action="store_true")
    parser.add_argument("--summary-only", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        report = build_report(args)
    except ValueError as error:
        print(str(error), file=sys.stderr)
        return 2
    output = json.dumps(report, indent=2)
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(output + "\n", encoding="utf-8")
    if args.summary_only:
        print(
            json.dumps(
                {
                    "videos": report["videos"],
                    "scope": report["scope"],
                    "passed": report["passed"],
                    "failed": report["failed"],
                    "manual_audio_review_required": report[
                        "manual_audio_review_required"
                    ],
                    "summary": report["summary"],
                },
                indent=2,
            )
        )
    else:
        print(output)
    return 1 if report["failed"] else 0


if __name__ == "__main__":
    sys.exit(main())
