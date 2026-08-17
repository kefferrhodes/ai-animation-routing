# Prompting — the rules, and the failure each one prevents

Every rule below exists because a generation came back wrong. Where the wrong output is
instructive it's described, because the shape of the failure is what tells you when the rule
applies to a job it wasn't written for.

Image prompts and motion prompts fail differently. They're separated.

---

# Motion prompts

## 1. The keyframe is the environment

**Describe only what moves.**

Every word you spend on the setting, the lighting, the background or the props is a word the
model tries to satisfy — including when those things are already in the picture you gave it.
Mention "warm afternoon light through a window" over an image that already has warm afternoon
light through a window, and the model doesn't nod along; it generates *more*, or different, or
somewhere else. One shot was described with its (already present) environment and the model
built an entirely invented tunnel of scenery to honour the words.

The image carries the scene. The prompt carries the motion. That's the whole division.

**Bad:** "In a warm sunlit kitchen, a hand lifts a ceramic mug from a wooden table."
**Good:** "The hand lifts the mug straight up about fifteen centimetres and holds it there."

## 2. Name the one thing that moves, then freeze everything else out loud

Stating what moves is not enough. You have to state what doesn't.

> "Her mid-back rounds forward. Her pelvis and hips stay exactly as they are, her feet stay
> planted on the same spot, and her head stays where it is."

Without the second sentence, other things drift, and a shot where two things changed when one
was supposed to is unusable — you can't cut it against its neighbours.

Freeze the camera explicitly too, in the same breath: *"the camera is completely locked — it
does not pan, tilt, push, orbit or drift at all."* Models add camera moves unprompted.

## 3. Bound every motion — models ride verbs to their maximum

Give a model a verb and it will perform the most extreme version of that verb it can. Ask for
a slouch and you get a forehead on the desk. Ask for a lean and you get a fall.

Cap it in the prompt, in plain language, and name the boundary:

> "The slouch stays subtle. He remains upright and keeps typing the entire time, and his head
> never comes near the desk."

Naming what "too far" looks like works better than adjectives. "Subtle" is a word the model
weighs against everything else in the prompt; "his head never comes near the desk" is a
constraint it can check itself against.

## 4. Never ask a model to fill time with motion that doesn't exist

A real version of your action takes as long as it takes. If the action is one second and you
ask for a five-second clip, the model **invents motion to fill the gap** — a rehearsal move, a
pause and restart, or the action performed and then reversed back through the same positions.

This is a nasty one because it is invisible in a contact sheet. A 21-frame grid passed a clip
that contained five direction reversals; every individual frame was a legitimate pose from the
action, they were just in the wrong order.

The framing that works is to describe the clip as slow motion of a single move:

> "**This is extreme slow motion — the whole clip covers ONE short movement, filmed at very
> high frame rate and played back slowed right down. The single move is stretched evenly across
> the entire clip so it is still travelling at the last frame. Do not speed it up and then
> wait, and do not add any extra movement to fill the time.** One single continuous move in one
> direction, from the very first frame to the very last. The motion never reverses, never goes
> back the way it came, and never returns to the starting position part-way through."

That took reversals from five to one on the shot that produced it. Note what *doesn't* work:
asking for "a slower version" is read as "perform it, then wait."

Check for it with `aar qc` — direction reversals are one of the reported metrics.

## 5. Ban the failure mode by name

Once you know how a shot type fails, say the failure out loud as a prohibition. It measurably
helps:

> "No dissolving, no fading, no cross-fading, no morphing between images, no ghosting or double
> exposure."

## 6. Protect faces explicitly — they degrade first

Faces and fine features are the first thing to go, and the first thing a viewer notices:

> "His facial features, ears and skull stay completely intact — only the POSITION of the head
> changes."

## 7. Pin the scale of anything you add

Introduce a new object or a second subject without a size reference and you get comically wrong
scale — giant hands next to a doll-sized figure. Anchor it to something already in frame:

> "Exactly life-size — the same size as the figure's own hands."

## 8. Negative prompts often lose to model bias

Telling a model that an object is absent reliably produced the object, take after take, on a
shot whose scene type strongly implied it. If a model has a strong prior that your scene
contains a thing, telling it not to include the thing puts the word in the prompt and the thing
in the frame.

**If something must be absent, remove it from the source image, or edit it out of the output
afterwards.** Treat negatives as a weak hint, not a control.

(The exception is negatives about *rendering behaviour* — "no cross-fading", "no text" — which
do work, because they describe an operation rather than an object.)

## 9. Over-specify stillness for locked plates

If the shot is meant to be a near-still plate, "the subject stays still" is not enough:

> "He does not drift, sway, lean or shift position at all. His feet stay on exactly the same
> spot. He stays the same size in frame throughout."

## 10. Say what geometry actually means

Technical shorthand is not self-explanatory to a model. A camera position named with an
industry term produced something else entirely until it was spelled out in terms of what is
visible in frame: *what you can see of the subject, which way they face, and what this is
NOT* ("this is not a side view, not a profile, not a front view").

If a term in your prompt is jargon, replace it with a description of the resulting picture.

## 11. Repeat critical constraints locally, not just globally

A constraint stated once at the top of a long prompt gets diluted. If a rule has to hold at a
specific moment in the shot, restate it inside the description of that moment. A global "stays
in position" was ignored at the one point in the action where the model's prior was strongest;
the fix was to repeat the constraint inside that position's own text and describe what wrong
looks like there.

---

# Image prompts and edits

## 12. Edit-derive, never regenerate

Every variant should be an **edit of an approved parent image**, with the parent attached, in a
fresh request. Never rely on conversation memory, and never regenerate a subject from text
alone — text re-rolls identity every single time.

The instruction shape that works names what stays before what changes:

> "Return THE SAME SHOT — same locked camera, same framing, distance, lens, lighting,
> background, floor, shadow, and the same subject — with [one thing] changed. The new state:
> [describe only the change]."

## 13. Attach only the references you want obeyed

A reference image in the stack is an instruction. Leaving an old style anchor attached
alongside a newer canonical frame made the model snap the subject back to the anchor's pose
and camera, wasting both takes. **Once you have a canonical in-context frame, drop the earlier
anchors** — that frame already carries style, camera and pose, and the anchor only fights it.

## 14. No metaphors in image prompts

Image models render what you say, literally. A metaphorical description of a mechanism
produced the literal mechanical object bolted onto the subject. Describe only what should be
visible — form, material, light, colour. Keep the metaphor in the voiceover and the caption,
where it belongs.

## 15. Pin the properties you're not changing but that drift anyway

Some properties drift under editing even when untouched. Colour saturation is the usual
suspect: an edit request that said nothing about colour came back desaturated across the whole
image. State the invariant explicitly — *"the colours stay exactly as saturated as they are"* —
for anything you're relying on.

Likewise, confine a described effect to its region or it will spread: an instruction to make a
surface look wet smeared speculars across neighbouring surfaces until it was scoped to
*"ONLY the [region] — everything else stays matte and dry."*

## 16. Generate at the aspect ratio you need

Fork aspect ratios at the keyframe, not at the video. Generate each ratio natively, or
outpaint an approved frame to the second ratio and confirm the subject is unchanged. Cropping
finished video to a different ratio throws away resolution and recomposes the shot badly.

Some models also behave differently by ratio: vertical framings baited unstoppable slow zooms
on a model that was well-behaved in widescreen. If you hit that, generate wide and centre-crop.

---

# Never generate

**Text, labels, numbers, arrows, counters, and precisely-timed effects.** Composite them.

- Models render text badly and inconsistently, and a number that has to be *correct* is not
  something to leave to a sampler.
- An effect that has to start, stop or travel at an exact time cannot be trusted to a model.
  In production, a clip's effect extinguished itself before the moment it was supposed to mark
  — and once it's not in the render, no amount of post can recover it.

The general rule: **generate the plate clean, add the effect procedurally.** You get exact
control, you get it for free, and it's the same amount of work.
