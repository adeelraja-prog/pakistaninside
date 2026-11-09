# Adeel Raja Newsroom — Activation Checklist

The recovery work lives on `recovery/international-newsroom`. The original `main` branch has not been changed.

## Before production

1. Review the draft recovery pull request and wait for all quality checks.
2. Confirm the existing GitHub repository secrets are present:
   - `GEMINI_API_KEY`
   - `FACEBOOK_PAGE_ID`
   - `FACEBOOK_PAGE_ACCESS_TOKEN`
3. Confirm the Facebook Page token is a current Page access token with `pages_manage_posts` permission. The deprecated `publish_actions` permission is not a substitute.
4. Keep `GEMINI_MODEL` unset unless you have verified another model for this AI Studio project. Default is `gemini-3.8-flash`; legacy Gemini 2.5 access may be restricted for projects without prior use.
5. Run the newsroom manually with both publish inputs set to false. Inspect the poster and MP4 artifacts before enabling publication.
6. For YouTube, create an OAuth client, enable YouTube Data API v3, complete user authorisation, then add:
   - `YOUTUBE_CLIENT_ID`
   - `YOUTUBE_CLIENT_SECRET`
   - `YOUTUBE_REFRESH_TOKEN`
   Uploads default to private. Only change `YOUTUBE_PRIVACY_STATUS` after review.
7. To enable the daily Facebook poll, verify Page permissions and then set repository variable `ENABLE_DAILY_POLL=true`.
8. Scheduled workflows run only after the recovery branch is merged into the repository's default branch. GitHub schedule start times may be delayed.

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
- RSS ranking and headline clustering are heuristic aids, not a substitute for editorial review.
