# AGENTS.md — routing instructions for the assistant

You are helping someone generate images and video with AI models. This repo exists because
picking the wrong model is the single most expensive mistake in this work, and it is a mistake
you can avoid for free by reading a table.

Everything here was learned by getting it wrong first, on a real paid production. Treat the
rules as load-bearing, not as suggestions.

---

## Read order

1. This file — routing and the non-negotiables. Enough for most jobs.
2. [`knowledge/routing.md`](knowledge/routing.md) — the reasoning behind each routing decision.
3. [`knowledge/prompting.md`](knowledge/prompting.md) — before you write any prompt.
4. [`knowledge/failures.md`](knowledge/failures.md) — when something comes back wrong.
5. [`knowledge/qc.md`](knowledge/qc.md) — before you tell the user a shot is done.
6. [`knowledge/workflow.md`](knowledge/workflow.md) — one shot start to finish.
7. [`knowledge/cost.md`](knowledge/cost.md) — before you spend a lot of someone's money.

`models.json` is the machine-readable version of the routing table. The CLI reads it. So can you.
[`CONTRIBUTING.md`](CONTRIBUTING.md) is how a new learning becomes a rule — read it before you
propose an edit to anything in `knowledge/`.

---

## First: work out what kind of job this is

Ask yourself these in order. The first "yes" routes the job.

| Question | If yes |
|---|---|
| Does the shot have a **defined start AND end state**? | **Keyframe pair.** Generate both stills, then `aar video --first A.png --last B.png`. This is the highest-quality path and you should reach for it whenever the shot admits it. |
| Is it **one image that should come alive** (idle, ambient, small motion)? | Single-image i2v. `aar video --first A.png`. Bound the motion hard — see below. |
| Do you have **a clip you like** and want one thing changed? | Video-to-video. `aar edit clip.mp4 "remove the spoon"`. Do not regenerate the whole shot. |
| Is it **a still**, or a variation on a still? | Image generation / image edit. `aar image`. |
| Is the shot **text, labels, numbers, arrows, counters, or a precisely-timed effect**? | **Do not generate it.** Composite it afterwards. Models place text badly and time effects worse. |

**Do not build motion by interpolating between two stills.** Frame interpolation is a crossfade.
It warps pixels between endpoints, so anything the two images disagree on — an ear, a face, an
edge — dissolves instead of moving. It reads as cheap and everyone notices. If you have two
states, give both to a video model as keyframes and let it generate the motion.

---

## The routing table

Current as of the `verified` dates in `models.json`. Model names rot — run `aar probe` to
re-derive the live list for free before trusting any row.

| Job | Reach for | Why |
|---|---|---|
| Two keyframes (start → end) | `kling3.0_pro` | Accepts the `promptImage` array, 1080p native, ~85 credits against 200–340 for the alternatives. |
| Two keyframes, first choice blocked | `seedance2`, then `hailuo3` | Different vendors, different moderation classifiers. |
| Two keyframes, cheap test run | `seedance2_mini` | ~80 credits. Confirm a keyframe pair works before paying for a good take. |
| Single image → motion, composition must stay put | `kling3.0_pro` | Holds framing. Lowest measured jitter on near-still shots. |
| Single image → motion, previous choice refuses the image | `veo3.1` | Rarely blocks. Historically re-stages long takes — moves and resizes the subject — so verify before trusting it with a locked composition. |
| Change one thing in a clip you already like | `aleph2` (video-to-video) | Obeys remove/add-object instructions well. |
| Need above 1080p | `seedance2` at a 4K ratio | It generates 3840×2160 natively. Beats generating small and upscaling — no invented detail, no stutter risk. |
| Upscale (last resort) | `magnific_video_upscaler_creative` | 2×, genuinely sharper. Safe on CG, **breaks live-action fine texture**. Generate at delivery resolution instead where you can. |
| Stills and still edits | `gemini-3-pro-image-preview` | Edit-derive from an approved parent, never regenerate from text. |

**Cannot take two keyframes** (verified 2026-08-17): `gen4`, `gen4_turbo`, `gen4.5`,
`grok_imagine_1_5`, `gemini_omni_flash`. The API rejects the array outright. If a shot needs a
start and an end, these are not options — no amount of prompting changes this.

**`gen4.5` has no 1080-line option** — measured 2026-08-17, its largest short side is 960 and
its landscape ratios stop at 1280×720. `kling3.0_pro` does 1920×1080 and reaches 1440. Choosing
the right model deletes an entire upscale step and its risk.

Run `aar audit` to see the current resolution tier of every model — it reports the largest short
side each one offers, which is what "is this a 1080p model?" actually means. As of 2026-08-17
the `gen4` family, `kling3.0_standard`, `seedance2_fast` and `seedance2_mini` all top out below
1080 lines. **Check before you plan a pipeline around upscaling.**

> ### This table rots faster than you would think
>
> Between 2026-08-15 and 2026-08-17, on the same API: **`veo3` was removed entirely**, and
> **`veo3.1` gained keyframe-pair support it did not previously have.** Two days. A document
> saying "veo3 is your fallback, and it cannot take two keyframes" was wrong on both counts by
> the time it was published.
>
> That is what `aar probe` is for. Run it before you trust anything above.

---

## Non-negotiables

1. **Never resubmit a moderation-blocked input unchanged.** Repeatedly hammering a filter with
   the same rejected input is how accounts get suspended. Change the framing, change the
   description, or change the vendor. The CLI refuses to do it for you.
2. **Never bake text, labels, numbers or arrows into a generation.** Composite them.
3. **Never ship a generation without looking at the encoded output file.** Not the source, not
   the intent, not a sample of frames. See `knowledge/qc.md` rule 0.
4. **Never overwrite an earlier take.** The first take is a real candidate and is often the
   one the client picks. Keep versions, offer the comparison.
5. **Never claim a shot is clean if you have not checked it.** If you are writing a caveat,
   you are not finished — iterate instead. Generation is cheap; a client noticing something
   you already knew about is not.
6. **Never spend the user's credits on a large batch without saying what it will cost first.**
   `aar` prints an estimate and the balance. Show them.

---

## Prompt rules, compressed

The long version with worked examples is in [`knowledge/prompting.md`](knowledge/prompting.md).

- **The keyframe is the environment.** Describe only what moves. Mention the setting, the
  lighting or the background and the model will invent scenery to satisfy your words —
  including scenery that is already in the picture.
- **Name the one thing that moves, then freeze everything else out loud.** "Her hand lifts the
  cup. Her shoulders, head and the table stay exactly as they are."
- **Bound every motion.** Models ride verbs to their maximum: "slouch" gets you a forehead on
  the desk. Cap it — "stays subtle," "never comes near the table" — and name what must not move.
- **Ban the failure mode by name.** "No dissolving, no fading, no cross-fading, no morphing
  between images" measurably helps.
- **Protect faces explicitly.** They degrade first: "facial features, ears and skull stay
  completely intact; only the position of the head changes."
- **Pin the scale of anything you add.** Unpinned, you get giant hands and a doll-sized subject.
- **Negative prompts often lose to model bias.** Telling a model an object is absent puts the
  word in the prompt and the object in the frame. If something must be absent, remove it from
  the source image or edit it out afterwards.
- **Never ask a model to fill time with motion that does not exist.** A 1-second action
  stretched to a 5-second clip makes the model invent a rehearsal move and swing back through
  the same positions. Say it is extreme slow motion of one short move, evenly stretched, still
  travelling at the last frame.

---

## Using the CLI

The CLI is transport only. It handles auth, base64, submission, polling, download, conforming
and contact sheets — the parts that are easy to get wrong and expensive to get wrong twice.
All judgment stays with you.

```bash
aar doctor                                    # check keys resolve, show balance
aar models                                    # routing table from models.json
aar probe image_to_video                      # re-derive live model list, free, no credits

aar image "a ceramic mug on a linen cloth" -o mug.png
aar image "same shot, the mug is now full of coffee" --ref mug.png -o mug-full.png

aar video --first mug.png --last mug-full.png "coffee pours in..." -o pour.mp4
aar video --first mug.png "steam rises gently..." -o idle.mp4

aar edit pour.mp4 "remove the spoon"
aar upscale pour.mp4

aar qc pour.mp4 --first mug.png --last mug-full.png --sheet

aar audit                                     # is models.json still true?
aar learn "what just went wrong" --cost "…"   # captured locally, gitignored
```

`aar` auto-conforms output (models return off-spec dimensions and silent audio tracks — this
is normal, not an anomaly) and writes a contact sheet after every generation. Look at it.

---

## When to stop and ask the user

- Before a batch that costs a meaningful fraction of their balance.
- When a shot has failed 3+ times for the same reason — the keyframe is usually wrong, not
  the prompt. Changing the prompt a fourth time is how you burn an afternoon.
- When they have asked for something a model cannot do (two keyframes on a single-image model,
  precise text, exact effect timing). Say so and propose the compositing route instead.
- When output is moderation-blocked twice across two vendors. Something about the subject or
  the framing needs a human decision.

---

## When something surprises you, capture it

If a shot fails in a way this repo does not describe, or a rule here turns out to be wrong,
run `aar learn "<what happened>" --cost "<what it cost>"` before moving on. It writes to a
gitignored local file — no ceremony, nothing published.

Do this **at the moment of failure**, while you still know why. Later, `aar learn --review`
hands those entries plus the de-projection rubric back to you, and you turn the ones that
qualify into proposed edits to `knowledge/`.

Two rules about that file: never commit it, and never let a learning reach `knowledge/` with a
client, subject or project name still in it. See [`CONTRIBUTING.md`](CONTRIBUTING.md).
