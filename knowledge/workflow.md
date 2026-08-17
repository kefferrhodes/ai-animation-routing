# One shot, start to finish

The order matters. Most wasted money in this work comes from doing step 5 before step 1.

---

## 1. Decide what the shot does, and frame it for that

Before anything is generated, answer: where does this land, and what does a viewer need to see?

**Never default to the framing your source image happens to have.** If the thing that changes
is a small part of a wide frame, three things go wrong at once: nobody sees it, the model has
fewer pixels to work with so it renders worse, and the shot reads as unfocused.

- **Inserts and detail shots:** crop tight. The change fills the frame.
- **Wides:** establishing, and transitions where the whole subject transforms.
- If the shot is about a specific part of the subject, pick a view where that part is
  **visible and unobstructed**. One shot shipped where a glow appeared to come out of a
  subject's bicep, because the relevant anatomy was hidden behind an arm in the chosen view.
- Crop through the forehead, never through the eyes. A face cut at the eyes reads as a mistake.

Framing is a decision, not a leftover.

---

## 2. Decide the route

Does the shot have a defined end state?

- **Yes** → keyframe pair. You need two stills.
- **No** → single image with bounded motion. You need one.
- **Already have a clip you like, one thing wrong** → video edit, or fix the keyframe and
  regenerate. See [`routing.md`](routing.md).

Check `models.json` (or run `aar probe`) and confirm your model actually supports what you need
before you build stills for it. Building a start and an end frame for a model that only takes
one image is a wasted afternoon.

---

## 3. Build the stills

- **The first one from scratch, everything else edit-derived from it.** Attach the parent image
  every time. Never regenerate a subject from text alone.
- Generate at the aspect ratio you need. Fork ratios here, at the keyframe — never by cropping
  finished video.
- **Composite onto a controlled background.** A raw generation's background is unstable and
  usually reads as unfinished. Matte the subject and comp onto a plate you own, so every shot
  in the sequence shares a background by construction.
- Crop to the framing you chose in step 1.
- Look at both frames side by side at the same scale before generating anything. If the subject
  doesn't look like the same subject in your two keyframes, the clip will be worse, not better.

---

## 4. Generate

```bash
aar video --first start.png --last end.png "…" -o shot_t1.mp4
```

- **Two takes minimum.** The first take is a real candidate, but so is the second, and you want
  the comparison.
- Budget **3–6 takes**. Pick, don't polish.
- If it's not close by take six, **the keyframes are wrong** — go back to step 3. Changing the
  motion prompt a seventh time is how afternoons disappear.
- If it's refused: don't resubmit unchanged. Change the framing or switch vendor.

---

## 5. QC

```bash
aar qc shot_t1.mp4 --first start.png --last end.png --sheet
```

Then read [`qc.md`](qc.md) and actually do it. The short list:

- View the encoded file, every frame
- Check for direction reversals
- Check both endpoints were honoured
- Check identity holds across the shot
- Check nothing moved that was told not to
- Check nothing is in frame that shouldn't be — tracked across frames, not judged from a still

If something's wrong, **decide whether it's a keyframe problem or a take problem**. Keyframe
problems repeat across takes; take problems don't.

---

## 6. Fix, if needed

- **Something in the subject is wrong** → fix the keyframe, regenerate.
- **An object in the scene needs removing** → video edit is fine.
- **You want a region restyled** → regenerate. Video edits don't do this.
- **After any fix**, diff against the original and look at everything that changed.

---

## 7. Add the camera move in post

Not in the prompt. Animate a crop window across the rendered frames:

- Push toward whatever the shot is about, or pan with the subject drifting across frame
- **Ease in and out** — constant speed that stops dead reads as a crop, not a camera
- 3–12% of frame width over five seconds
- Keep full output resolution by cropping from a larger source, or by generating wider than you
  deliver

Exception: don't bake a move into a plate you'll be tracking effects onto later. A moving
background means the effect has to be tracked rather than drawn.

---

## 8. Composite everything that isn't photographable

Text, labels, numbers, arrows, counters, and any effect with exact timing. Generated plate
underneath, everything precise on top. You get exact control for free.

Keep effects **on the subject** — masked by the subject's alpha — rather than sweeping across
the whole frame including the background. A full-frame effect band reads as a transition
preset; a subtle effect confined to the subject reads as production value.

---

## 9. Conform, file, archive

- Conform to your delivery spec and strip stray audio (`aar` does this on generation)
- File the approved take
- **Archive what it replaced — don't delete it.** Put a one-line note next to it saying why it
  was replaced. The rejected work is how the next person avoids repeating it, and sometimes the
  client changes their mind back.

---

# Working practices that saved time

**Name things so a stranger can sort them.** `shotname_take03_1080.mp4`. Takes numbered, never
overwritten.

**Keep a running log of what failed and why**, in the repo, next to the work. Not a
retrospective — a log written as it happens. Almost everything in this repo came out of one.

**Batch generation, then QC in one pass.** Generation is slow and mostly waiting; QC is fast and
needs attention. Interleaving them wastes both.

**Print the cost before a batch, and the balance after.** Someone is paying for this and it
should never be a surprise.

**Never detach a long-running job with `&` from inside an agent session** — it dies when the
tool call tears down. Use your harness's background mode.
