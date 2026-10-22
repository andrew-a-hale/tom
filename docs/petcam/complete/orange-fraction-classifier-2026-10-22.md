# Petcam classifier: orange fraction replaces the gray-fraction rule

**Date:** 2026-10-22 · **Task:** petcam detection accuracy (website showed stale cat shots)

## Symptom

The petcam site showed willow's latest shot as 21:49 even though she was seen at
22:01, 22:03 and 23:44. Each of those sightings was classified `unknown`, saved
as an `_unknown.jpg` shot, and the older ones were pruned by `KEEP_PER_CAT=1` —
so the willow card went stale and an "unknown" card appeared instead.

## Root cause

The hue classifier needed gray fraction ≥ `GRAY_FRAC=0.5` to call a cat
"gray"/willow. In dim evening light willow's gray fraction drops to ~0.27–0.43
(sensor noise gives dark pixels false saturation), so she fell to `unknown`.
Pancake was never affected — his orange fraction clears the orange check first.

## Evidence (113 hand-labeled boxes, bright to dim, 2026-10-22)

- Orange fraction: pancake 0.27–0.75, willow 0.00–0.10 — clean gap, stable in
  all light. `ORANGE_FRAC=0.18` sits in the middle of the gap.
- Gray fraction: pancake up to 0.73, willow down to 0.27 — total overlap; no
  threshold can work.

## Change

`scripts/petcam-detect.py` `classify()` is now binary: orange fraction >
`ORANGE_FRAC` (0.25 → 0.18) → pancake, else willow. The `unknown` label is gone
(two-cat house, YOLO already gates on cat ≥ 0.4 conf). Gray fraction is still
computed and logged for diagnostics. Selftest updated; `--checknames` went
88 ok / 25 wrong → **113 ok / 0 wrong**. Deployed to `tom`, stale `_unknown`
shot removed, detector restarted via cron watchdog — first post-deploy willow
sighting (23:55:21, orange=0.01 gray=0.76) labeled and shot correctly.

## Ceiling

One evening of data. The NoIR camera (planned second cam) will shift hues and
need recalibration of `ORANGE_MIN_SAT`/`ORANGE_FRAC` — the `--checknames`
regression over the hand-labeled corpus is the tool for that.
