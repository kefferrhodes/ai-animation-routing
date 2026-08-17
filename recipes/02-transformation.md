# Recipe 02 — A two-state transformation

**The job:** a houseplant, wilted and drooping, recovers — leaves lifting, stems
straightening. Five seconds. It has to arrive at a specific final state, because the next shot
in the sequence cuts from it.

**What this teaches:** the keyframe-pair pattern. This is the highest-value thing in this repo
and the one most people skip because interpolation looks like it should work.

---

## 1. Route it

Does the shot have a defined end state? **Yes** — the recovered plant, and the next shot has
to match it.

That single answer rules out three of the models in the table. `veo3`, `veo3.1` and `gen4.5`
take one image only; they physically cannot be given an end frame. Confirm before you build
anything:

```bash
aar models keyframe_pair
```

**The wrong routes, and why they fail:**

| Tempting | What happens |
|---|---|
| Single-image i2v with "the plant recovers" | No end constraint. Convincing for ~2s, then the plant becomes a different plant, or keeps growing past where you wanted it. |
| Generate both stills, interpolate between them | Interpolation is a crossfade. The leaves don't lift — they dissolve from one position and fade in at the other. Everyone sees it. |

## 2. Build the start frame

```bash
aar image "A potted houseplant on a windowsill, badly wilted — leaves drooping down over the \
rim of the terracotta pot, stems bowed, foliage limp and dull. Soft grey daylight from the \
window behind. Plain pale wall. Photographic, natural, high detail. No text." \
  --ratio 16:9 --size 2K --takes 3 -o plant_wilted.png
```

Pick your favourite.

## 3. Build the end frame — as an EDIT of the start frame

This is the step that matters. **Do not write a second prompt from scratch.**

```bash
aar image "Return THE SAME SHOT — the same pot, the same plant, the same number of leaves, \
the same camera position, framing, distance, lighting, window, wall and shadow — with the \
plant RECOVERED. The stems are upright and firm, the leaves are lifted and turned outward, \
the foliage looks green and turgid. Nothing else in the picture changes at all, and the \
colours stay exactly as saturated as they are." \
  --ref plant_wilted.png --ratio 16:9 --size 2K --takes 3 -o plant_recovered.png
```

Three things that prompt is doing deliberately:

- **Names everything that stays before what changes.** A generation from text alone would give
  you a different pot, a different leaf count, a different room — and the clip between them
  would have to invent a transformation between two different plants.
- **Pins saturation.** Edits drift on colour even when you say nothing about it. One production
  edit came back desaturated across the whole frame for exactly this reason.
- **Says "nothing else changes."** Out loud, every time.

## 4. Look at both frames side by side before spending anything

```bash
open plant_wilted.png plant_recovered.png
```

Same pot? Same number of leaves? Same camera? If not, fix it here — a video model given two
frames that disagree will produce something that disagrees with itself. **Stills are cents;
video takes are dollars.** This check has never not been worth it.

## 5. Generate

```bash
aar video "The wilted plant slowly recovers over the whole clip: the drooping leaves lift and \
turn outward and the bowed stems straighten and firm up. **This is one single continuous \
change in one direction, from the first frame to the last — the motion never reverses, never \
goes back the way it came, and never returns partway to the wilted state.** The pot does not \
move or change. The windowsill, wall, window, shadow and lighting stay exactly as they are. \
The camera is completely locked. No dissolving, no fading, no cross-fading, no morphing \
between images." \
  --first plant_wilted.png --last plant_recovered.png \
  --duration 5 --ratio 1920:1080 --takes 2 -o recover.mp4
```

Note the prompt still **describes only what moves** — the environment is in both keyframes and
never mentioned. And note the two explicit prohibitions: reversal, and cross-fading. Both are
failure modes these models actually have, and naming them measurably helps.

If your first-choice model refuses the image, `aar` will try the next vendor automatically and
tell you it did. It will not resubmit the same input to the same model.

## 6. QC

```bash
aar qc recover.mp4 --first plant_wilted.png --last plant_recovered.png --sheet
```

For a keyframe pair, read in this order:

1. **direction changes** — this is the one. `0` or `1` is fine. `2` or more means the plant
   recovered, wilted again and recovered, or similar. It is completely invisible in the contact
   sheet and it is the most common failure of this shot type.
2. **end adherence** — did it actually arrive at your end frame, or somewhere near it? A high
   number here means the far end wasn't honoured and the next shot won't cut.
3. **start adherence** — same at the other end.
4. **subject scale / travel** — the pot shouldn't have moved.

Then watch it. Specifically watch for anything dissolving rather than moving — that's the
signature of the model falling back on a blend, and it means the two keyframes disagreed
somewhere you didn't check.

## 7. If it's wrong

Work out first whether it's a **keyframe problem** or a **take problem**:

- Wrong in the same way across both takes → keyframe problem. Go back to step 3.
- Different failures in each take → take problem. Roll two more.
- Still not close by take six → keyframe problem, regardless of what it looks like. Changing
  the motion prompt a seventh time is how afternoons disappear.

## 8. Camera move, deliver

As in [recipe 01](01-product-hero.md) — in post, eased, 3–12%. A slow push toward the plant
works here because the shot is about the plant.

---

## What this cost

Six stills (cents) plus two video takes at ~85 credits ≈ **170 credits, about $1.70**.

The interpolated version of this shot costs nothing in credits and gets rejected in review. An
entire sequence was built that way once, rejected, and rebuilt from scratch. That rebuild is
the most expensive thing in this repo's history and it was avoidable by reading one paragraph.
