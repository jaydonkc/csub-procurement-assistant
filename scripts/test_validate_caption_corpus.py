import importlib.util
import argparse
import sys
import tempfile
import unittest
from pathlib import Path, PurePosixPath


MODULE_PATH = Path(__file__).with_name("validate_caption_corpus.py")
SPEC = importlib.util.spec_from_file_location("validate_caption_corpus", MODULE_PATH)
caption_validation = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = caption_validation
SPEC.loader.exec_module(caption_validation)


class CaptionValidationTests(unittest.TestCase):
    def test_valid_caption_reports_speaker_and_sound_annotations(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            caption = root / "Training" / "Example.vtt"
            caption.parent.mkdir(parents=True)
            caption.write_text(
                "WEBVTT\n\n"
                "00:00:00.000 --> 00:00:02.000\n"
                "<v Instructor>Open the Orders menu.\n\n"
                "00:00:02.100 --> 00:00:04.000\n"
                "[Keyboard clicks]\n",
                encoding="utf-8",
            )

            result = caption_validation.validate_pair(
                PurePosixPath("Training/Example.mp4"), root
            )

            self.assertEqual(result.errors, [])
            self.assertEqual(result.cues, 2)
            self.assertEqual(result.speaker_cues, 1)
            self.assertEqual(result.sound_cues, 1)

    def test_report_includes_aggregate_accessibility_counts(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            caption = root / "Training" / "Example.vtt"
            caption.parent.mkdir(parents=True)
            caption.write_text(
                "WEBVTT\n\n"
                "00:00:00.000 --> 00:00:01.000\n"
                "This caption is intentionally much too long and much too fast.\n",
                encoding="utf-8",
            )
            policy = root / "policy.json"
            policy.write_text(
                '{"Statement":[{"Resource":['
                '"arn:aws:s3:::example/media/videos/Training/Example.mp4"'
                "]}]}",
                encoding="utf-8",
            )
            args = argparse.Namespace(
                all_discovered=False,
                video_root=None,
                policy=policy,
                caption_root=root,
                ffprobe="ffprobe",
            )

            report = caption_validation.build_report(args)

        self.assertEqual(report["summary"]["cues"], 1)
        self.assertEqual(report["summary"]["line_length_warnings"], 1)
        self.assertEqual(report["summary"]["reading_speed_warnings"], 1)

    def test_missing_caption_fails_validation(self):
        with tempfile.TemporaryDirectory() as directory:
            result = caption_validation.validate_pair(
                PurePosixPath("Training/Missing.mp4"), Path(directory)
            )

            self.assertIn("caption file is missing", result.errors)

    def test_invalid_timing_and_empty_text_fail_validation(self):
        cues, errors = caption_validation.parse_webvtt(
            "WEBVTT\n\n00:00:03.000 --> 00:00:02.000\n\n"
        )

        self.assertEqual(errors, [])
        self.assertEqual(len(cues), 1)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            caption = root / "Broken.vtt"
            caption.write_text(
                "WEBVTT\n\n00:00:03.000 --> 00:00:02.000\n\n",
                encoding="utf-8",
            )
            result = caption_validation.validate_pair(
                PurePosixPath("Broken.mp4"), root
            )
        self.assertIn("cue 1: end must follow start", result.errors)
        self.assertIn("cue 1: caption text is empty", result.errors)

    def test_all_discovered_mode_requires_video_root(self):
        args = argparse.Namespace(
            all_discovered=True,
            video_root=None,
            policy=Path("unused.json"),
            caption_root=Path("unused"),
            ffprobe="ffprobe",
        )

        with self.assertRaisesRegex(ValueError, "requires --video-root"):
            caption_validation.build_report(args)


if __name__ == "__main__":
    unittest.main()
