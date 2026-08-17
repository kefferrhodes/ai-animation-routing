# ai-animation-routing

**Which AI model to use for which image or video job, and why — plus a thin CLI so your
assistant doesn't have to guess at the API.**

Point any LLM at this repo — Claude Code, Codex, Cursor, Gemini CLI, or a chat window you
paste into — describe the shot you want in plain language, and it routes you to the right
model, writes a prompt that respects the failure modes, generates it, and checks the output
before telling you it's done.

The knowledge is the product. The CLI is transport.

---

## Why this exists

Generative video models look interchangeable and are not. The differences that matter aren't
in the marketing copy:

- Some accept **two keyframes** (a start and an end frame). Most accept only one. If your shot
  has a defined end state and you pick a single-image model, the subject drifts — there is
  nothing pinning the far end — and no amount of prompting fixes it.
- One of them **silently caps at 720p** while another does 1080p natively, which is the
  difference between needing an upscale pass and not.
- One is excellent at **changing one thing in a clip you already like** and useless at
  restyling a region.
- Their moderation filters have different shapes, so a shot one vendor refuses will often
  clear at another on the first try.

None of that is documented anywhere convenient. It was learned across a few hundred paid
generations on a real production, mostly by getting it wrong first. This repo is that
knowledge, extracted and de-projected so it applies to a product shot, an explainer, or a
character sequence just as well as to what it was learned on.

## What you get

| | |
|---|---|
| [`AGENTS.md`](AGENTS.md) | The router. Your assistant reads this first. `CLAUDE.md` points here too. |
| [`knowledge/`](knowledge/) | Routing reasoning, prompt rules, the failure catalogue, QC doctrine, workflow, cost. |
| [`cli/`](cli/) | `aar` — generate, edit, upscale, probe, QC. Zero Python dependencies. |
| [`recipes/`](recipes/) | Three worked jobs, end to end, with the actual commands. |
| [`models.json`](models.json) | Machine-readable routing table with capability flags and verification dates. |

## Quick start

```bash
git clone https://github.com/kefferrhodes/ai-animation-routing.git
cd ai-animation-routing
cp .env.example .env      # then fill it in — see SETUP.md
python3 cli/aar.py doctor
```

`doctor` tells you which keys resolved, what balance you have, and whether `ffmpeg` is
reachable. Read [`SETUP.md`](SETUP.md) first — it says what each key is for, what it costs,
and when you can skip one.

Then open your assistant in this directory and describe a shot:

> "I want a slow push on a ceramic mug as coffee pours into it, five seconds, 1080p."

It should route you to a keyframe pair, generate both stills, generate the motion, add the
camera move in post, and QC the file before handing it back.

## Requirements

- Python 3.9+ — **no pip packages required**, standard library only
- `curl` — present on macOS and most Linux
- `ffmpeg` — for conforming and QC. `brew install ffmpeg` / `apt install ffmpeg`
- API keys — see [`SETUP.md`](SETUP.md)

## Honest scope

- **This is not a wrapper library.** It is a set of rules with just enough code to make them
  executable. If you want an SDK, use the vendors'.
- **Model names and prices rot.** Everything is dated. `aar probe` re-derives the live model
  list from the API for free, without creating a task or spending credits — run it before
  trusting a table that's a few months old.
- **The observations came from one production.** Where a finding is a structural fact about
  how these models work, it's stated as a rule. Where it's a measurement that might not
  generalise, it's dated and hedged. Those are marked distinctly on purpose.
- **No affiliation with any model vendor.** Nothing here is a benchmark; it's field notes.

## Contributing

Corrections are the most valuable thing you can add — especially "this model now does X" or
"this stopped being true." Include the date and how you verified it. Keep findings separated
into structural facts vs. dated measurements, the way the existing docs do.

## Licence

MIT. See [`LICENSE`](LICENSE).
