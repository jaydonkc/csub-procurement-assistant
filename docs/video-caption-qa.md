# Video Caption QA

## Scope

The canonical source bucket contains 17 MP4 training videos and 17 approved WebVTT transcripts. Eleven videos pass the public-source boundary and can appear in the public assistant; six internal/admin videos remain intentionally unavailable in the public UI. The caption validator supports both the eleven-video public allowlist and all discovered private videos.

## Implementation

- The backend maps each public `*.mp4` source to the matching `approved/transcripts/*.vtt` object.
- Video and caption URLs are signed independently for 15 minutes. A caption-signing failure does not remove an otherwise valid video URL.
- The API returns the caption as `caption_url` without indexing it as a second source.
- The existing native video element includes an English `kind="captions"` track, marks it as default, and switches the loaded text track to `showing`.
- If a caption is missing or fails to load, the source panel announces a readable transcript-summary fallback.
- The source bucket CORS configuration permits read-only media requests from production and the two supported local-development origins.
- The IAM policy grants the Lambda role access only to the eleven public MP4/VTT pairs.

## Automated Validation

`scripts/validate_caption_corpus.py` checks every selected video/caption pair for:

- a present VTT file and valid `WEBVTT` header;
- valid, ordered cue timestamps and nonempty cue text;
- cues that do not extend beyond the MP4 duration when `ffprobe` is available;
- cue duration, line count, line length, and reading-speed warnings;
- counts of WebVTT voice labels and bracketed sound descriptions for manual review.

To validate all 17 canonical videos after authenticating the `calpoly` AWS profile:

```powershell
aws s3 sync s3://csub-pa-mvp-source-335010339891-us-west-2/approved/transcripts/ tmp/caption-audit/captions/ --profile calpoly --region us-west-2
aws s3 sync s3://csub-pa-mvp-source-335010339891-us-west-2/media/videos/ tmp/caption-audit/videos/ --profile calpoly --region us-west-2
py scripts/validate_caption_corpus.py --caption-root tmp/caption-audit/captions --video-root tmp/caption-audit/videos --all-discovered --report tmp/caption-audit/report.json --summary-only
```

Passing structural validation is not a substitute for listening. A human reviewer must watch each video with captions enabled and confirm verbatim meaning, synchronization, and descriptions of relevant non-speech audio. Speaker identification was excluded from this project's caption scope by the product owner on July 16, 2026, so no paid diarization jobs will be run.

### Corpus Audit Results

The `calpoly` profile was verified against AWS account `335010339891` on July 16, 2026. The private audit downloaded all 17 MP4/VTT pairs and the 17 retained Amazon Transcribe JSON results. Bucket versioning is enabled.

| Check | Original approved VTT | Reflowed candidate |
| --- | ---: | ---: |
| Video/caption pairs structurally passed | 17/17 | 17/17 |
| Cues | 9,095 | 4,555 |
| Lines over 42 characters | 1,523 | 0 |
| Cues over 20 characters/second | 2,606 | 437 |
| Cues over 7 seconds | 0 | 0 |
| Speaker-labeled cues | 0 | 0 |
| Relevant-sound cues | 0 | 0 |

`scripts/reflow_caption_corpus.py` creates candidates in a separate output tree. It groups fragmented phrases, wraps text to two 42-character lines, and uses available silence without crossing the next cue or the verified MP4 duration. It also proves that reflowing preserves the glossary-corrected spoken text. The optional `scripts/caption-glossary.json` corrected 86 known product-name variants to `CSUBUY`, `JAGGAER`, `ServiceNow`, or `P2P`.

```powershell
py scripts/reflow_caption_corpus.py --input-root tmp/caption-audit/captions --output-root tmp/caption-audit/reflowed --video-root tmp/caption-audit/videos --glossary scripts/caption-glossary.json
py scripts/validate_caption_corpus.py --caption-root tmp/caption-audit/reflowed --video-root tmp/caption-audit/videos --all-discovered --report tmp/caption-audit/reflowed-report.json --summary-only
```

All 12 scripted tutorials have zero line-length, duration, and reading-speed warnings after reflow. The remaining 437 reading-speed advisories occur in the five long live recordings. They require editorial review because reducing them further would require resegmenting word-level timing or paraphrasing fast speech.

## Browser And Device Results

The native WebVTT test used a four-second MP4 with two distinct audio tones and two synchronized sound-description cues. Each run confirmed two loaded cues, `showing` mode, and the correct active cue during each tone. A second exhaustive run loaded all 17 real reflowed MP4/VTT pairs in each desktop browser, confirmed the expected cue count and `showing` mode, played each video from the beginning, and confirmed that an active cue contained the current playback timestamp.

| Environment | Synthetic test | Real corpus |
| --- | --- | --- |
| Google Chrome desktop | Pass | 17/17 pass |
| Microsoft Edge desktop | Pass | 17/17 pass |
| Mozilla Firefox desktop | Pass | 17/17 pass |
| Android Chrome emulation, 390 x 844 | Pass | Not repeated |
| Firefox responsive viewport, 390 x 844 | Pass | Not repeated |

Safari/iOS testing requires Apple hardware or a hosted real-device service and remains a release check if Safari is declared supported.

## Public Video Inventory

| Public video | IAM pair | Deployed API retrieval check |
| --- | --- | --- |
| Fiscal Year End/2026 Fiscal Year End Process Training.mp4 | Pass | Pass |
| Getting Started/User Profile Update.mp4 | Pass | Pass |
| Getting Started/Using Comments.mp4 | Pass | Pass |
| Procurement/Updating PO Payment Terms.mp4 | Pass | Pass |
| Receiving/Creating a Receipt.mp4 | Pass | Pass |
| Search, Data Exports, Reports, & Support Tickets/Search for Requisitions (CSU08_SearchRequisition).mp4 | Pass | Pass |
| Search, Data Exports, Reports, & Support Tickets/Searching in CSUBUY (CSU02_BasicAdvancedSearching).mp4 | Pass | Pass |
| Shopping and Requistions/Shop Using a Form.mp4 | Pass | Pass |
| Shopping and Requistions/Shop Using a Punchout Catalog.mp4 | Pass | Pass |
| Shopping and Requistions/Submitting a Change Request (CSU10_POChangeRequest_V2).mp4 | Pass | Pass |
| Suppliers/Request a New Supplier.mp4 | Pass | Not selected by the tested public query |

## Issues Found

| ID | Finding | Resolution |
| --- | --- | --- |
| CAP-001 | The player did not receive a caption URL. | Added independently signed `caption_url` values to video source cards. |
| CAP-002 | The native player had no caption track. | Added a default English WebVTT captions track and readable failure fallback. |
| CAP-003 | The source bucket currently omits CORS headers, so enabling cross-origin tracks also blocks MP4 playback. | Added a narrow read-only bucket CORS policy and deployment step. This must be deployed before the caption-enabled frontend. |
| CAP-004 | Chrome/Edge update `activeCues` after `seeked`, unlike Firefox. | Browser QA now verifies cue changes during real playback instead of assuming event simultaneity. No product change was required. |
| CAP-005 | The private VTT/MP4 corpus was initially unavailable. | Resolved with the authorized `calpoly` profile; all 17 pairs were downloaded and structurally audited. |
| CAP-006 | The tested query did not retrieve the public supplier-request video. | Caption pairing is configured; retrieval coverage should be evaluated separately because captions are loaded only after a video is cited. |
| CAP-007 | Original Transcribe VTT output used 9,095 fragmented cues and produced 1,523 line-length plus 2,606 reading-speed warnings. | Added a non-destructive, duration-aware reflow tool. The candidate has zero line-length warnings and 437 speed advisories confined to five live recordings. |
| CAP-008 | Approved transcripts contain repeated product-name errors such as `CSU by` and `Jagger`. | Added a reviewable glossary that corrected 86 occurrences to approved product names in the candidate corpus. |
| CAP-009 | The retained Transcribe jobs were created without speaker diarization; all 17 VTTs therefore have zero speaker labels. | Accepted as out of scope by product-owner decision. No paid diarization jobs will be run. |
| CAP-010 | The existing VTTs contain no relevant non-speech descriptions. | Open. A listening review must confirm whether meaningful music, alerts, or other sounds occur and add descriptions where needed. |

## Release Gate

Do not claim complete caption accuracy or deploy the caption-enabled frontend until:

1. The backend/IAM/CORS changes are deployed first.
2. The reflowed candidate is editorially reviewed and promoted to `approved/transcripts/`; S3 versioning is enabled, but no production VTT was overwritten during this audit.
3. Transcript wording and relevant non-speech sounds are reviewed for all 17 videos, with special attention to the five live recordings.
4. The 437 remaining live-recording speed advisories are accepted or corrected by an accessibility reviewer.
5. The deployed app is smoke-tested in each declared supported browser, including Safari if applicable.
