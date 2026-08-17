# Cost — what this actually runs to

All figures observed in production during July–August 2026 on the Runway developer API.
**Prices move.** Treat these as orders of magnitude and check current rates before committing
to a budget. `aar doctor` prints your live balance; `aar` prints an estimate before a batch.

---

## Unit economics

Credits, prepaid. Observed at 10,000 credits ≈ $100, so **≈ $0.01 per credit**.

Per-model, for a 5-second keyframe-pair shot — these came from the API's own `estimatedCost`,
read on 2026-08-17 by creating a task and cancelling it immediately:

| Model | Resolution | Credits | ≈ USD |
|---|---|---|---|
| `kling3.0_pro` | 1080p | ~85 | ~$0.85 |
| `seedance2_mini` | 720p | 80 | $0.80 |
| `seedance2_fast` | 720p | 145 | $1.45 |
| `seedance2` | 720p | 180 | $1.80 |
| `seedance2` | 1080p | 200 | $2.00 |
| `seedance2_5` | 1080p | 340 | $3.40 |
| `veo3.1` | 720p, 8s | 320 | $3.20 |
| `veo3.1_fast` | 720p, 8s | 120 | $1.20 |

And the other operations:

| Operation | Credits | ≈ USD |
|---|---|---|
| Video-to-video edit, 8s | ~224 | ~$2.24 |
| 2× upscale, 5s clip | ~109 | ~$1.09 |
| Image generation / edit | cents | — |
| Schema probe | 0 (**if you cancel**) | free |

Watch the resolution column: `seedance2_mini` and `seedance2_fast` are cheap partly because
they cannot deliver 1080 lines. They are test tiers, not delivery tiers.

**The spread is 4×, for the same shot.** `kling3.0_pro` at 1080p costs less than half of
`seedance2` at 720p and a quarter of `seedance2_5`. Model choice is the single biggest lever on
what a sequence costs — bigger than length, bigger than take count. Route first, then budget.

> **On the probe being free:** it is free on models that validate the image at submit time, and
> **not free** on models that don't — those create a real billable task from a probe payload.
> Cancel immediately and it costs nothing; leave it and it runs. `aar probe` cancels for you.

---

## What a shot really costs

The unit price is not the number that matters. **Takes per shot** is.

Observed across a completed production: **3–6 takes per shot** is normal. Shots that landed on
take one were luck. The worst single shot in that build went eleven iterations before being
abandoned and rebuilt on a different architecture.

At ~85 credits a take, a finished 5-second shot is realistically **250–500 credits, $2.50–5.00**.

A four-shot sequence, complete: roughly **1,100 credits (~$11)** — that's a real measured
figure, ten takes across four shots. Scale from there. A short sequence of a dozen shots lands
somewhere around **$50–150** of generation.

---

## Where money actually goes

Ranked by what it cost in practice, largest first. None of the top three is generation.

**1. Chasing a defect that didn't exist — ~450 credits.**
A correctly rendered object, motion-blurred, was read as a defect from a mid-zoom glance. Two
remediation passes ran against it before anyone checked at full magnification.
*Prevention:* verify at maximum zoom before spending. Free.

**2. Using the wrong tool for a fix — 280 credits, unusable.**
A video-to-video edit was the intuitive route for "remove this, keep everything else." It
removed the target and also stripped a property the shot depended on. Fixing the source
keyframe and regenerating was cleaner and cheaper.
*Prevention:* read the routing table. Free.

**3. Building on a model with a silent resolution cap.**
An entire library got built at 720p, requiring an upscale pass on every clip — most of which
were then rejected for temporal artefacts. A 1080p-native model existed the whole time and
would have removed both the upscale cost and the rejections.
*Prevention:* check native max resolution before choosing. Free.

**4. Retrying a moderation-blocked input.**
7 of 7 and 6 of 6 blocked on the same framing. Every one of those was paid latency and
attention. Switching vendor cleared it on the first try.
*Prevention:* characterise the block before retrying. Free.

**5. Interpolating instead of generating.**
An entire sequence built with frame interpolation, rejected in review, rebuilt from scratch with
a video model.
*Prevention:* read one paragraph of [`routing.md`](routing.md). Free.

The pattern is not subtle. **The expensive mistakes are all routing and QC mistakes, and they
are all free to avoid.**

---

## Budgeting a job

1. Count your shots.
2. Multiply by 4 takes.
3. Multiply by the unit cost of your chosen model and duration.
4. **Add 50%.** Something will need rebuilding.
5. Add stills: budget 2–3 generations per keyframe, at cents each — noise against video.

For a 10-shot, 5-second sequence at 1080p: 10 × 4 × 85 = 3,400 credits, +50% = **~5,100 credits,
roughly $51**.

---

## Cost discipline that's worth the effort

**Probe before you spend.** `aar probe` re-derives the live model list from validation errors —
no task created, no credits spent. Discovering a model can't do what you need *after* building
its inputs is the expensive version.

**Two takes, then stop and look.** Don't queue six takes of an untested prompt. Run two, QC
them, adjust, then batch. The information from take two changes what you'd ask for in takes
three through six.

**Change keyframes, not prompts, after take six.** If a shot isn't close by six takes the
problem is upstream and further takes are a donation.

**Generate at the resolution you'll deliver.** Upscaling costs credits, adds latency, and
introduces a failure mode that's invisible until playback.

**Never overwrite a take.** Re-generating something you already had is the dumbest possible
line item, and it happens because someone overwrote a file.

**Check the balance before and after a batch.** `aar` does this automatically. It also catches
credits lost to failed tasks — worth reconciling occasionally, since failed submissions have
been observed to consume credits.

---

## Fixed costs outside generation

- **Runway developer API** — prepaid credits. Separate from the app subscription; see
  [`SETUP.md`](../SETUP.md).
- **Google Gemini API** — per-image, billing enabled on the project. Cheap relative to video.
- **ffmpeg** — free.
- Optional: an editor or compositor for the post work (camera moves, effects, text). The camera
  move can be done with ffmpeg alone if you don't have one.
