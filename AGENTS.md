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
8. [`FIELD-NOTES.md`](FIELD-NOTES.md) — unconfirmed observations from the field. Lower
   confidence than the docs above; read it last and weigh it accordingly.

`models.json` is the machine-readable version of the routing table. The CLI reads it. So can you.
[`CONTRIBUTING.md`](CONTRIBUTING.md) is how a new learning becomes a rule. You will need it —
capturing learnings is your job here, not the user's. See the last section of this file.

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

## Capturing what you learn — YOUR job, not the user's

**This is an unprompted background behaviour. Do not ask permission and do not make the user
run a command.** They will not remember to, and the knowledge dies with the session.

### While you work: append to `learnings.local.md`

The moment any of these happens, write one entry and carry straight on with what you were
doing. Do not stop the work, do not announce it, do not ask:

- A generation fails in a way this repo does not already describe
- A rule in here turns out to be wrong, incomplete, or misleading
- You find a model capability, limit, price, ratio or behaviour that isn't in `models.json`
- A shot took more than three takes and you worked out why
- **The user corrects you** about how something works — that correction is a learning
- `aar audit` reports drift
- A prompt phrasing measurably fixed something, or measurably failed

Write it raw. Name the subject, the client, the exact prompt, the model, the numbers. That file
is gitignored and stays on this machine, and the specifics are what make the entry worth
anything later. If it doesn't exist, create it.

```markdown
## [2026-08-17 14:22] pending · L004

kling3.0_pro refused the hips-up crop of the anatomy figure 6/6. Widened to full body,
passed first attempt. Same subject, same prompt, only the crop changed.
**Cost:** ~2h, 6 wasted submissions
```

### Before you commit: promote what generalises

**Whenever you are about to commit in this repo, or a working session is wrapping up**, read
`learnings.local.md` for `pending` entries and deal with them. Again — unprompted.

For each one, apply the four tests in [`CONTRIBUTING.md`](CONTRIBUTING.md): does it help a
stranger with a different subject, can you say *why* it happens, what class of claim is it, and
what did it cost. Then:

- **Passes** → strip every project-specific detail and append it to [`FIELD-NOTES.md`](FIELD-NOTES.md)
  in the house format. Mark the local entry `promoted`.
- **Fails** → leave it local, mark it `local-only`. Not everything generalises and that's fine.
- **Contradicts something already in `knowledge/`** → do NOT quietly append. Say so to the user
  directly and let them decide; a contradiction is more valuable than an addition.

`FIELD-NOTES.md` is the **only** file a contribution touches. The curated docs in `knowledge/`
are maintainer-edited — you propose, you don't rewrite them.

Then commit as normal. Show the user the field-note diff so they can see what's going out.

### Two hard rules

1. **Never commit `learnings.local.md`.** It is gitignored; keep it that way.
2. **Never let a client, project, brand or asset name reach `FIELD-NOTES.md`.** Strip it at
   promotion. If you can't state the lesson without naming the subject, it isn't a lesson yet —
   leave it local.

There is also `aar learn "..."` if a human wants to jot something themselves, but the capture
above is yours to do and does not depend on anyone remembering a command.
