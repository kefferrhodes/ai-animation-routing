# QC — what a pass actually requires

Every rule here exists because something shipped broken. They're ordered roughly by how much
each one cost.

The short version: **generation is cheap, and a client noticing something you already knew
about is not.**

---

## 0. View the delivered file. Measuring is not looking.

A clip shipped with a table demonstrating that an effect tracked correctly through the shot.
The table described the *intent*. The file didn't match — the model had extinguished the effect
before the moment it was supposed to mark — because the metric had been computed against the
source rather than the encoded output. The client caught it in one viewing.

**Extract frames from the file you are actually sending, and look at them.** Verify every
metric against the output, never against the input.

**Corollary:** if an effect has to obey a rule — start here, stop there, hold for this long —
generate the plate clean and add the effect procedurally. Never trust a model to time it. Once
it's not in the render, no amount of post can recover it.

---

## 1. Check the encoded deliverable, every frame

Not the working frames. Not a sample.

Sampling five frames from a five-second clip means inspecting about 4% of it. Two separate
rejections came straight out of sampled QC: a subject changing identity mid-shot, and an
object present in a shot that had been declared clean.

Extract all the frames and step through them, or write a check that scans all of them. `aar qc`
scans every frame and writes a contact sheet; the sheet is for orienting yourself, not for
deciding.

---

## 2. Never classify a moving thing from a single still

A stray white shape was dismissed as motion blur from one frame. It was an object that
shouldn't have been in the shot. Separately, a pale region on a moving object was flagged *as*
a defect from one frame; it was a correctly rendered object, motion-blurred, and chasing it
cost ~450 credits.

**Track anything suspicious across neighbouring frames before deciding what it is.** A
ballistic path across frames means a free object. Rigidly attached to something else that's
moving means it's part of that thing.

The same rule governs flagging, not just clearing.

---

## 3. Verify a defect at maximum zoom before spending on remediation

Both directions. Don't clear a suspicion without checking; don't pay to fix one without
checking either. A mid-zoom glance is not evidence.

---

## 4. Identity is a property of the sequence, not the frame

Every keyframe can be individually perfect while the subject morphs between them, because each
independent generation re-rolls appearance. **Build a cross-key identity strip** — the
keyframes side by side at the same scale — and look at it before you assemble anything.

Then check the assembled clip at the key boundaries at full speed. That's where it shows.

---

## 5. Temporal coherence is invisible in stills

Sharpness, colour and artefacts can all look fine on a pass that has doubled the frame-to-frame
irregularity on a face. Upscales and any other per-frame AI pass must be checked for
**frame-to-frame irregularity per region against the source**, not just for image quality.

Two upscales passed a still comparison and were rejected on playback.

`aar qc --compare original.mp4 processed.mp4` reports this.

---

## 6. Physical motion needs numbers

An object that was supposed to roll along a surface was sliding instead. It survived two rounds
of review, because "the surface pattern looks different between these two frames" is also
exactly what sliding looks like — and the frames being compared weren't consecutive.

**Work out what the physics implies, then measure it.** Rolling contact against a static
surface means the body travels twice as far as the roller, in the same direction, with the tread
phase advancing across **consecutive** frames and contact never breaking. Track feature
positions numerically. Don't eyeball sparse frames.

Generalises to anything with a physical constraint: gears, liquid volume, weight transfer,
things that should be attached staying attached.

---

## 7. Audit your own patches

Any fix, diff the result against the original and look at **everything** that changed, not just
the region you meant to change. A patch pass punched holes in an adjacent object and it wasn't
found until a later audit.

---

## 8. Keep every version, and offer the comparison

The first take is a real candidate. Three rounds of increasingly precise work on an effect
ended with the client picking version one, untouched. Correct is not the same as better.

Never overwrite. When a note produces a v2, present them side by side.

---

## 9. If you're writing a caveat, you're not finished

"Slight flicker, invisible at speed." "Minor artefact in the corner." "Known imperfection."

Each of those is a signal to iterate, not a note to attach. If you're about to send something
with an explanation of what's wrong with it, generate another take instead. Volume is not the
constraint — a client noticing something you already knew is what costs.

---

# What to actually check, by shot type

## Every clip

- [ ] Encoded dimensions and frame rate are what you promised
- [ ] No unexpected audio track
- [ ] First frame matches your start keyframe; last frame matches your end keyframe
- [ ] No object present that shouldn't be, checked across all frames
- [ ] Subject identity holds start to end
- [ ] Nothing you told to stay still moved

## Keyframe-pair clips

- [ ] **Direction reversals** — does the motion ever go back the way it came? (The single most
      common failure and invisible in a contact sheet.)
- [ ] Both endpoints honoured, not just the first
- [ ] Motion is still travelling at the last frame if it should be, rather than arriving early
      and holding
- [ ] Nothing dissolves or cross-fades at any point

## Locked plates

- [ ] Frame-to-frame jitter measured, not eyeballed
- [ ] Subject doesn't drift, sway, or change size
- [ ] Background is genuinely static
- [ ] Colour temperature doesn't drift start to end (a 24% cool drift over a take was invisible
      in a three-frame check and obvious in the numbers)

## Anything with a physical constraint

- [ ] Physics model written down, then measured across consecutive frames

## After any upscale or per-frame pass

- [ ] Frame-to-frame irregularity compared against the source, per region
- [ ] Faces and fine texture checked at full speed, not in stills

## Before delivery

- [ ] You have viewed the encoded file you are sending
- [ ] Earlier versions archived, not overwritten
- [ ] You are not attaching a caveat

---

# Using `aar qc`

```bash
aar qc clip.mp4                                    # full scan + metrics
aar qc clip.mp4 --first start.png --last end.png   # + keyframe adherence
aar qc clip.mp4 --sheet                            # + contact sheet
aar qc --compare source.mp4 upscaled.mp4           # temporal irregularity vs source
```

It reports: dimensions, frame rate, audio presence, per-frame jitter, direction reversals,
subject scale and position drift, colour temperature drift, and keyframe adherence at both
ends.

**It tells you where to look. It does not tell you the shot is good.** Nothing here replaces
rule 0.
