# Adeel Raja Newsroom — Activation Checklist

The recovery work lives on `recovery/international-newsroom`. The original `main` branch has not been changed.

## Before production

1. Review the draft recovery pull request and wait for all quality checks.
2. Confirm the existing GitHub repository secrets are present:
   - `GEMINI_API_KEY`
   - `FACEBOOK_PAGE_ID`
   - `FACEBOOK_PAGE_ACCESS_TOKEN`
3. Confirm the Facebook Page token is a current Page access token with `pages_manage_posts` permission. The deprecated `publish_actions` permission is not a substitute.
4. Keep `GEMINI_MODEL` unset unless you have verified another model for this AI Studio project. Default is `gemini-3.8-flash`. Use Google AI Studio's free tier only; do not attach paid billing or enable a paid usage tier. The code caps calls at 16 per Pacific Time day, including retries. Free-tier prompts may be used by Google to improve its products, so send public news only—not confidential source identities or unpublished sensitive notes.
5. Add optional repository variables:
   - `X_RSS_FEEDS`: semicolon-separated public X-to-RSS bridge URLs, only if you have a verified working bridge.
   - `WHATSAPP_CHANNEL_URL`: your real WhatsApp Channel invite link.
6. Run the newsroom manually with both publish inputs set to false. Inspect JPG posters, MP4 reels, bilingual copy and platform drafts before enabling publication. Posters rotate through Light Editorial, Dark Editorial and White + Red; the 23 category labels use restrained accents.
7. For YouTube, create an OAuth client, enable YouTube Data API v3, complete user authorisation, then add:
   - `YOUTUBE_CLIENT_ID`
   - `YOUTUBE_CLIENT_SECRET`
   - `YOUTUBE_REFRESH_TOKEN`
   Uploads default to private. Only change `YOUTUBE_PRIVACY_STATUS` after review.
8. To enable the daily Facebook question post, verify Page permissions and then set repository variable `ENABLE_DAILY_POLL=true`.
9. Scheduled workflows run only after the recovery branch is merged into the repository's default branch. GitHub schedule start times may be delayed.

## Safe defaults

- Facebook publishing: off by default.
- YouTube publishing: off by default.
- Daily poll publishing: off by default.
- YouTube privacy: private.
- Missing Urdu, source URL, or image: block output rather than publish a broken card.
- Publication receipts are cached between Actions runs as a best-effort duplicate guard.

## Not yet available

- WhatsApp Channel publishing is not wired up in this branch. Do not use the WhatsApp Business messaging endpoint as a substitute for Channel publishing.
- The current image pipeline reads publisher-supplied RSS media. Verify reuse rights for the images or configure a licensed image source before large-scale distribution.
- X reading needs a verified RSS bridge; no paid X API or scraping is used.
- WhatsApp Channel posts are prepared as drafts for manual posting because the official Cloud API does not expose Channel publishing.
- RSS ranking and headline clustering are heuristic aids, not a substitute for editorial review.
- Reels use image motion, an animated ticker/progress line and Urdu narration; they are not AI-generated cinematic video scenes.
