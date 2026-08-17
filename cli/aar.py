#!/usr/bin/env python3
"""aar — ai-animation-routing.

Thin transport for AI image and video generation. It handles auth, base64, submission,
polling, download, conforming and QC — the parts that are easy to get wrong and expensive
to get wrong twice. All judgment stays with you; read AGENTS.md for that.

    aar doctor                                  keys, balance, ffmpeg
    aar models [job]                            routing table
    aar audit [--deep]                          is models.json still true? diff vs live API
    aar probe [endpoint]                        re-derive live model list from the API

    aar learn "what you learned"                capture locally (gitignored)
    aar learn --review                          hand the inbox + rubric to your assistant

    aar image "PROMPT" [-o out.png] [--ref parent.png ...] [--ratio 16:9]
    aar video "PROMPT" --first a.png [--last b.png] [-o out.mp4]
    aar edit clip.mp4 "remove the spoon" [-o out.mp4]
    aar upscale clip.mp4 [-o out.mp4]

    aar qc clip.mp4 [--first a.png] [--last b.png] [--sheet]
    aar qc --compare source.mp4 processed.mp4

Network goes through curl on purpose: zero Python dependencies, and it sidesteps the broken
local certificate stores some Python installs ship with (a failure mode that costs an hour
and looks like an API outage).
"""
import argparse
import base64
import hashlib
import json
import os
import re
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATE = os.path.join(ROOT, ".aar")
BLOCKED = os.path.join(STATE, "blocked.json")
INBOX = os.path.join(ROOT, "learnings.local.md")

# A 1x1 png. Deliberately invalid input: the validation error it provokes enumerates every
# allowed value for the field being probed. Free on models that pre-validate the image;
# models that don't will CREATE A TASK from it, so anything using this must cancel.
POISON = ("data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJ"
          "AAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==")

RUNWAY_BASE = "https://api.dev.runwayml.com/v1"
RUNWAY_VERSION = "2024-11-06"
GEMINI_BASE = "https://generativelanguage.googleapis.com/v1beta"


# ─────────────────────────────────────────────────────────────── environment ──

def load_env():
    """Read .env from the repo root. Real environment variables win."""
    path = os.path.join(ROOT, ".env")
    if not os.path.exists(path):
        return
    for line in open(path):
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        k, v = k.strip(), v.strip().strip('"').strip("'")
        if k and k not in os.environ:
            os.environ[k] = v


def key(name, what):
    v = os.environ.get(name)
    if not v:
        die(f"{name} is not set — {what}.\nSee SETUP.md, then: cp .env.example .env")
    return v


def die(msg, code=1):
    print(f"\n  ✗ {msg}\n", file=sys.stderr)
    raise SystemExit(code)


def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def models_json():
    with open(os.path.join(ROOT, "models.json")) as f:
        return json.load(f)


# ──────────────────────────────────────────────────────────────────── ffmpeg ──

_FF = None


def ff():
    """Find ffmpeg: PATH first, then the binary bundled with imageio-ffmpeg if present."""
    global _FF
    if _FF:
        return _FF
    p = subprocess.run(["which", "ffmpeg"], capture_output=True, text=True)
    if p.returncode == 0 and p.stdout.strip():
        _FF = p.stdout.strip()
        return _FF
    try:
        import imageio_ffmpeg
        _FF = imageio_ffmpeg.get_ffmpeg_exe()
        return _FF
    except Exception:
        pass
    die("ffmpeg not found. `brew install ffmpeg` or `apt install ffmpeg`.\n"
        "    Needed for conforming output and for QC — and QC is the whole point.")


def probe_media(path):
    """Dimensions, fps, duration, audio presence — parsed from ffmpeg's own report."""
    err = subprocess.run([ff(), "-v", "error", "-i", path, "-f", "null", "-"],
                         capture_output=True, text=True).stderr
    err += subprocess.run([ff(), "-i", path], capture_output=True, text=True).stderr
    info = {"width": None, "height": None, "fps": None, "duration": None, "audio": False}
    m = re.search(r"Video:.*?(\d{2,5})x(\d{2,5})", err)
    if m:
        info["width"], info["height"] = int(m.group(1)), int(m.group(2))
    m = re.search(r"([\d.]+) fps", err)
    if m:
        info["fps"] = float(m.group(1))
    m = re.search(r"Duration: (\d+):(\d+):([\d.]+)", err)
    if m:
        info["duration"] = int(m.group(1)) * 3600 + int(m.group(2)) * 60 + float(m.group(3))
    info["audio"] = "Audio:" in err
    return info


def gray_frames(path, w=160, h=90):
    """Every frame, downscaled to grayscale, as a list of bytes objects."""
    raw = subprocess.run([ff(), "-v", "error", "-i", path, "-vf", f"scale={w}:{h}",
                          "-f", "rawvideo", "-pix_fmt", "gray", "-"],
                         capture_output=True).stdout
    n = len(raw) // (w * h)
    return [raw[i * w * h:(i + 1) * w * h] for i in range(n)]


def rgb_frames(path, w=64, h=36):
    raw = subprocess.run([ff(), "-v", "error", "-i", path, "-vf", f"scale={w}:{h}",
                          "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                         capture_output=True).stdout
    n = len(raw) // (w * h * 3)
    return [raw[i * w * h * 3:(i + 1) * w * h * 3] for i in range(n)]


def conform(src, dst, width=None, height=None):
    """Models return off-spec dimensions (1924x1076 where you asked for 1920x1080) and
    silent audio tracks. Both are normal. Fix both, always."""
    info = probe_media(src)
    w = width or (info["width"] or 1920)
    h = height or (info["height"] or 1080)
    w, h = w - (w % 2), h - (h % 2)
    subprocess.run([ff(), "-y", "-v", "error", "-i", src,
                    "-vf", f"scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h}",
                    "-an", "-c:v", "libx264", "-crf", "16", "-pix_fmt", "yuv420p", dst],
                   capture_output=True)
    return dst


def contact_sheet(src, dst, cols=6, rows=4):
    """A grid of frames. For orienting yourself — NOT for deciding. See knowledge/qc.md."""
    info = probe_media(src)
    total = int((info["duration"] or 5) * (info["fps"] or 24))
    step = max(1, total // (cols * rows))
    subprocess.run([ff(), "-y", "-v", "error", "-i", src,
                    "-vf", f"select=not(mod(n\\,{step})),scale=320:-1,tile={cols}x{rows}",
                    "-frames:v", "1", dst], capture_output=True)
    return dst if os.path.exists(dst) else None


def extract_frame(src, dst, last=False):
    cmd = [ff(), "-y", "-v", "error"]
    if last:
        info = probe_media(src)
        cmd += ["-sseof", "-0.2"]
    cmd += ["-i", src, "-frames:v", "1", "-update", "1", dst]
    subprocess.run(cmd, capture_output=True)
    return dst if os.path.exists(dst) else None


# ─────────────────────────────────────────────────────────────────── network ──

def curl(args, timeout=300):
    p = subprocess.run(["curl", "-s", "--max-time", str(timeout)] + args,
                       capture_output=True, text=True)
    try:
        return json.loads(p.stdout)
    except Exception:
        return {"_raw": (p.stdout or p.stderr or "")[:500]}


def runway(method, path, body=None):
    k = key("RUNWAY_API_KEY", "every video operation needs it")
    args = ["-X", method,
            "-H", f"Authorization: Bearer {k}",
            "-H", f"X-Runway-Version: {RUNWAY_VERSION}",
            "-H", "Content-Type: application/json",
            RUNWAY_BASE + path]
    if body is not None:
        os.makedirs(STATE, exist_ok=True)
        req = os.path.join(STATE, "req.json")
        with open(req, "w") as f:
            json.dump(body, f)
        args += ["-d", f"@{req}"]
    return curl(args)


def balance():
    d = runway("GET", "/organization")
    return d.get("creditBalance")


def data_uri(path):
    mime = "image/png" if path.lower().endswith(".png") else "image/jpeg"
    with open(path, "rb") as f:
        return f"data:{mime};base64," + base64.b64encode(f.read()).decode()


def poll(task_id, dest, every=6, limit=220):
    for _ in range(limit):
        time.sleep(every)
        t = runway("GET", f"/tasks/{task_id}")
        st = t.get("status")
        if st == "SUCCEEDED":
            url = (t.get("output") or [None])[0]
            if not url:
                return False, "succeeded with no output"
            subprocess.run(["curl", "-s", "-o", dest, url], capture_output=True)
            ok = os.path.exists(dest) and os.path.getsize(dest) > 0
            return ok, None if ok else "download produced an empty file"
        if st in ("FAILED", "CANCELLED"):
            return False, json.dumps(t.get("failure") or t)[:400]
    return False, "timed out waiting for the task"


# ───────────────────────────────────────────────── moderation block memory ──
# Never resubmit a blocked input unchanged. That is an account-suspension path, and it is
# also just money on fire — see knowledge/routing.md.

def fingerprint(model, prompt, files):
    h = hashlib.sha256()
    h.update(model.encode())
    h.update(prompt.encode())
    for p in files:
        with open(p, "rb") as f:
            h.update(hashlib.sha256(f.read()).digest())
    return h.hexdigest()[:20]


def blocked_load():
    if os.path.exists(BLOCKED):
        try:
            return json.load(open(BLOCKED))
        except Exception:
            return {}
    return {}


def blocked_record(fp, model, reason):
    os.makedirs(STATE, exist_ok=True)
    d = blocked_load()
    e = d.setdefault(fp, {"model": model, "count": 0, "reason": reason})
    e["count"] += 1
    e["reason"] = reason
    with open(BLOCKED, "w") as f:
        json.dump(d, f, indent=2)
    return e["count"]


def looks_like_moderation(text):
    t = (text or "").lower()
    return any(w in t for w in ("moderation", "safety", "content policy", "policy violation",
                                "flagged", "nsfw", "prohibited", "not allowed"))


# ─────────────────────────────────────────────── live capability inspection ──
# Everything below reads the API's own validation errors. Walking the response structure
# rather than regexing serialised JSON keeps the enumerated allowed-values list intact —
# that list is the entire point.

def api_strings(obj):
    if isinstance(obj, str):
        yield obj
    elif isinstance(obj, dict):
        for v in obj.values():
            yield from api_strings(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from api_strings(v)


def live_model_enum(endpoint="/image_to_video"):
    """Every model the API currently accepts. Free — pure schema validation, no task."""
    d = runway("POST", endpoint, {"model": "__nope__", "promptImage": POISON, "promptText": "x"})
    for s in api_strings(d):
        if "expected one of" in s:
            return re.findall(r'"([^"]+)"', s)
    return None


def live_ratios(model, endpoint="/image_to_video"):
    """Allowed ratios for a model — which is how you find a silent resolution cap. Free."""
    d = runway("POST", endpoint,
               {"model": model, "promptImage": POISON, "promptText": "x", "ratio": "1:1"})
    for s in api_strings(d):
        if "expected one of" in s:
            found = re.findall(r'"(\d+:\d+)"', s)
            if found:
                return found
    return None


def live_keyframe_pair(model, endpoint="/image_to_video"):
    """Does this model accept a first/last keyframe array?

    NOT free on every model. Ones that pre-validate the image reject the poison outright;
    ones that don't create a real billable task, which is cancelled here immediately.
    Returns (supported, estimated_credits_of_the_cancelled_task).

    Fields like ratio and duration are model-specific and validated BEFORE the image, so a
    fixed payload returns 'unclear' on any model with different requirements — a real answer
    to a question we didn't ask. So this adapts: when the API rejects a field, it names the
    allowed values, and we fill one in and retry until the request reaches the image."""
    body = {"model": model, "promptText": "x",
            "promptImage": [{"uri": POISON, "position": "first"},
                            {"uri": POISON, "position": "last"}]}
    for _ in range(5):
        d = runway("POST", endpoint, body)
        if d.get("id"):
            cost = (d.get("estimatedCost") or {}).get("credits")
            runway("DELETE", f"/tasks/{d['id']}")
            return True, cost
        txt = " ".join(api_strings(d)).lower()
        if "<=1 items" in txt:
            return False, None
        if "300px" in txt or "dimension" in txt:
            return True, None

        # Let the error teach us what the payload is missing.
        progressed = False
        if "ratio" not in body:
            for s in api_strings(d):
                if "expected one of" in s:
                    opts = re.findall(r'"(\d+:\d+)"', s)
                    if opts:
                        body["ratio"] = opts[0]
                        progressed = True
                        break
        if not progressed and "duration" in txt and "duration" not in body:
            body["duration"] = 8
            progressed = True
        if not progressed:
            break
    return None, None


# ───────────────────────────────────────────────────────────────── commands ──

def cmd_doctor(a):
    print()
    print("  ai-animation-routing — environment check")
    print("  " + "─" * 44)

    rk = os.environ.get("RUNWAY_API_KEY")
    if rk:
        bal = balance()
        if bal is None:
            print("  RUNWAY_API_KEY   set, but the API did not return a balance")
            print("                   → the key may be invalid or revoked")
        else:
            print(f"  RUNWAY_API_KEY   ok · balance {bal:,} credits (≈ ${bal / 100:,.2f})")
    else:
        print("  RUNWAY_API_KEY   MISSING — all video operations will fail")

    gk = os.environ.get("GEMINI_API_KEY")
    print(f"  GEMINI_API_KEY   {'ok' if gk else 'MISSING — image generation will fail'}")

    try:
        print(f"  ffmpeg           {ff()}")
    except SystemExit:
        print("  ffmpeg           MISSING — conforming and QC will fail")

    blocks = blocked_load()
    if blocks:
        print(f"  blocked inputs   {len(blocks)} remembered (will not be resubmitted unchanged)")

    if not rk or not gk:
        print("\n  → See SETUP.md. It says what each key is for and when you can skip one.")
    print()


def cmd_models(a):
    m = models_json()
    job = (a.job or "").strip()
    print()
    if job:
        ids = m["routes"].get(job)
        if not ids:
            die(f"unknown job '{job}'. Known: {', '.join(m['routes'])}")
        print(f"  {job} → {' → '.join(ids)}   (try in order)")
    else:
        print("  Routing (from models.json, verified " + m["_verified"] + ")")
        print("  " + "─" * 60)
        for k, v in m["routes"].items():
            print(f"  {k:<16} {' → '.join(v)}")
    print()
    for entry in m["models"]:
        if job and entry["id"] not in (m["routes"].get(job) or []):
            continue
        if not job:
            continue
        print(f"  ── {entry['id']}")
        for n in entry.get("notes", []):
            print(f"     · {n}")
        print()
    if not job:
        print("  aar models <job>   for capability notes")
        print("  aar probe          to re-derive the live list from the API (free)\n")


def cmd_probe(a):
    """POST a deliberately invalid request and read the validation error, which enumerates
    the allowed values. This is how the routing table in models.json was derived — use it to
    check the table is still true before trusting it.

    Caveat learned the hard way: it is NOT free on every model. Some validate the image
    eagerly and reject the 1x1 poison outright (no task, nothing spent); others validate
    lazily and CREATE A REAL TASK from it. So every task this function creates is cancelled
    immediately. Cancelling straight away has been observed to cost nothing, but an
    uncancelled probe task will run and bill you."""
    endpoint = a.endpoint if a.endpoint.startswith("/") else "/" + a.endpoint
    poison = ("data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJ"
              "AAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==")
    b0 = balance()
    print(f"\n  Probing {endpoint}.  Balance {b0:,}." if b0 is not None
          else f"\n  Probing {endpoint}.")
    print("  Any task accidentally created by a probe is cancelled immediately.\n")

    probes = [
        ("model list", {"model": "__nope__", "promptImage": poison, "promptText": "x"}),
        ("ratio list", {"model": a.model or "gen4.5", "promptImage": poison,
                        "promptText": "x", "ratio": "1:1"}),
        ("keyframe array support",
         {"model": a.model or "kling3.0_pro", "promptText": "x",
          "promptImage": [{"uri": poison, "position": "first"},
                          {"uri": poison, "position": "last"}]}),
    ]
    def strings(obj):
        """Every string leaf in the response. Walking the structure rather than regexing the
        serialised JSON keeps the enumerated allowed-values list intact — that list is the
        entire reason to run this."""
        if isinstance(obj, str):
            yield obj
        elif isinstance(obj, dict):
            for v in obj.values():
                yield from strings(v)
        elif isinstance(obj, list):
            for v in obj:
                yield from strings(v)

    for label, body in probes:
        d = runway("POST", endpoint, body)
        if d.get("id"):
            # Lazy validator: it made a real task from the poison payload. Kill it now.
            cost = (d.get("estimatedCost") or {}).get("credits")
            runway("DELETE", f"/tasks/{d['id']}")
            print(f"  {label}: ACCEPTED — this model does not pre-validate the image, so the "
                  f"probe created a task.")
            print(f"    Cancelled {d['id']}."
                  + (f"  It would have cost {cost} credits." if cost else ""))
            print(f"    → acceptance IS the answer: this model accepts the payload shape "
                  f"being probed.\n")
            continue
        print(f"  {label}:")
        seen = set()
        for s in strings(d):
            s = s.strip()
            if len(s) < 8 or s in seen:
                continue
            seen.add(s)
            print(f"    {s[:900]}")
        text = " ".join(seen).lower()
        if label == "keyframe array support":
            if "expected string" in text and "dimension" not in text and "300px" not in text:
                print("    → reads as ARRAY NOT SUPPORTED (single image only)")
            elif "dimension" in text or "px" in text:
                print("    → array accepted; it rejected the 1x1 pixel image, which is the "
                      "expected result for a keyframe-pair capable model")
        print()


def cmd_audit(a):
    """Diff the live API against models.json and say exactly what moved.

    Safe mode touches only schema validation — no task is ever created, nothing is spent.
    --deep additionally re-checks keyframe-pair support, which DOES create tasks on models
    that validate lazily; each one is cancelled immediately."""
    m = models_json()
    snap = m.get("live_model_list", {})
    known = snap.get("models", [])
    print()
    print("  Auditing the live API against models.json")
    print(f"  snapshot verified {snap.get('verified', '?')} · {len(known)} models recorded")
    print("  " + "─" * 60)

    live = live_model_enum(snap.get("endpoint", "/image_to_video"))
    if not live:
        die("could not read the model enum. Check RUNWAY_API_KEY and try `aar doctor`.")

    gone = [x for x in known if x not in live]
    new = [x for x in live if x not in known]
    drift = bool(gone or new)

    print(f"\n  live now: {len(live)} models")
    if gone:
        print("\n  REMOVED since the snapshot:")
        for x in gone:
            used = [e for e in m["models"] if e["id"] == x and e.get("use_for")]
            warn = "  ← models.json still routes to this" if used else ""
            print(f"    − {x}{warn}")
    if new:
        print("\n  NEW since the snapshot:")
        for x in new:
            print(f"    + {x}")
    if not drift:
        print("\n  Model list unchanged.")

    # Resolution tier, measured as the largest SHORT SIDE the model offers.
    #
    # Short side, not pixel area, and not width. Area ranks an ultrawide 1584x672 above
    # 1280x720 even though it has fewer lines; width ranks a 3840x3840 square as "4K wide"
    # when what you wanted to know was how many lines you get. Short side is what
    # "is this a 1080p model?" actually means, and it is orientation-neutral.
    print("\n  Resolution tier — largest short side offered (documented models only):")
    for e in m["models"]:
        if e.get("provider") != "runway" or e.get("endpoint") != "/image_to_video":
            continue
        if e.get("status") == "REMOVED" or e["id"] not in live:
            continue
        ratios = live_ratios(e["id"])
        if not ratios:
            continue
        best = max(ratios, key=lambda r: min(int(r.split(":")[0]), int(r.split(":")[1])))
        tier = min(int(best.split(":")[0]), int(best.split(":")[1]))
        recorded = e.get("max_short_side")
        line = f"    {e['id']:<22} {tier:>5}  ({best})"
        if recorded is not None and recorded != tier:
            drift = True
            line += f"   models.json says {recorded}  ← CHANGED"
        elif recorded is None:
            line += "   not recorded"
        # The claim that actually drives routing.
        if tier < 1080:
            line += "   ← no 1080-line option"
        print(line)

    if a.deep:
        print("\n  Keyframe-pair support (creates tasks on lazy validators — each cancelled):")
        caps = m.get("capabilities", {})
        yes, no = caps.get("keyframe_pair_yes", []), caps.get("keyframe_pair_no", [])
        unresolved = []
        for model in live:
            supported, cost = live_keyframe_pair(model)
            if supported is None:
                unresolved.append(model)
                print(f"    {model:<22} unclear — the probe never reached the image field")
                continue
            was = True if model in yes else (False if model in no else None)
            note = ""
            if was is not None and was != supported:
                drift = True
                note = f"  ← CHANGED (was {'yes' if was else 'no'})"
            elif was is None:
                note = "  ← not recorded"
            billed = f"  [cancelled a {cost}cr task]" if cost else ""
            print(f"    {model:<22} {'yes' if supported else 'no ':<4}{note}{billed}")
        if unresolved:
            print(f"\n    {len(unresolved)} model(s) unresolved: {', '.join(unresolved)}")
            print("    Not a pass and not a fail — go probe them by hand before relying on them.")

    print()
    if drift:
        print("  ⚠  models.json is out of date. Update it, then record what you learned:")
        print("       aar learn \"<what changed and what it means for routing>\"")
        print("     Anything you generate against a stale table is a coin flip.")
    else:
        print("  ✓ models.json matches the live API.")
    print()
    raise SystemExit(1 if drift else 0)


# ────────────────────────────────────────────────────────── learnings inbox ──

INBOX_HEADER = """# Local learnings inbox

Raw and unfiltered. **This file is gitignored and never leaves your machine.** Write freely —
name the client, name the subject, paste the prompt that failed. That detail is what makes an
entry worth anything a week later.

Promotion is what strips it. `aar learn --review` hands these entries and the de-projection
rubric to your assistant, which turns the useful ones into general rules and proposes them as
edits to `knowledge/`. See CONTRIBUTING.md.

Capture at the moment it breaks, not at the end of the day. You will not remember why.

---
"""


def inbox_entries():
    if not os.path.exists(INBOX):
        return []
    text = open(INBOX).read()
    out = []
    for block in re.split(r"\n## ", text)[1:]:
        head, _, body = block.partition("\n")
        m = re.match(r"\[(.*?)\]\s+(\w+)\s+·\s+(L\d+)", head.strip())
        if m:
            out.append({"when": m.group(1), "status": m.group(2), "id": m.group(3),
                        "body": body.strip()})
    return out


def cmd_learn(a):
    entries = inbox_entries()

    if a.done:
        if not entries:
            die("nothing in the inbox")
        text = open(INBOX).read()
        hits = 0
        for eid in a.done:
            pat = re.compile(r"(\[.*?\]\s+)pending(\s+·\s+" + re.escape(eid.upper()) + r"\b)")
            text, n = pat.subn(r"\1promoted\2", text)
            hits += n
            print(f"  {eid.upper()}: {'marked promoted' if n else 'not found (or already promoted)'}")
        open(INBOX, "w").write(text)
        return

    pending = [e for e in entries if e["status"] == "pending"]

    if a.list:
        if not pending:
            print("\n  Inbox empty. Nothing pending.\n")
            return
        print(f"\n  {len(pending)} pending\n")
        for e in pending:
            first = e["body"].splitlines()[0] if e["body"] else ""
            print(f"  {e['id']}  {e['when']}  {first[:70]}")
        print()
        return

    if a.review:
        if not pending:
            print("\n  Inbox empty. Nothing to promote.\n")
            return
        print("\n" + "=" * 74)
        print("  PROMOTION BRIEF — for the assistant, not for the terminal")
        print("=" * 74)
        print("""
Below are raw learnings captured during real work. Your job is to turn the ones that
qualify into general rules, and to reject the ones that don't.

Read CONTRIBUTING.md for the full rubric. In short, every entry must pass four tests:

  1. STRANGER TEST   Would this help someone whose subject shares nothing with yours?
                     If the rule only parses with the original subject named, you have an
                     instance, not a rule. Find the mechanism underneath it.
  2. MECHANISM TEST  Can you say WHY it happens? "Model X blocked my crop" is an anecdote.
                     "Moderation tracks a property of the frame, so retries don't help and
                     reframing does" is a rule.
  3. CLASS TEST      Classify it, because the classes have different shelf lives:
                       structural  — a fact about how these models work. Durable.
                       measured    — a number from one subject on one date. Date it, name
                                     the subject, say it may not generalise.
                       capability  — what a named model can do. Rots in DAYS. Needs probe
                                     output (`aar audit --deep`) or it does not go in.
  4. COST TEST       What did not knowing this cost — money, hours, a rejected delivery?
                     An entry that cannot name a price is trivia, and trivia is what makes
                     a rules doc too long to read.

Then:
  - Strip every subject-specific detail. No client names, no project names, no assets.
  - Find the doc it belongs in: knowledge/routing.md, prompting.md, failures.md, qc.md,
    workflow.md, cost.md, or models.json.
  - Prefer AMENDING an existing rule over adding a new one. Two rules that overlap are
    worse than one rule stated well.
  - Propose the edits, show them to the human, and only then commit.
  - Mark each promoted entry: aar learn --done <id>
""")
        print("=" * 74)
        print(f"  {len(pending)} PENDING ENTRIES")
        print("=" * 74 + "\n")
        for e in pending:
            print(f"── {e['id']}  ({e['when']})")
            print(f"{e['body']}\n")
        return

    if not a.note:
        die("say what you learned:  aar learn \"kling blocked the tight crop, wider passed\"\n"
            "    or:  aar learn --list | --review | --done L001")

    if not os.path.exists(INBOX):
        open(INBOX, "w").write(INBOX_HEADER)
    nxt = f"L{len(entries) + 1:03d}"
    stamp = time.strftime("%Y-%m-%d %H:%M")
    body = a.note
    if a.cost:
        body += f"\n\n**Cost:** {a.cost}"
    if a.kind:
        body += f"\n**Class:** {a.kind}"
    with open(INBOX, "a") as f:
        f.write(f"\n## [{stamp}] pending · {nxt}\n\n{body}\n")
    print(f"\n  {nxt} captured → learnings.local.md (gitignored)")
    print("  Promote when you have a few:  aar learn --review\n")


def cmd_image(a):
    k = key("GEMINI_API_KEY", "image generation needs it")
    model = a.model or models_json()["routes"]["image"][0]
    out = a.out or "out.png"
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)

    parts = []
    for ref in (a.ref or []):
        if not os.path.exists(ref):
            die(f"reference not found: {ref}")
        mime = "image/png" if ref.lower().endswith(".png") else "image/jpeg"
        with open(ref, "rb") as f:
            parts.append({"inlineData": {"mimeType": mime,
                                         "data": base64.b64encode(f.read()).decode()}})
    parts.append({"text": a.prompt})

    if a.ref:
        log(f"editing from {len(a.ref)} reference(s) — attach only the references you want "
            f"obeyed (knowledge/prompting.md §13)")
    else:
        log("generating from text alone — fine for a first frame, but every VARIANT should "
            "be an edit of this one, not another text generation")

    body = {"contents": [{"parts": parts}],
            "generationConfig": {"responseModalities": ["TEXT", "IMAGE"],
                                 "imageConfig": {"aspectRatio": a.ratio, "imageSize": a.size}}}
    os.makedirs(STATE, exist_ok=True)
    req = os.path.join(STATE, "gemini_req.json")
    with open(req, "w") as f:
        json.dump(body, f)

    stem, ext = os.path.splitext(out)
    got = 0
    for attempt in range(a.takes * 3):
        if got >= a.takes:
            break
        d = curl(["-H", "Content-Type: application/json", "-H", f"x-goog-api-key: {k}",
                  f"{GEMINI_BASE}/models/{model}:generateContent", "-d", f"@{req}"])
        wrote = False
        for c in d.get("candidates", []):
            for p in c.get("content", {}).get("parts", []):
                blob = p.get("inlineData", {}).get("data")
                if blob:
                    got += 1
                    path = out if a.takes == 1 else f"{stem}_t{got}{ext}"
                    with open(path, "wb") as f:
                        f.write(base64.b64decode(blob))
                    log(f"  ✅ {path}")
                    wrote = True
        if not wrote:
            err = json.dumps(d)[:300]
            log(f"  attempt {attempt + 1} returned no image: {err}")
            if looks_like_moderation(err):
                log("  → reads as a content block. Do not retry unchanged: rephrase in the "
                    "subject's real domain register, or change the framing.")
                break
            time.sleep(4)
    os.path.exists(req) and os.remove(req)
    if got == 0:
        die("no image came back. Three failures on the same input usually means the content "
            "tripped a filter; everything failing means platform load — walk away an hour.")
    if got < a.takes:
        log(f"  ⚠️  only {got}/{a.takes} takes came back")


def cmd_video(a):
    m = models_json()
    pair = bool(a.last)
    if not os.path.exists(a.first):
        die(f"start keyframe not found: {a.first}")
    if pair and not os.path.exists(a.last):
        die(f"end keyframe not found: {a.last}")

    ladder = [a.model] if a.model else m["routes"]["keyframe_pair" if pair else "single_image"]
    if not pair:
        print()
        log("single-image i2v has NO END CONSTRAINT — drift is unbounded and typically shows "
            "up after ~2s.")
        log("If this shot has a defined end state, generate that frame and pass --last "
            "instead. It is the single biggest quality win available here.")
        print()

    images = [{"uri": data_uri(a.first), "position": "first"}]
    if pair:
        images.append({"uri": data_uri(a.last), "position": "last"})
    payload_image = images if pair else data_uri(a.first)

    inputs = [a.first] + ([a.last] if pair else [])
    out = a.out or "out.mp4"
    stem, ext = os.path.splitext(out)
    os.makedirs(os.path.dirname(os.path.abspath(out)) or ".", exist_ok=True)
    tmp = os.path.join(STATE, "tmp")
    os.makedirs(tmp, exist_ok=True)

    bal0 = balance()
    if bal0 is not None:
        log(f"balance {bal0:,} credits")

    known = blocked_load()
    made = []
    for take in range(1, a.takes + 1):
        target = out if a.takes == 1 else f"{stem}_t{take}{ext}"
        log(f"take {take}/{a.takes} → {os.path.basename(target)}")
        task_id, used = None, None

        for model in ladder:
            fp = fingerprint(model, a.prompt, inputs)
            if fp in known:
                log(f"  {model}: SKIPPED — this exact input was blocked here before "
                    f"({known[fp]['count']}x). Change the framing, the prompt, or the vendor.")
                continue

            body = {"model": model, "promptImage": payload_image, "promptText": a.prompt,
                    "duration": a.duration}
            if a.ratio:
                body["ratio"] = a.ratio
            d = runway("POST", "/image_to_video", body)

            if d.get("id"):
                task_id, used = d["id"], model
                log(f"  submitted to {model} → {task_id}")
                break

            err = json.dumps(d)[:300]
            if looks_like_moderation(err):
                n = blocked_record(fp, model, err)
                log(f"  {model}: BLOCKED ({n}x). Trying a different vendor.")
            elif a.ratio and "ratio" in err.lower():
                body.pop("ratio")
                d = runway("POST", "/image_to_video", body)
                if d.get("id"):
                    task_id, used = d["id"], model
                    log(f"  submitted to {model} (ratio dropped — check native max in "
                        f"models.json) → {task_id}")
                    break
                log(f"  {model}: rejected → {json.dumps(d)[:200]}")
            else:
                log(f"  {model}: rejected → {err[:200]}")

        if not task_id:
            log("  ✗ no model accepted this take.")
            log("    Two vendors refusing the same input is a human decision — see "
                "knowledge/routing.md, 'Moderation as a routing problem'.")
            continue

        raw = os.path.join(tmp, f"raw_{take}.mp4")
        ok, why = poll(task_id, raw)
        if not ok:
            if looks_like_moderation(why):
                blocked_record(fingerprint(used, a.prompt, inputs), used, why or "")
                log(f"  ✗ {used} blocked it at generation time. Recorded — will not resubmit "
                    f"unchanged.")
            else:
                log(f"  ✗ {why}")
            continue

        info = probe_media(raw)
        conform(raw, target, a.width, a.height)
        made.append(target)
        note = ""
        if info["width"] and a.ratio:
            want_w = int(a.ratio.split(":")[0])
            if info["width"] != want_w:
                note = f" (returned {info['width']}x{info['height']} — conformed)"
        if info["audio"]:
            note += " (silent audio track stripped)"
        log(f"  ✅ {target}  [{used}]{note}")

        sheet = f"{os.path.splitext(target)[0]}_sheet.jpg"
        if contact_sheet(target, sheet):
            log(f"     contact sheet → {sheet}")

    bal1 = balance()
    if bal0 is not None and bal1 is not None:
        log(f"balance {bal1:,} credits  (spent {bal0 - bal1:,} ≈ ${(bal0 - bal1) / 100:.2f})")

    if made:
        print()
        log("QC before you call this done — a contact sheet is not QC:")
        kf = f" --first {a.first}" + (f" --last {a.last}" if pair else "")
        log(f"  aar qc {made[0]}{kf}")


def cmd_edit(a):
    if not os.path.exists(a.clip):
        die(f"clip not found: {a.clip}")
    model = a.model or models_json()["routes"]["video_edit"][0]
    out = a.out or f"{os.path.splitext(a.clip)[0]}_edit.mp4"

    print()
    log("Video edits obey REMOVE-object and ADD-object well.")
    log("They IGNORE 're-render this region in another style' — that returns a no-op.")
    log("And if the change is IN THE SUBJECT rather than an object in the scene, fixing the "
        "source keyframe and regenerating is cheaper and cleaner (knowledge/routing.md).")
    print()

    with open(a.clip, "rb") as f:
        uri = "data:video/mp4;base64," + base64.b64encode(f.read()).decode()

    bal0 = balance()
    d = runway("POST", "/video_to_video",
               {"model": model, "videoUri": uri, "promptText": a.prompt})
    if not d.get("id"):
        die(f"{model} rejected it → {json.dumps(d)[:300]}")

    tmp = os.path.join(STATE, "tmp")
    os.makedirs(tmp, exist_ok=True)
    raw = os.path.join(tmp, "edit_raw.mp4")
    ok, why = poll(d["id"], raw)
    if not ok:
        die(f"edit failed → {why}")
    conform(raw, out)
    log(f"  ✅ {out}")
    bal1 = balance()
    if bal0 and bal1:
        log(f"spent {bal0 - bal1:,} credits ≈ ${(bal0 - bal1) / 100:.2f}")
    print()
    log("Now diff it against the original. Edits are not surgical — one that removed its "
        "target also stripped an adjacent property the shot depended on:")
    log(f"  aar qc --compare {a.clip} {out}")


def cmd_upscale(a):
    if not os.path.exists(a.clip):
        die(f"clip not found: {a.clip}")
    model = a.model or models_json()["routes"]["upscale"][0]
    out = a.out or f"{os.path.splitext(a.clip)[0]}_2x.mp4"

    print()
    log("This is a CREATIVE upscaler — it invents detail rather than interpolating.")
    log("Safe on CG. It BREAKS live-action with fine moving texture (hair, beard, knitwear) "
        "by inventing that detail differently every frame — a shimmer that reads as stutter "
        "and is invisible in stills.")
    print()

    with open(a.clip, "rb") as f:
        uri = "data:video/mp4;base64," + base64.b64encode(f.read()).decode()
    bal0 = balance()
    d = runway("POST", "/video_upscale", {"model": model, "videoUri": uri})
    if not d.get("id"):
        die(f"{model} rejected it → {json.dumps(d)[:300]}")
    tmp = os.path.join(STATE, "tmp")
    os.makedirs(tmp, exist_ok=True)
    raw = os.path.join(tmp, "up_raw.mp4")
    ok, why = poll(d["id"], raw)
    if not ok:
        die(f"upscale failed → {why}")
    conform(raw, out)
    log(f"  ✅ {out}")
    bal1 = balance()
    if bal0 and bal1:
        log(f"spent {bal0 - bal1:,} credits ≈ ${(bal0 - bal1) / 100:.2f}")
    print()
    log("Never sign off an upscale on stills. Measure temporal irregularity vs the source:")
    log(f"  aar qc --compare {a.clip} {out}")


# ───────────────────────────────────────────────────────────────────── QC ──

def otsu(hist, total):
    """Otsu's method. A naive fraction-of-range threshold gets swallowed by a vignetted
    background — that mistake cost real time, so this is the default here."""
    sum_all = sum(i * hist[i] for i in range(256))
    sum_b = w_b = 0.0
    best, thresh = -1.0, 128
    for t in range(256):
        w_b += hist[t]
        if w_b == 0:
            continue
        w_f = total - w_b
        if w_f == 0:
            break
        sum_b += t * hist[t]
        m_b = sum_b / w_b
        m_f = (sum_all - sum_b) / w_f
        var = w_b * w_f * (m_b - m_f) ** 2
        if var > best:
            best, thresh = var, t
    return thresh


def frame_stats(buf, w, h):
    """Foreground bbox + centroid, via an Otsu threshold on the frame."""
    hist = [0] * 256
    for b in buf:
        hist[b] += 1
    t = otsu(hist, len(buf))
    xs, ys, n, sx, sy = w, h, 0, 0, 0
    x2 = y2 = 0
    for y in range(h):
        row = y * w
        for x in range(w):
            if buf[row + x] > t:
                n += 1
                sx += x
                sy += y
                if x < xs: xs = x
                if x > x2: x2 = x
                if y < ys: ys = y
                if y > y2: y2 = y
    if n == 0:
        return None
    return {"cx": sx / n, "cy": sy / n, "area": n,
            "bw": max(0, x2 - xs), "bh": max(0, y2 - ys)}


def mad(a, b):
    """Mean absolute difference between two equal-length byte buffers, 0..255."""
    return sum(abs(a[i] - b[i]) for i in range(len(a))) / len(a)


def resize_to(path, w, h, dst):
    subprocess.run([ff(), "-y", "-v", "error", "-i", path, "-vf", f"scale={w}:{h}",
                    "-f", "rawvideo", "-pix_fmt", "gray", dst], capture_output=True)
    with open(dst, "rb") as f:
        return f.read()[:w * h]


def cmd_qc(a):
    if a.compare:
        return qc_compare(a.compare[0], a.compare[1])
    clip = a.clip
    if not clip or not os.path.exists(clip):
        die("give me a clip: aar qc clip.mp4")

    info = probe_media(clip)
    W, H = 160, 90
    frames = gray_frames(clip, W, H)
    if len(frames) < 3:
        die("could not read frames — is this a video?")

    print()
    print(f"  QC — {os.path.basename(clip)}")
    print("  " + "─" * 58)
    print(f"  {info['width']}x{info['height']} · {info['fps']} fps · "
          f"{info['duration']:.2f}s · {len(frames)} frames")
    flags = []

    if info["audio"]:
        print("  audio            PRESENT")
        flags.append("strip the audio track before delivery — several models attach a silent one")
    if info["width"] and info["width"] % 2:
        flags.append("odd frame width — will break some encoders")

    # ── jitter: mean absolute delta between consecutive frames
    deltas = [mad(frames[i], frames[i - 1]) for i in range(1, len(frames))]
    jitter = sum(deltas) / len(deltas) / 255.0

    # ── reversal: distance-from-first should climb monotonically in a one-direction move
    d0 = [mad(f, frames[0]) for f in frames]
    k = max(2, len(d0) // 20)
    sm = [sum(d0[max(0, i - k):i + k + 1]) / len(d0[max(0, i - k):i + k + 1])
          for i in range(len(d0))]
    span = max(sm) - min(sm)

    print(f"  jitter           {jitter:.4f}   (mean |Δ| between consecutive frames, 0–1)")
    # A small object moving across a dark frame produces low jitter without being still, so
    # the near-still call needs the total departure from frame 0 to be small as well.
    if jitter < 0.004 and span / 255.0 < 0.010:
        print("                   → reads as a near-still plate")
    elif jitter > 0.10:
        flags.append(f"high frame-to-frame irregularity ({jitter:.3f}) — check for stutter at "
                     f"full speed, not in stills")

    rev, direction = 0, 0
    last_ext = sm[0]
    for v in sm:
        if span > 0 and abs(v - last_ext) > 0.12 * span:
            nd = 1 if v > last_ext else -1
            if direction and nd != direction:
                rev += 1
            direction = nd
            last_ext = v
    print(f"  direction changes {rev}")
    if rev >= 2:
        flags.append(f"{rev} direction reversals — the motion goes back the way it came. This "
                     f"is what 'fill 5s with a 1s action' looks like, and a contact sheet "
                     f"cannot show it. See knowledge/prompting.md §4")

    # ── travel / scale drift
    s0, s1 = frame_stats(frames[0], W, H), frame_stats(frames[-1], W, H)
    if s0 and s1:
        travel = ((s1["cx"] - s0["cx"]) ** 2 + (s1["cy"] - s0["cy"]) ** 2) ** 0.5
        travel_pct = travel / W * 100
        scale = (s1["area"] / s0["area"]) if s0["area"] else 1.0
        print(f"  subject travel   {travel_pct:.1f}% of frame width")
        print(f"  subject scale    {scale:.2f}x  (first → last)")
        if travel_pct > 6:
            flags.append(f"subject moved {travel_pct:.1f}% across frame — if this was meant to "
                         f"be a locked plate, it isn't one")
        if scale < 0.9 or scale > 1.1:
            flags.append(f"subject changed size by {abs(1 - scale) * 100:.0f}% — check for an "
                         f"unrequested zoom, or re-staging")

    # ── colour temperature drift
    rgb = rgb_frames(clip, 64, 36)
    if len(rgb) > 2:
        def warmth(buf):
            r = sum(buf[0::3]) / (len(buf) / 3)
            b = sum(buf[2::3]) / (len(buf) / 3)
            return r - b
        w0, w1 = warmth(rgb[0]), warmth(rgb[-1])
        drift = w1 - w0
        print(f"  warmth drift     {drift:+.1f}   (mean R−B, first → last)")
        if abs(drift) > 6:
            flags.append(f"colour temperature drifted {drift:+.1f} across the take — invisible "
                         f"in a 3-frame check, obvious here")

    # ── keyframe adherence
    # A raw mean-difference score is dominated by how much of the frame is content — a small
    # subject on a dark background scores low even when it is in completely the wrong place.
    # So the score is read against the clip's OWN total change, first frame to last: a
    # mismatch comparable to the whole shot's motion means the endpoint was not honoured.
    motion = mad(frames[0], frames[-1]) / 255.0
    tmp = os.path.join(STATE, "tmp")
    os.makedirs(tmp, exist_ok=True)
    for label, kf, want_last in (("start", a.first, False), ("end", a.last, True)):
        if not kf:
            continue
        if not os.path.exists(kf):
            print(f"  {label} keyframe   not found: {kf}")
            continue
        vf = extract_frame(clip, os.path.join(tmp, f"{label}.png"), last=want_last)
        if not vf:
            continue
        kb = resize_to(kf, W, H, os.path.join(tmp, f"{label}_k.raw"))
        vb = resize_to(vf, W, H, os.path.join(tmp, f"{label}_v.raw"))
        if len(kb) == len(vb) == W * H:
            score = mad(kb, vb) / 255.0
            rel = (score / motion) if motion > 0.01 else None
            rel_txt = f" · {rel:.2f}x the clip's own motion" if rel is not None else ""
            print(f"  {(label + ' adherence'):<16} {score:.3f}{rel_txt}"
                  f"   (0 = identical to your keyframe)")
            missed = (rel > 0.35) if rel is not None else (score > 0.14)
            if missed:
                flags.append(f"{label} frame is a long way from the keyframe you supplied "
                             f"({score:.3f}) — the model did not honour that end")

    if a.sheet:
        dst = f"{os.path.splitext(clip)[0]}_sheet.jpg"
        if contact_sheet(clip, dst):
            print(f"  contact sheet    {dst}")

    print()
    if flags:
        print("  FLAGS")
        for f in flags:
            print(f"    ⚠  {f}")
    else:
        print("  No automatic flags.")
    print()
    print("  These metrics tell you WHERE TO LOOK. They do not tell you the shot is good.")
    print("  Open the file. Every frame. Nothing here replaces that — knowledge/qc.md rule 0.")
    print()


def qc_compare(src, out):
    """Per-region temporal irregularity, processed vs source. This is the check that catches
    a creative upscaler doubling the stutter on a face while every still looks better."""
    for p in (src, out):
        if not os.path.exists(p):
            die(f"not found: {p}")
    W, H, GX, GY = 160, 90, 4, 4
    a, b = gray_frames(src, W, H), gray_frames(out, W, H)
    n = min(len(a), len(b))
    if n < 3:
        die("could not read enough frames from both clips")

    def cell_jitter(frames):
        cw, ch = W // GX, H // GY
        res = []
        for gy in range(GY):
            for gx in range(GX):
                tot = 0.0
                for i in range(1, n):
                    s = 0
                    for y in range(gy * ch, (gy + 1) * ch):
                        row = y * W
                        for x in range(gx * cw, (gx + 1) * cw):
                            s += abs(frames[i][row + x] - frames[i - 1][row + x])
                    tot += s / (cw * ch)
                res.append(tot / (n - 1) / 255.0)
        return res

    ja, jb = cell_jitter(a), cell_jitter(b)
    print()
    print(f"  Temporal irregularity — {os.path.basename(out)} vs {os.path.basename(src)}")
    print("  " + "─" * 58)
    print("  Ratio per region (>1 = the processed clip is less stable than the source)\n")
    worst = 0.0
    for gy in range(GY):
        row = []
        for gx in range(GX):
            i = gy * GX + gx
            if ja[i] > 1e-6:
                r = jb[i] / ja[i]
            elif jb[i] > 1e-4:
                # Source region was perfectly stable and the processed one is not. This is
                # the most damning case, not a divide-by-zero to shrug at.
                r = float("inf")
            else:
                r = 1.0
            worst = max(worst, r)
            row.append("  new " if r == float("inf") else f"{r:5.2f}")
        print("    " + "  ".join(row))
    print(f"\n  worst region  " +
          ("instability where the source had none" if worst == float("inf")
           else f"{worst:.2f}x"))
    if worst > 1.5:
        print("\n  ⚠  This pass has meaningfully increased frame-to-frame irregularity in at "
              "least one\n     region. On live-action faces or fine texture that reads as "
              "stutter and it is\n     invisible in stills. Two upscales shipped this way and "
              "were rejected on playback.")
    else:
        print("\n  No region got meaningfully less stable. Still watch it at full speed.")
    print()


# ─────────────────────────────────────────────────────────────────── parser ──

def main():
    load_env()
    p = argparse.ArgumentParser(prog="aar", description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd")

    sub.add_parser("doctor", help="check keys, balance and ffmpeg").set_defaults(fn=cmd_doctor)

    m = sub.add_parser("models", help="routing table")
    m.add_argument("job", nargs="?", help="keyframe_pair | single_image | locked_plate | "
                                          "video_edit | upscale | image")
    m.set_defaults(fn=cmd_models)

    pr = sub.add_parser("probe", help="re-derive the live model list from validation errors")
    pr.add_argument("endpoint", nargs="?", default="image_to_video")
    pr.add_argument("--model")
    pr.add_argument("--audit", action="store_true", help="alias for `aar audit`")
    pr.add_argument("--deep", action="store_true")
    pr.set_defaults(fn=lambda a: cmd_audit(a) if a.audit else cmd_probe(a))

    au = sub.add_parser("audit", help="diff the live API against models.json — is the table "
                                      "still true?")
    au.add_argument("--deep", action="store_true",
                    help="also re-check keyframe-pair support. Creates tasks on models that "
                         "validate lazily; each is cancelled immediately.")
    au.set_defaults(fn=cmd_audit)

    ln = sub.add_parser("learn", help="capture a learning locally; promote it later")
    ln.add_argument("note", nargs="?", help="what you learned, in plain language")
    ln.add_argument("--cost", help="what not knowing it cost (credits, hours, a redo)")
    ln.add_argument("--kind", choices=["structural", "measured", "capability"],
                    help="claim class — leave blank and let the review step decide")
    ln.add_argument("--list", action="store_true", help="show pending entries")
    ln.add_argument("--review", action="store_true",
                    help="print the pending entries plus the de-projection rubric, for your "
                         "assistant to turn into proposed edits")
    ln.add_argument("--done", nargs="+", metavar="ID", help="mark entries promoted")
    ln.set_defaults(fn=cmd_learn)

    im = sub.add_parser("image", help="generate or edit a still")
    im.add_argument("prompt")
    im.add_argument("-o", "--out")
    im.add_argument("--ref", action="append", help="parent image to edit from (repeatable)")
    im.add_argument("--ratio", default="16:9")
    im.add_argument("--size", default="2K")
    im.add_argument("--takes", type=int, default=1)
    im.add_argument("--model")
    im.set_defaults(fn=cmd_image)

    vi = sub.add_parser("video", help="generate motion from one or two keyframes")
    vi.add_argument("prompt")
    vi.add_argument("--first", required=True, help="start keyframe")
    vi.add_argument("--last", help="end keyframe — use this whenever the shot has an end state")
    vi.add_argument("-o", "--out")
    vi.add_argument("--duration", type=int, default=5)
    vi.add_argument("--ratio", default="1920:1080")
    vi.add_argument("--takes", type=int, default=2)
    vi.add_argument("--width", type=int)
    vi.add_argument("--height", type=int)
    vi.add_argument("--model")
    vi.set_defaults(fn=cmd_video)

    ed = sub.add_parser("edit", help="change one thing in a clip you already like")
    ed.add_argument("clip")
    ed.add_argument("prompt")
    ed.add_argument("-o", "--out")
    ed.add_argument("--model")
    ed.set_defaults(fn=cmd_edit)

    up = sub.add_parser("upscale", help="2x upscale")
    up.add_argument("clip")
    up.add_argument("-o", "--out")
    up.add_argument("--model")
    up.set_defaults(fn=cmd_upscale)

    qc = sub.add_parser("qc", help="scan a clip for the failures that actually happen")
    qc.add_argument("clip", nargs="?")
    qc.add_argument("--first", help="start keyframe, to check adherence")
    qc.add_argument("--last", help="end keyframe, to check adherence")
    qc.add_argument("--sheet", action="store_true", help="also write a contact sheet")
    qc.add_argument("--compare", nargs=2, metavar=("SOURCE", "PROCESSED"),
                    help="temporal irregularity of PROCESSED against SOURCE")
    qc.set_defaults(fn=cmd_qc)

    a = p.parse_args()
    if not getattr(a, "fn", None):
        p.print_help()
        raise SystemExit(0)
    a.fn(a)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n  interrupted\n")
        raise SystemExit(130)
