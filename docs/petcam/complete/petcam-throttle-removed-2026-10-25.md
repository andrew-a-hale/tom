# Petcam throttle removed (latest shot updates on every detection)

## Question raised
TODO: "What is the point of petcam throttle if the image was classified
anyway? It should just update the latest."

## Decision
Remove the per-label detection throttle (`THROTTLE_S` / `throttle_ok` /
`/dev/shm/petcam/throttle.json`) from `scripts/petcam-detect.py`. A
detection now always writes/updates the latest shot for that cat. Storage is
already bounded by `KEEP_PER_CAT = 1` (newest file per label kept, older
ones deleted in `save()`), so the throttle only made the gallery stale
without preventing any pile-up.

## Why the throttle existed
- Comment said "one shot per label per 10 min (no 500 photos of a napping
  cat)".
- But `KEEP_PER_CAT=1` already caps `~/petcam/shots/` to one file per cat,
  so shots never piled up regardless of throttle.
- The throttle therefore only delayed refreshing the single "latest" shot,
  even though YOLO classification had already run that pass.

## Changes
- `scripts/petcam-detect.py`: dropped `THROTTLE_FILE`, `THROTTLE_S`,
  `throttle_ok()`, the `json` import, and the throttled branch in
  `pass_once()`. Every detection now calls `save()` and logs
  "saved latest ...".
- `docs/petcam/README.md`, `docs/server/README.md`: throttle references
  removed/updated; knob list no longer lists `THROTTLE_S`.
- `docs/website/README.md`: notes detection shot-throttle removed.
- `andrewahale.com/web/main.go`: `resetThrottle()` and its call in
  `handleDelete()` removed; deleting a shot no longer touches shared
  throttle state (next sighting re-shoots anyway).

## Trade-offs / follow-ups
- Training pairs (`~/petcam/training/`) still accumulate on every `save()`,
  same as before minus the throttle. If that becomes a problem, add a
  separate sampling/throttle for training writes only; not done here to keep
  the change minimal and keep `--selftest`'s `save()` contract intact.
- `/dev/shm/petcam/throttle.json` is now unused; harmless if left in place.
- Web app must be rebuilt/redeployed on Tom for the `handleDelete` change.
- Follow-up fix: gallery poll now reconciles the DOM with `/shots.json`
  (removes figures whose files were replaced/removed), so a newer per-cat
  shot replaces the older one instead of leaving a stale/broken image. See
  `andrewahale.com/web/templates/petcam.html`.
