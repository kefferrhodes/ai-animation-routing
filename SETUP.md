# Setup — which keys you need, and whether you need them

Read this before signing up for anything. Each key below says what it buys you, what breaks
without it, roughly what it costs, and when you can skip it.

Two keys cover everything in this repo. Neither is required to read the knowledge docs.

---

## 1. Runway — the video gateway

**What it is for.** Every video operation: motion from keyframes, motion from a single image,
video-to-video edits, and upscaling. Runway's developer API acts as a gateway to several
vendors' models — Kling, Seedance, Veo, Aleph, Magnific — so one key and one bill reaches all
of them. That is the main reason this repo routes through it rather than through five
separate vendor accounts.

**What breaks without it.** All video. Image generation still works.

> ### ⚠️ The trap that costs people money
>
> **The Runway developer API bills separately from the Runway app subscription.** An Unlimited
> plan on runwayml.com gives you unlimited generations *in the web app* and **zero** API
> credits. The API is prepaid credits, bought separately, in the developer portal. People
> subscribe expecting the API to be covered and it is not.
>
> If you only ever want to generate by hand in a browser, buy the subscription and ignore this
> repo's CLI. If you want your assistant to drive generation, you need API credits.

**What it costs.** Credits, prepaid. Observed at 10,000 credits for about $100, so roughly
**$0.01 per credit**. Per-operation costs observed in production (2026-08 — verify, these move):

| Operation | Credits | ≈ USD |
|---|---|---|
| Keyframe-pair video, 5s, 1080p (`kling3.0_pro`) | ~85 | ~$0.85 |
| Single-image video, 8s, 720p (`veo3.1`) | ~320 | ~$3.20 |
| Video-to-video edit, 8s (`aleph2`) | ~224 | ~$2.24 |
| 2× upscale, 5s clip (`magnific_video_upscaler_creative`) | ~109 | ~$1.09 |

Budget **3–6 takes per shot**. A shot that lands on take 1 is luck, not skill. At the rates
above a finished 5-second shot is typically $3–5 of generation, and a whole short sequence
runs $50–150. See [`knowledge/cost.md`](knowledge/cost.md) before committing to a batch.

**How to get one.** Sign in at [dev.runwayml.com](https://dev.runwayml.com), create an API key
in the developer portal, and buy credits there. The key looks like `key_...`. `aar doctor`
will read your balance back to you so you know it worked.

**Can you skip it?** Only if you're doing stills.

---

## 2. Google Gemini — images and image edits

**What it is for.** Every still: generating a frame from scratch, and — more importantly —
**editing an approved frame into a variant**. Nearly all the keyframes in a good sequence are
edits of one parent image, not independent generations. That is what keeps a subject looking
like itself from shot to shot.

**What breaks without it.** Image generation and editing. You can still animate images you
already have from any other source.

**What it costs.** Billed per image on Google's Gemini API pricing. In practice it is
inexpensive next to video — cents per image against dollars per clip — but Google changes
these numbers, so read the current
[Gemini API pricing](https://ai.google.dev/pricing) rather than trusting a figure here. There
is a free tier for evaluation; production image generation requires billing enabled on the
project.

**How to get one.** Create a key at [aistudio.google.com](https://aistudio.google.com/apikey).
Enable billing on the associated Google Cloud project if you plan to generate more than a
handful of images. The key looks like `AIza...`.

**Can you skip it?** Yes, if you're bringing your own stills — shot photography, renders,
frames from existing footage, or images made in any other tool. The video half of this repo
doesn't care where a keyframe came from.

---

## Wiring it up

```bash
cp .env.example .env
```

Then edit `.env`:

```
RUNWAY_API_KEY=key_xxxxxxxxxxxxxxxxxxxx
GEMINI_API_KEY=AIzaxxxxxxxxxxxxxxxxxxxx
```

Verify:

```bash
python3 cli/aar.py doctor
```

`doctor` reports which keys resolved, your Runway credit balance, and whether `ffmpeg` is
reachable. It never prints a key.

If you'd rather keep keys in your shell profile than in a file, `aar` reads the same variables
from the environment — `.env` is a convenience, not a requirement.

### Keys stay local

`.env` is gitignored. So are `out/`, `*.mp4`, `*.png` and the other generation artefacts. This
repo is meant to be forked and made public; nothing in it should ever carry a credential or
a client's footage. If you add a script, keep reading keys from the environment — never
hardcode, never commit, never log.

If you think you may have committed a key: rotate it first, then clean history. Rotation is
instant and certain; history rewriting is neither.

---

## Optional: ffmpeg

Required for conforming output and for QC. Almost every failure this repo teaches you to catch
is caught by looking at extracted frames.

```bash
brew install ffmpeg          # macOS
sudo apt install ffmpeg      # Debian/Ubuntu
```

If you have the Python package `imageio-ffmpeg` installed for something else, `aar` will find
and use its bundled binary automatically. You do not need to install it on purpose.

---

## Note on `curl`

The CLI shells out to `curl` for every network call instead of using Python's HTTP libraries.
This is deliberate: it keeps the dependency list at zero, and it sidesteps the broken local
certificate stores that some Python installs ship with — a failure mode that costs an hour
and looks like an API outage. If `curl` works in your terminal, `aar` works.
