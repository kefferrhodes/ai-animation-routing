# Recipe 01 — Product hero shot

**The job:** a five-second hero shot of a product on a surface. Ambient life — steam, a
reflection shifting — plus a slow push in. Nothing transforms.

**What this teaches:** when a single image is the right route, how to bound motion so the
model doesn't invent a scene, and why the camera move goes in afterwards.

---

## 1. Route it

Does the shot have a defined end state? **No.** The steam doesn't need to arrive at a
particular arrangement. So: single image, bounded motion.

```bash
aar models single_image
```

Note what the CLI will warn you about: single-image i2v has no end constraint, so it drifts.
For a five-second ambient shot that's acceptable — there's nothing precise to drift *away*
from. For anything with a target state it isn't, and you'd use [recipe 02](02-transformation.md).

## 2. Build the still

```bash
aar image "A matte black insulated coffee flask standing on a pale concrete surface. \
Soft directional window light from the left, deep soft shadow to the right, dark neutral \
background falling off to black. Shallow depth of field. Photographic, premium product \
photography, high detail. No text, no labels, no logos." \
  --ratio 16:9 --size 2K --takes 3 -o hero.png
```

Three takes, because stills are cents and the first one is rarely the best. Pick one.

Two things in that prompt worth noticing:

- **"No text, no labels, no logos"** — one of the few negatives that reliably works, because
  it describes a rendering behaviour rather than an object.
- The lighting and background are described **here**, in the image prompt, where they belong.
  They will not be mentioned again.

## 3. Generate the motion

```bash
aar video "Steam rises gently and continuously from the mouth of the flask, drifting slightly \
to the left as it goes. The flask itself does not move at all — it does not rotate, shift, \
tip or change size. The surface, the shadow, the background and the lighting stay exactly as \
they are. The camera is completely locked: it does not pan, tilt, push, orbit or drift." \
  --first hero.png --duration 5 --ratio 1920:1080 --takes 2 -o steam.mp4
```

This prompt is doing four things and nothing else:

1. **Names the one thing that moves** — the steam.
2. **Freezes the subject out loud** — and enumerates the ways it could fail (rotate, shift,
   tip, resize) rather than saying "stays still."
3. **Says nothing about the scene.** The window light, the concrete, the falloff are all
   already in the picture. Describing them again invites the model to generate its own.
4. **Locks the camera explicitly.** Models add moves you didn't ask for.

## 4. QC

```bash
aar qc steam.mp4 --first hero.png --sheet
```

For a locked ambient plate, read these in particular:

- **subject travel** — should be under 1–2% of frame width. If the flask moved, the take is
  no good however nice the steam is; you can't cut it against a static insert.
- **subject scale** — should be ~1.00×. Anything else is an unrequested zoom.
- **warmth drift** — a take that cools across five seconds won't match the rest of the
  sequence.
- **start adherence** — confirms the model started from your frame rather than its own idea
  of it.

Then open the file and watch it. The metrics tell you where to look.

## 5. Add the camera move in post

Not in the prompt — a prompted push competes with everything you just froze.

A 4% push over five seconds, eased, straight from ffmpeg:

```bash
ffmpeg -i steam.mp4 -vf "\
scale=2304:1296,\
crop=w='1920+96-96*(0.5-0.5*cos(PI*min(t/5,1)))*2':h='1080+54-54*(0.5-0.5*cos(PI*min(t/5,1)))*2':\
x='(in_w-out_w)/2':y='(in_h-out_h)/2',\
scale=1920:1080" -c:v libx264 -crf 16 -pix_fmt yuv420p -an hero_push.mp4
```

The `0.5-0.5*cos(...)` term is the easing — it's what makes it read as a camera rather than a
crop. Scaling up first preserves full output resolution at the tightest point of the push.

If you have an editor, do it there instead; it's a two-keyframe scale animation with ease in
and out. The point is only that it happens **after** generation, where it's free and can't
hallucinate.

## 6. Deliver

```bash
aar qc hero_push.mp4
```

Check the file you're actually sending — not the pre-move version you already looked at. Then
archive `steam.mp4` next to it rather than deleting it. If the note comes back "less push",
you want the clean plate.

---

## What this cost

Three stills (cents) plus two video takes at ~85 credits each ≈ **170 credits, about $1.70**.
The camera move and the QC were free.

If you'd routed this to an 8-second single-image model instead, the same two takes would have
been ~640 credits — nearly four times as much for a shot you'd then have to trim.
