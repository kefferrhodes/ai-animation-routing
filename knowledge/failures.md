# The failure catalogue

Indexed by **what you're looking at**, because that's what you have when something comes back
wrong. Each entry: the symptom, what actually causes it, and the fix that worked.

These are real failures from a paid production. Where a finding is structural it's stated as a
rule. Where it's a measurement that may not generalise, it says so.

---

## Motion and structure

### The subject drifts out of position partway through, or a held object fades away

**Cause:** single-image image-to-video has no end constraint. Error accumulates with nothing
to accumulate *toward*. Convincing for the first second or two, then progressive collapse.

**Fix:** use a keyframe pair. Generate the end state as a still and pin both ends. This is not
a prompting problem and more prompt will not solve it.

---

### The shot performs the action, then does it again, or reverses back through it

**Cause:** you asked for a clip longer than the action takes. The model invents motion to fill
the time — a rehearsal move, a pause-and-restart, or a reversal.

**Fix:** describe the clip as extreme slow motion of one short move, evenly stretched, still
travelling at the last frame. Explicitly ban reversal and rehearsal. See
[`prompting.md` §4](prompting.md) for the wording. Asking for "slower" gets read as "perform
it, then wait" and does not work.

**Watch out:** this is invisible in a contact sheet — every frame is a legitimate pose, just
in the wrong order. A 21-frame grid passed a clip with five reversals. Use `aar qc`, which
tracks direction changes.

---

### Edges dissolve, ears and faces smear, the movement looks animatronic

**Cause:** the "motion" is frame interpolation between two stills. Interpolation is a
crossfade — it warps pixels between endpoints, so anything the two images disagree on has
nothing to move toward and dissolves.

**Fix:** stop interpolating. Give both frames to a video model as keyframes. This is the single
highest-value substitution in this repo.

---

### The subject subtly becomes a different person / a different object across the shot

**Cause:** the sequence is built from multiple independently generated frames. Each generation
re-rolls identity — build, face, surface detail, small asymmetries. Any individual frame is
valid; identity lives *between* frames.

**Fix:** generate fewer stills and let the video model interpolate the middle. Edit-derive every
variant from one approved parent with the parent attached. Before assembling, build a
**cross-key identity strip** — the keyframes side by side at the same scale — and look at it.

**Watch out:** this passes a stills QC completely. A 52-frame sweep approved a shot a client
rejected within two seconds of watching it.

---

### The composition changed — subject rotated, recentred, props resized

**Cause:** some models re-stage a static input rather than animating it, particularly on longer
single-image takes.

**Fix:** route locked compositions to a model that holds framing. If you're stuck with the
re-stager because it's the only one that will accept your subject, shorten the take.

---

### The shot looks like a bad encode — shimmering, unstable, "cheap"

**Cause:** frame-to-frame jitter. Measurable, and it differs between models by several times on
near-still footage.

**Fix:** measure it (`aar qc` reports mean frame delta) and route locked plates to whichever
model measures lowest **on your subject**. Don't trust a table — the published measurement in
`models.json` came from one subject on one date.

---

### The model added a camera move you didn't ask for, or fought the one you did

**Cause:** models add camera motion unprompted; and a prompted move competes with keyframe
adherence, so the model trades one against the other.

**Fix:** freeze the camera explicitly in every motion prompt, generate locked, and **add the
camera move in post** as an animated crop window over the rendered frames. Free, cannot
hallucinate, works on completely static footage. Ease in and out; 3–12% of frame width over
five seconds. A constant-speed move that stops dead reads as a crop, not a camera.

---

### The generated background drifts, or doesn't match your other shots

**Cause:** the model invented its own background, and invented backgrounds are unstable.

**Fix:** matte the subject out and composite onto a controlled plate you own. Then the
background is fixed by construction and matches everything else in the sequence.

---

## Content that shouldn't be there

### You asked for something to be absent and it appeared anyway

**Cause:** negative prompts lose to model priors. Where the model has a strong prior that a
scene contains a thing, naming the thing in a negative reliably produces the thing — observed
repeatedly on the same shot.

**Fix:** remove it from the source image before generating, or edit it out of the output
afterwards. Treat negatives about *objects* as a weak hint. (Negatives about *rendering
behaviour* — "no cross-fading" — do work.)

---

### A video edit removed the thing you asked for and also removed something you needed

**Cause:** video-to-video edits are not surgical when the target is entangled with an adjacent
property. Asked to remove one feature from a subject, the model also stripped a colour
treatment the shot depended on — 224 credits for an unusable result.

**Fix:** **fix the source keyframe and regenerate.** Editing a still is precise and verifiable
— you can diff it against the original and confirm nothing else moved (a real edit came back
with a 3/255 mean delta outside the intended region). Then regenerate from the corrected frame.

**Rule of thumb:** if the thing you want changed is *in the subject*, fix the keyframe. If it's
an object you want gone from the scene, a video edit is fine.

---

### A video edit did nothing at all

**Cause:** you asked it to *re-render a region in a different style*. Video-to-video models
obey remove/add-object instructions and ignore restyling instructions. Two full passes produced
measurable no-ops (near-white pixel mean moved 773 → 699; worst frame visually identical).

**Fix:** regenerate from a corrected keyframe. Don't spend a third pass.

---

### You tried to patch the problem frame by frame and made it worse

**Cause:** per-frame pixel surgery on video is whack-a-mole. Patching a moving object damages
its neighbours, and then you're auditing your own repairs. Failed twice, independently.

**Fix:** regenerate. There is exactly one narrow exception — a **locked-off** shot where the
target is spatially isolated and only ever crosses static background. Outside that, don't.

**And if you do patch anything:** diff the result against the original afterwards and look at
everything that changed. A patch pass punched holes in an object adjacent to the target and
nobody noticed until a later audit.

---

## Moderation

### The model refused your image

**First, work out which situation you're in.** Blocks came in two distinct patterns:

1. **Framing-correlated.** Certain crops of a human subject blocked repeatedly — 6 of 6, 7 of 7
   — while wider framings of the same subject passed first try. When blocks track a property
   of the frame, retrying is money on fire. Change the framing.
2. **Genuinely stochastic.** An identical input blocked twice and passed on the third attempt.
   When you've seen the *same* input both pass and fail, a bounded retry (2–3) is reasonable.

**The reliable fix is to switch vendor.** Different companies run different classifiers. A
model from a different vendor cleared every shot the first-choice model refused, usually first
try. `aar` will suggest the alternate automatically.

**Also worth checking:** describe your subject accurately in its real domain register. A
technical illustration described as a technical illustration is being described correctly, not
disguised — a classifier reading your intent wrong is very often a description problem.

> **Never resubmit a blocked input unchanged.** Repeatedly hammering a moderation endpoint with
> a rejected input is an account-suspension path. `aar` refuses to do it.

---

### Everything is failing, including things that worked yesterday

**Cause:** platform load or an incident, not your content.

**Fix:** three failures on materially different inputs means it's not you. Stop, wait an hour,
come back. Debugging your prompt during an outage is a good way to lose an afternoon and
convince yourself of something false.

---

## Output files

### The file isn't the resolution you asked for

**Cause:** models return off-spec dimensions as a matter of course — 1924×1076 where you
expected 1920×1080 — and several models in the current set **have no 1080-line option at all**,
silently, regardless of what you request.

**Fix:** conform on delivery (`aar` does it automatically), and check native maximum resolution
*before* choosing a model. Picking a 1080p-native model deletes an entire upscale pass.

---

### There's an audio track on a clip that has no sound

**Cause:** several models attach a silent AAC track.

**Fix:** strip it on conform. Harmless until it isn't — it will surprise an editor, and it
breaks naive concatenation.

---

### The upscale looks sharper and reads worse

**Cause:** *creative* upscalers invent plausible detail rather than interpolating, and they
invent it slightly differently on every frame. On clean synthetic renders that's a gift. On
live-action with fine moving texture — hair, beard, knitwear, foliage — it doubles temporal
irregularity into a shimmer that reads as stutter.

**It is completely invisible in still frames.** Two upscales shipped after passing a still
comparison and were rejected on playback.

**Fix:** measure frame-to-frame irregularity per region against the source before accepting any
upscale (`aar qc --compare`). Never sign off an upscale on stills alone. Expect to accept
upscales on CG and reject them on live-action faces.

---

## Process failures

These cost more time than any model behaviour.

### You "fixed" a defect that didn't exist

A pale shape on a moving object was read as a rendering defect from a mid-zoom glance. Two
correction passes were run against it — roughly 450 credits — before anyone checked at full
magnification, where it turned out to be a correctly rendered object, motion-blurred.

**Rule:** verify a defect is real at maximum zoom **before** spending anything on remediation.
The rule cuts both ways — don't clear a suspicion without checking, and don't fix one without
checking either.

---

### You chased a note into a worse result

Three rounds of increasingly precise, increasingly technically correct work on an effect — and
the client picked version one, the original untouched render. **Correct is not the same as
better.**

**Rule:** never overwrite an earlier take. When a note produces a v2, present the versions side
by side rather than assuming the newest wins.

---

### You changed the prompt four times when the keyframe was wrong

If a shot isn't close by take six, the problem is upstream. Change the keyframes, not the
motion prompt. Budget 3–6 takes per shot: pick, don't polish.

---

### The metric said pass and the file said fail

A delivery went out with a table showing an effect tracking correctly. The table described the
*intent*; the file did not match, because the metric had been computed against the source
rather than the encoded output.

**Rule:** extract frames from the file you are actually sending, and look at them. Measuring is
not looking. See [`qc.md`](qc.md) rule 0.
