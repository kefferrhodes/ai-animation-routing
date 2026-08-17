# Routing — which model, and why

The table in [`AGENTS.md`](../AGENTS.md) is the answer. This is the reasoning, so you can route
a job the table doesn't cover and so you can tell when a row has stopped being true.

---

## The one distinction that matters: does your shot have an end state?

Everything else is detail. Ask whether the shot has a **defined final frame** — a state the
subject must arrive at.

- *A lid closing.* Yes: open, then closed.
- *A logo assembling from parts.* Yes.
- *A person moving from one posture to another.* Yes.
- *Steam drifting off a cup.* No — there's no particular arrangement of steam it must reach.
- *A crowd milling in a plaza.* No.

If the answer is yes, use **two keyframes**. If no, a single image is fine.

### Why this is structural, not stylistic

Single-image image-to-video has **no end constraint**. The model is given a starting condition
and a text description and asked to invent everything after that. Nothing anchors the far end,
so error accumulates. This has a characteristic signature: convincing motion for the first
second or two, then progressive degradation — the subject relaxes out of a held posture, a
prop fades from a hand, the framing wanders.

Tested head to head on a shot that had a known end state, single-image i2v held for about two
seconds before the subject stood out of position and the object in his hands dissolved. The
same shot as a first/last keyframe pair held all the way to the last frame. The pair pins both
ends, so drift is bounded by construction rather than by prompting.

This is worth internalising because the fix people reach for is more prompt. More prompt does
not add an end constraint. Only an end keyframe does.

### The corollary: don't fake it with interpolation

Given a start and an end frame, the tempting move is to interpolate — optical flow, frame
blending, "morph" tools. **Frame interpolation is a crossfade.** It warps pixels from one
image toward the other. Where the two images agree, that looks like motion. Where they
*disagree* — an ear that's turned, a face at a different angle, a contour that's changed shape
— there is no correspondence to warp along, so those regions dissolve.

The client feedback on interpolated shots is always some version of the same thing: "crossfady",
"the ears fade away", "it looks animatronic". Root cause is not the settings. It is that
blending is not movement.

A video model given the same two frames generates actual motion between them, because it has a
model of how things move. Ears stay ears. This one substitution is the difference between a
rejected sequence and an approved one.

---

## Then: how many independent generations does your sequence contain?

**Identity is a property of the sequence, not of the frame.** Every image you generate
independently is a fresh roll of the dice on your subject's exact appearance — the face, the
build, the surface pattern, the small asymmetries. Any single frame can be perfect. Between
frames, the subject can become a different subject.

This failure is invisible in stills and glaring at speed. A 52-frame still sweep passed a shot
that a client rejected in the first two seconds of watching it, because the shot was built
from many independently generated keyframes and the subject re-rendered at every boundary.

Two consequences for routing:

1. **Minimise independent renders.** Generate the fewest keyframes the shot actually needs and
   let the video model fill the middle. Generating intermediate states as extra stills feels
   like more control; it is more drift. On a sequence with ten identifiable positions, build
   four or five as stills and let the model interpolate the rest.
2. **Edit-derive every variant.** Each new still should be an *edit* of an approved parent,
   with the parent attached, not a fresh generation from text. Text alone re-rolls identity
   every time.

---

## Locked compositions vs. free motion

If the shot must not move — a plate you'll composite on, an insert that has to line up with
something else — you need a model that holds framing. Two behaviours to route around:

- **Re-staging.** Some models treat a static input as a suggestion and re-block the shot:
  rotating the subject, recentring, resizing props. Observed on longer single-image takes.
  Fatal for locked compositions.
- **Jitter.** On near-still footage, frame-to-frame irregularity reads as a bad encode. It is
  measurable — mean absolute frame delta — and it differs by model by a factor of several.

Route locked plates to whichever model measures lowest on your own subject, and measure it
rather than trusting the table. `aar qc` reports jitter.

**And add the camera move afterwards, not in the prompt.** A move animated as a crop window
over rendered frames costs nothing, cannot hallucinate, works on footage generated completely
static, and does not compete with keyframe adherence. Prompted camera moves do compete: the
model is now solving for both your end frame and your dolly, and it will trade one off against
the other. Generate locked, move in post. Ease in and out — a constant-speed move that stops
dead reads as a crop, not a camera. 3–12% of frame width across five seconds.

---

## Fixing vs. regenerating

You have a clip you like and one thing is wrong. Two routes:

**Video-to-video edit** — cheap, preserves the take you already approved. Works well for
*remove this object* and *add this object*. Does not work for *re-render this region in a
different style*: instructions of that shape produce measurable no-ops. And it is not
surgical when the edit is entangled with something else in the frame — asked to remove one
feature from a subject, it stripped an adjacent treatment the shot depended on and returned
something unusable.

**Fix the source frame and regenerate** — this is the underrated route and usually the right
one. Editing a still is precise, cheap, and verifiable: you can diff the edited keyframe
against the original and confirm nothing else moved. Then regenerate the clip from the
corrected keyframe. The rule of thumb:

> If the thing you want changed is *in the subject*, fix the keyframe.
> If it's an object you want gone from the scene, a video edit is fine.

**Never do per-frame pixel surgery on video as a general fix.** Two separate attempts failed
the same way: patching a moving object frame by frame becomes whack-a-mole, damages neighbours,
and leaves you auditing your own repairs. There is one narrow exception — a locked-off shot
where the target is spatially isolated from everything that matters and crosses only static
background. Outside that, regenerate.

---

## Moderation as a routing problem

Filters are classifiers, and different vendors classify differently. That is exploitable in the
most boring possible way: **if one vendor refuses your shot, send it to a different vendor.**
A model from a different company cleared every shot the first-choice model refused, usually
first try.

Before you retry, work out which situation you're in:

- **The classifier is reacting to something structural about the frame.** In production this
  showed up as framing-correlated: certain crops of a human subject blocked repeatedly (6 of 6,
  7 of 7) while wider framings of the same subject passed first time. When blocks correlate
  with framing, retrying is wasted money. Change the framing or change the vendor.
- **The same input genuinely passes sometimes.** Also observed — an identical input blocked
  twice and passed on the third attempt. When you have seen the *same* input both pass and
  fail, a bounded retry (2–3, then escalate) is reasonable.

Characterise before you retry. And describe your subject accurately in its real domain
register — a technical illustration described as a technical illustration is being described
correctly, not disguised; a classifier that reads your intent wrong is usually a description
problem. What is never acceptable is hammering the filter: **never resubmit a blocked input
unchanged.** That is an account-suspension path, and the CLI will refuse.

---

## Resolution, and the upscale trap

Check the **native output resolution** of a model before you plan around it. One model in the
current set has no 1080-line option at all while another does 4K natively. Picking the second one
deletes an entire upscale pass — along with its cost, its latency and its failure mode.

When you do need to upscale, know what a *creative* upscaler is: it invents plausible detail
rather than interpolating. On clean synthetic renders that is a gift. On live-action with fine
moving texture — hair, beard, knitwear, foliage — it invents that detail slightly differently
on every frame, and the result is a shimmer that reads as stutter. It is **completely invisible
in still frames**, which is exactly how it ships.

Two upscales in production were rejected for this after passing a still comparison. Measure
frame-to-frame irregularity against the source, per region, before accepting any upscale.

---

## Keeping this table alive

Model names, capabilities and prices change **fast**. Two days after this repo's routing table
was written, a re-probe of the same API found:

- **`veo3` no longer existed.** It had been a documented workhorse two weeks earlier.
- **`veo3.1` had gained keyframe-pair support** it demonstrably did not have before.
- Six models had appeared that weren't in the table at all.

A table is a snapshot. The probe is the actual tool:

```bash
aar probe image_to_video
```

It POSTs a deliberately invalid request — a 1×1 pixel image, a nonsense aspect ratio — and reads
the **validation error**, which enumerates every allowed value for that field. That's how the
model list, the keyframe-array support and the allowed ratios in `models.json` were all derived.

**Two things to know about probing:**

1. **It is not free on every model.** Some validate the image eagerly and reject the poison
   payload outright — no task, nothing spent. Others validate lazily and **create a real,
   billable task** from it. Probing 19 models once created five live tasks. `aar probe` cancels
   anything it creates immediately; cancelling straight away was observed to cost nothing, but
   a probe task you leave running will bill you. If you roll your own probe, cancel.
2. **Acceptance is itself an answer.** If a model accepts a keyframe-pair payload rather than
   rejecting the array, that model supports keyframe pairs. Cancel the task and record the
   capability. The response also carries an `estimatedCost`, which is how you get current
   per-model pricing without generating anything.

If a row here turns out to be wrong, that's a pull request. Include the date and how you
verified it.
