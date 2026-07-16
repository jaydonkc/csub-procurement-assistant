import importlib.util
import re
import sys
import unittest
from pathlib import Path


VALIDATOR_PATH = Path(__file__).with_name("validate_caption_corpus.py")
VALIDATOR_SPEC = importlib.util.spec_from_file_location(
    "validate_caption_corpus", VALIDATOR_PATH
)
validator = importlib.util.module_from_spec(VALIDATOR_SPEC)
assert VALIDATOR_SPEC.loader is not None
sys.modules[VALIDATOR_SPEC.name] = validator
VALIDATOR_SPEC.loader.exec_module(validator)

MODULE_PATH = Path(__file__).with_name("reflow_caption_corpus.py")
SPEC = importlib.util.spec_from_file_location("reflow_caption_corpus", MODULE_PATH)
reflow = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = reflow
SPEC.loader.exec_module(reflow)


class CaptionReflowTests(unittest.TestCase):
    def test_merges_fragments_and_wraps_complete_sentence(self):
        cues = [
            validator.Cue(6.38, 7.34, ("In this video,",)),
            validator.Cue(7.46, 9.06, ("you will learn how to approve,",)),
            validator.Cue(9.46, 9.92, ("return,",)),
            validator.Cue(10.06, 12.079, ("and reject requisitions.",)),
        ]

        result = reflow.reflow_cues(cues)

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].start, 6.38)
        self.assertEqual(result[0].end, 12.079)
        self.assertLessEqual(len(result[0].lines), 2)
        self.assertEqual(
            result[0].text,
            "In this video, you will learn how to approve, return, and reject requisitions.",
        )

    def test_does_not_merge_across_sentence_or_long_gap(self):
        cues = [
            validator.Cue(0.0, 1.0, ("First sentence.",)),
            validator.Cue(1.1, 2.0, ("Second",)),
            validator.Cue(3.0, 4.0, ("thought",)),
        ]

        result = reflow.reflow_cues(cues)

        self.assertEqual([cue.text for cue in result], ["First sentence.", "Second", "thought"])

    def test_preserves_voice_boundaries_and_sound_descriptions(self):
        cues = [
            validator.Cue(0.0, 1.0, ("<v Instructor>Open",)),
            validator.Cue(1.1, 2.0, ("the menu.",)),
            validator.Cue(2.1, 3.0, ("[Keyboard clicks]",)),
        ]

        result = reflow.reflow_cues(cues)
        rendered = reflow.render_webvtt(result)

        self.assertIn("<v Instructor>Open the menu.", rendered)
        self.assertIn("[Keyboard clicks]", rendered)

    def test_timestamp_rolls_milliseconds_into_next_second(self):
        self.assertEqual(reflow.timestamp(59.9996), "00:01:00.000")

    def test_glossary_corrects_domain_terms_case_insensitively(self):
        replacements = [
            (re.compile(r"\bCSU\s+(?:buy|by|b)\b", re.IGNORECASE), "CSUBUY"),
            (re.compile(r"\bJagger\b", re.IGNORECASE), "JAGGAER"),
        ]

        text, count = reflow.apply_glossary(
            "Return to CSU by from the Jagger system.", replacements
        )

        self.assertEqual(text, "Return to CSUBUY from the JAGGAER system.")
        self.assertEqual(count, 2)

    def test_fast_cue_lingers_into_available_silence(self):
        cues = [
            reflow.ReflowedCue(0.0, 1.0, ("This caption needs more time.",)),
            reflow.ReflowedCue(3.0, 4.0, ("Next caption.",)),
        ]

        result = reflow.extend_fast_cues(
            cues,
            max_duration=7.0,
            target_cps=20.0,
        )

        self.assertEqual(result[0].end, len(result[0].text) / 20.0)
        self.assertEqual(result[1], cues[1])

    def test_final_fast_cue_uses_verified_video_tail(self):
        cues = [
            reflow.ReflowedCue(10.0, 11.0, ("Final caption needs more time.",)),
        ]

        result = reflow.extend_fast_cues(
            cues,
            max_duration=7.0,
            target_cps=20.0,
            final_end=15.0,
        )

        self.assertEqual(result[0].end, 10 + len(result[0].text) / 20.0)


if __name__ == "__main__":
    unittest.main()
