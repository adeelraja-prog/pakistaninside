# Pakistan Inside — Recovery Audit & Roadmap

Date: 2026-11-09
Target branch: recovery/international-newsroom
Production branch: main (unchanged)
Brand direction: Adeel Raja
Visual direction: International premium newsroom
Operating constraint: free-first; no paid API dependency introduced by this recovery plan.

## Confirmed findings from inspected source

1. `engine/scout.py` reads only the first five entries from each RSS feed, uses a small fixed keyword list, ranks by keyword count, and returns at most 20 stories. This is not editorial importance ranking, does not establish recency or corroboration, and can miss significant stories lower in feeds.
2. `engine/editor.py` fallback returns English-only cards with blank Urdu. In the inspected `main.py`, quota and general editor errors explicitly publish this fallback. This violates Urdu-first output requirements.
3. `engine/editor.py` contains validation code after the unconditional return in `fallback_stories`; that code is unreachable. The intended item validation method is therefore not defined in the inspected class.
4. `engine/designer.py` creates a flat colour background. No image retrieval/download path is present. It uses single-line draw calls without robust Urdu wrapping, text-fit, or clipping checks. It only discovers fonts by matching a filename keyword and falls back to Pillow's default font.
5. `main.py` uses one fixed output path for every story. Multiple cards in one run overwrite the same file, so the uploaded artifact may contain only the last card.
6. `.github/workflows/newsroom.yml` contains only manual `workflow_dispatch`; no `schedule` trigger is configured in that workflow.
7. Inspected execution path only publishes to Facebook. No YouTube Shorts rendering/upload or WhatsApp publishing path is present in the inspected files.
8. Facebook publishing code checks for a returned photo/post ID, but actual publication success rates require Actions run logs and Page-side verification.

## Recovery rules

- Never publish English fallback when Urdu is required. On editor/model failure, fail closed and record a clear error.
- Never publish a poster without a valid, relevant image unless an explicitly labelled illustrative graphic is intentionally approved for that story.
- Never call a story "breaking" solely because it is new. Require credible sourcing and editorial urgency.
- Deduplicate syndicated stories before ranking and retain source URLs/timestamps.
- Separate editorial selection, language validation, asset retrieval, rendering, and platform publishing into independently testable stages.
- Keep production branch `main` unchanged until recovery branch passes tests and is explicitly reviewed.
- No secrets, access tokens, or private credentials may be written to repository files or logs.

## Editorial scoring design (initial target)

Rank candidates using a transparent score, not raw keyword count:
- Public impact / consequence
- Political and constitutional significance
- Court / judiciary significance
- Breaking urgency and freshness
- Independent source corroboration
- Reliability of source and evidence
- Novelty / update value
- Repetition and low-value press-release penalty

Required coverage lanes: PTI / Imran Khan / opposition; judiciary and constitutional matters; parliament and government accountability; public-interest cost-of-living issues; national security and foreign affairs; major international developments. Coverage is not a partisan quota: factual importance and verification govern publication.

## Poster design specification

International premium newsroom identity, branded **Adeel Raja**:
- Strong editorial photograph or verified event image as the dominant visual.
- Clear hierarchy: category / urgency, concise Urdu headline, one supporting line, source and timestamp, Adeel Raja brand.
- Premium dark newsroom palette with restrained accent colours; no clutter, excessive badges, or tiny copy.
- Correct Urdu shaping with a verified Nastaliq-capable font and RAQM support.
- Automatic line wrapping, font fitting, safe margins, image crop checks, and rendered-image QA.
- Distinct templates for breaking, politics/courts, and public-interest explainers.
- If a suitable image cannot be retrieved and validated, block publishing and flag for review.

## Video specification

A separate 9:16 production pipeline:
- Urdu script and fact-check
- Voice-over (free/local option where feasible)
- Licensed/approved stills and motion graphics
- Burned-in Urdu subtitles
- 1080x1920 rendering and duration checks
- YouTube Shorts upload only after OAuth is configured and user authorizes it
- Keep Facebook and YouTube outputs independently configurable.

## Phased implementation

### Phase 0 — Preserve and inspect
- Keep `main` untouched.
- Work only on `recovery/international-newsroom`.
- Inventory source, manifests, dependencies, workflows, recent commits, and available run logs.

### Phase 1 — Stop harmful output
- Remove English fallback publishing.
- Repair editor validation and add unit tests.
- Ensure failures are visible and do not silently produce low-quality posts.

### Phase 2 — Editorial intelligence
- Improve feed collection and source metadata.
- Add deduplication, freshness, topic lanes, corroboration, scoring, and low-value press-release suppression.
- Add tests using representative Pakistan political, judiciary, public-interest, and routine press-release examples.

### Phase 3 — Urdu quality gate
- Strict schema, Urdu-script checks, names/numbers/source validation, and no-publish behavior on failure.
- Human review mode for uncertain/high-risk claims.

### Phase 4 — Poster studio
- Image retrieval with source/licensing metadata and relevance checks.
- Three premium Adeel Raja templates and render QA.
- Save each card under a unique filename; never overwrite the only output.

### Phase 5 — Shorts and animation
- Build and test vertical video rendering independently of publishing.
- Add subtitles, voice-over, motion graphics, and repeatable templates.

### Phase 6 — Distribution and operations
- Add independently gated Facebook / YouTube / WhatsApp adapters as permissions allow.
- Add duplicate prevention, retry safety, publishing receipts, failure notifications, and scheduled runs.
- Validate free-tier quotas and platform limits before enabling schedules.

### Phase 7 — Acceptance testing
- At least 20 representative stories across all coverage lanes.
- No English fallback, no missing-image publication, no duplicate posts, and no broken Urdu layout.
- Render and inspect multiple poster variants and Shorts.
- Confirm platform receipts and actual published URLs before declaring production-ready.

## Evidence still required

- Full GitHub Actions run history and job logs (to measure actual runtime failures).
- Screenshots or artifact samples of posters and generated videos.
- Current connected platform permissions and OAuth status.
- Whether any separate branches/workflows or external video experiments exist outside the inspected default-branch files.

This is a source-code audit of the inspected default-branch files, not a claim that every external integration or historical run has been exhaustively verified.


## Additional confirmed findings from GitHub Actions run 41624859464 (2026-11-03)

The workflow and job were marked successful, but the job log shows the newsroom did not successfully publish:

- Scout collected 30 stories.
- Gemini returned repeated HTTP 503 UNAVAILABLE errors (high demand).
- The application then used its simple English fallback despite the intended Urdu-first workflow.
- Facebook Graph API returned HTTP 403 / OAuthException code 200: the permission `publish_actions` is deprecated/unavailable.
- The Strategist returned error dictionaries, but the old `main.py` only printed those dictionaries and did not fail the job. Therefore GitHub Actions reported success despite Facebook publication failure.
- The `latest-poster` artifact uploaded successfully, but artifact upload success is not evidence of successful Facebook publishing or editorial quality.

This proves the prior green workflow status was a false positive for end-to-end newsroom success. Phase 1 must treat platform error receipts as job failures and distinguish artifact creation from publishing confirmation.

## Run status interpretation

A green Actions run currently proves only that the Python process exited successfully and the artifact step completed. It does not prove that a Facebook post was created. Production acceptance must check the platform response ID and, where possible, the resulting post URL.


## Recovery implementation update (9 November 2026)

Implemented on `recovery/international-newsroom` (not merged to production):

- Replaced the first-five RSS collector with up to 30 entries per feed, date parsing, basic topic lanes, duplicate-title suppression, and recency/topic/press-release heuristics.
- Repaired the Urdu editor validation path and disabled English/raw-RSS fallback publishing. The editor now must return an exact source URL so image and source metadata can be safely mapped back to the original feed item.
- Rebuilt poster rendering around a large editorial image, restrained international-newsroom hierarchy, Adeel Raja branding, Urdu Naskh font discovery, RAQM shaping, and unique output filenames. Missing or invalid images now block poster creation.
- Added vertical 9:16 reel rendering with Urdu TTS via Edge TTS and ffmpeg motion treatment.
- Added an optional YouTube Shorts uploader, gated behind explicit workflow input and OAuth secrets. Default privacy is private.
- Added a rotating daily Urdu audience-poll library and a scheduled dry-run workflow. Publishing remains gated behind the repository variable `ENABLE_DAILY_POLL` or a manual approval input.
- Added a four-hour scheduled newsroom dry-run. Facebook and YouTube publishing remain disabled by default.
- Added deterministic regression tests for editorial scoring, press-release penalties, Urdu fallback rejection, missing-image blocking, and poll rotation.

## Known limitations / user-side prerequisites

- RSS keyword/topic scoring is a transparent heuristic, not a fully trained editorial judgement system. It does not yet provide robust cross-source corroboration or semantic clustering; editorial sampling is required before production use.
- RSS image presence does not itself prove reuse rights. Confirm publisher image permissions or replace the image source with appropriately licensed assets before broad automated distribution.
- Facebook publishing requires a current Page access token and the correct Page permissions (not the deprecated `publish_actions` permission). A successful code check cannot grant these permissions.
- YouTube uploads require the user to create/authorise an OAuth client, enable YouTube Data API v3, and add `YOUTUBE_CLIENT_ID`, `YOUTUBE_CLIENT_SECRET`, and `YOUTUBE_REFRESH_TOKEN` as GitHub secrets. Uploads default to private.
- WhatsApp Channel publishing is not implemented in this recovery branch. A valid official channel-publishing integration and credentials must be confirmed; do not substitute a WhatsApp Business messaging endpoint and claim it publishes to a Channel.
- A daily poll workflow and library exist, but automatic live posting remains off until Page permissions are verified and the repository variable is deliberately enabled.
- The new poster and video pipelines still require a real end-to-end run with live RSS images and the configured TTS service. CI compilation/unit tests alone do not prove visual quality or successful media generation.
- GitHub Actions schedule timing is best-effort and may be delayed by GitHub. The four-hour workflow is intentionally dry-run by default.

## Acceptance status

Code-level regression checks have passed on intermediate recovery commits. Final acceptance remains pending: latest-commit CI, live dry-run poster/reel artifacts, image rights review, sample Urdu editorial review, and platform-authorisation checks.
