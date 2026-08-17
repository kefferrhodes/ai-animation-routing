# Recipe 03 — One character across five shots

**The job:** an explainer sequence. The same person appears in five shots — at a desk, standing
up, walking, at a window, sitting back down. They have to be recognisably the same person in
all five, cut together.

**What this teaches:** identity across a sequence, which is where most AI video projects
actually fail. Every individual shot can look great and the sequence still be unusable.

---

## 1. The thing to understand before you start

**Identity is a property of the sequence, not of the frame.**

Every image you generate independently is a fresh roll of the dice on your character's exact
appearance — face, build, hairline, the specific way their jacket sits. Any single frame can be
perfect. Across frames, the character becomes a different person.

This is invisible in stills and glaring at speed. A 52-frame still sweep once passed a shot
that was rejected within two seconds of someone watching it play.

Two consequences that drive everything below:

1. **Generate as few independent images as possible.** Let video models fill the gaps.
2. **Every image after the first is an EDIT of an approved parent**, with the parent attached.

## 2. Build the canonical frame — once

One image. Get it right. Everything else in the sequence descends from it.

```bash
aar image "A woman in her forties seated at a plain wooden desk in a bright minimal office, \
three-quarter view toward camera, wearing a charcoal crew-neck sweater, dark hair tied back, \
neutral expression, hands resting on the desk. Soft daylight from a large window to the left. \
Photographic, natural colour, high detail, shallow depth of field. No text, no logos." \
  --ratio 16:9 --size 2K --takes 4 -o canon.png
```

Four takes. Pick the one you'd be happy seeing five times, not the one with the nicest
lighting. This frame is now your character.

> **Do not keep a separate "style reference" around after this.** A style anchor left attached
> alongside a canonical frame fights it — in production it snapped the subject back to the
> anchor's pose and camera and wasted both takes. `canon.png` already carries the style, the
> camera and the character. It is the only reference you need.

## 3. Derive the other keyframes — each an edit of `canon.png`

```bash
aar image "Return THE SAME WOMAN — the same face, hair, build, charcoal sweater, the same \
office, window, desk and lighting — now STANDING beside the desk, three-quarter view, arms \
relaxed at her sides. Her face and hair are completely unchanged. Nothing else in the room \
changes." --ref canon.png --takes 3 -o standing.png

aar image "Return THE SAME WOMAN — same face, hair, build, sweater — now standing at the \
window looking out, seen from behind and slightly to the side. Same office, same daylight. \
Her hair and build are completely unchanged." --ref canon.png --takes 3 -o window.png
```

Always from `canon.png`, never from `standing.png` → `walking.png` → and onward. Chaining edits
compounds drift: each generation inherits the previous one's deviations and adds its own. One
parent, many children.

## 4. Build the identity strip and actually look at it

Before generating a single video frame, put the keyframes side by side at the same scale:

```bash
ffmpeg -y -i canon.png -i standing.png -i window.png \
  -filter_complex "[0:v]scale=-1:400[a];[1:v]scale=-1:400[b];[2:v]scale=-1:400[c];\
[a][b][c]hstack=inputs=3" identity_strip.png
open identity_strip.png
```

Same face? Same hairline? Same sweater, same colour, same neckline? Same build?

If any of them is off, **regenerate that keyframe now**. It costs cents here. Discovering it
after you've generated five video clips costs all five.

This one check is the difference between a sequence that cuts and one that doesn't.

## 5. Generate the motion — and let the model do the in-betweens

Here's the leverage. You have three stills and five shots. **Do not generate two more stills.**

Each transition is a keyframe pair between stills you already have, and every intermediate
position is the video model's job:

```bash
aar video "She rises from the chair and stands up beside the desk in one smooth continuous \
move. **One single continuous move in one direction — she never sits back down, never \
reverses, never returns partway.** Her face, hair and clothing stay completely unchanged. The \
desk, window, room and lighting stay exactly as they are. The camera is completely locked. No \
dissolving, no cross-fading, no morphing between images." \
  --first canon.png --last standing.png --duration 5 --takes 2 -o s2_standup.mp4
```

For a shot with no end state — she's just at the window, ambient — a single image is fine:

```bash
aar video "She stands at the window looking out, breathing, with very small natural shifts of \
weight. She does not turn around, does not walk, and does not change position. Her hair and \
clothing stay as they are. The room and light stay exactly as pictured. Camera locked." \
  --first window.png --duration 5 --takes 2 -o s4_window.mp4
```

Every extra still you generate for an intermediate pose is another independent roll of the
identity dice. On a sequence with ten identifiable positions, build four or five and let the
model interpolate the rest. Fewer renders, less drift.

## 6. QC — including the check specific to this job

Per clip, as usual:

```bash
aar qc s2_standup.mp4 --first canon.png --last standing.png --sheet
```

Then the sequence-level check nothing automatic will catch for you: **watch the cut points at
full speed.** Play the last second of each shot into the first second of the next. Identity
breaks show up at boundaries, and they show up in motion, not in frames.

If the character shifts across a cut, the fix is upstream — regenerate the offending keyframe
as a fresh edit of `canon.png` and re-roll the clips that use it. It is not fixable in post
and it is not fixable with a video edit.

## 7. Camera moves and delivery

Per-shot moves in post, eased, 3–12%. Vary the direction across the sequence so consecutive
shots don't all push the same way — that's the tell that everything was generated static.

---

## What this cost

Ten stills (cents) and roughly eight video takes at ~85 credits ≈ **700 credits, about $7**,
for a five-shot sequence.

The version of this job that skips step 4 costs the same to generate and then has to be done
again. The identity strip is free.

---

## Where this pattern breaks down

Be honest with people about the limits:

- **Character consistency is good, not perfect.** Edit-derivation from one parent gets you
  recognisably the same person. It does not get you frame-accurate continuity at the level a
  live-action shoot does. Cut around it: don't hold on a face longer than you need, and avoid
  cutting between two near-identical framings where a viewer can A/B the face.
- **The more the pose differs from the parent, the more drifts.** A profile derived from a
  three-quarter view drifts more than another three-quarter view. Order the sequence so the
  biggest departures are the least prominent shots.
- **Hands and text stay unreliable.** Frame around them or composite over them.
