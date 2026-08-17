# Contributing

The most valuable thing you can add here is **a rule you paid for.** Not a tip, not a
preference — something that cost you money, hours, or a rejected delivery, stated so the next
person doesn't pay it again.

The second most valuable thing is **a correction.** This repo's core content is claims about
model behaviour, and model behaviour rots. Between 2026-08-15 and 2026-08-17, on the same API,
one documented model was removed and another gained a capability it demonstrably lacked. If a
row here is wrong, saying so is a real contribution.

---

## The loop

```bash
aar learn "the tight crop was blocked 6 times; widening it cleared on the first try" \
  --cost "~2h and 6 wasted submissions"
```

That lands in `learnings.local.md`, which is **gitignored and never leaves your machine.**
Write freely in it — name the client, name the subject, paste the prompt that failed. That
detail is what makes an entry worth anything a week later, and it is exactly the detail that
must never reach a public repo.

Capture at the moment it breaks, not at the end of the day. You will not remember why.

When you have a few:

```bash
aar learn --review
```

That prints your pending entries alongside the rubric below, for your assistant to work
through. It proposes edits to `knowledge/`; you approve them; then:

```bash
aar learn --done L001 L002
git checkout -b learning/moderation-framing
# commit the knowledge/ edits — never learnings.local.md
gh pr create
```

**The inbox is private. The promotion is public.** Nothing crosses that line without a human
looking at it.

---

## The rubric — four tests every entry must pass

### 1. The stranger test

> Would this help someone whose subject shares nothing with yours?

If the rule only parses when the original subject is named, you have an *instance*, not a rule.
Find the mechanism underneath it.

| Instance | Rule |
|---|---|
| "Kling blocked my anatomical figure's torso crop" | "Moderation classifiers react to properties of the frame, so blocks that correlate with framing don't respond to retries — reframe or change vendor" |
| "The golfer stood up out of his posture after 2s" | "Single-image i2v has no end constraint; drift is unbounded and shows as the subject relaxing out of a held state" |
| "The upscale ruined the presenter's beard" | "Creative upscalers invent detail per-frame; on fine moving texture that becomes stutter, and it's invisible in stills" |

The right-hand column is what goes in. The left-hand column can appear as *evidence* — one
clause, subject stripped — but never as the rule itself.

### 2. The mechanism test

> Can you say **why** it happens?

"Model X blocked my crop" is an anecdote. "The classifier reacts to how much of the frame the
subject's bare skin occupies" is a mechanism, and a mechanism transfers to subjects nobody has
generated yet.

If you can't explain why, say so explicitly and file it as a *measurement* (below) rather than
dressing it up as a rule. An honest "we observed this and don't know why" is useful. A confident
false mechanism is worse than nothing.

### 3. The class test

Three kinds of claim, three shelf lives, three evidence bars. **Label every entry.**

| Class | What it is | Shelf life | Evidence required |
|---|---|---|---|
| **Structural** | A fact about how these models work — not about a named model | Durable | Explain the mechanism. Ideally two independent observations. |
| **Measured** | A number from one subject on one date | Decays quietly | Date it, name the subject type, state that it may not generalise |
| **Capability** | What a specific named model can do | **Rots in days** | `aar audit --deep` output, or it does not go in |

This is the test that keeps the repo honest. The most common way a doc like this goes bad is a
*measurement* hardening into a *law* — someone writes "model X is the best for locked plates",
the number behind it was from one subject in one week, and a year later people are routing on
folklore. Class labels stop that.

Capability claims are the most dangerous because they're the most confidently stated and the
fastest to expire. **Run the audit before you write one:**

```bash
aar audit --deep
```

### 4. The cost test

> What did not knowing this cost?

Money, hours, a redo, a rejected delivery. Name it. The whole pitch of this repo is "failure
modes we already paid for" — an entry that can't name a price is trivia, and trivia is what
makes a rules document too long for anyone to read.

If it cost nothing, it's probably a preference. Preferences don't go in.

---

## Where things go

| Doc | Takes |
|---|---|
| `knowledge/routing.md` | Which model for which job, and the reasoning |
| `knowledge/prompting.md` | Prompt rules — one rule, one failure it prevents |
| `knowledge/failures.md` | Symptom → cause → fix, indexed by what you're looking at |
| `knowledge/qc.md` | What a pass requires before you call a shot done |
| `knowledge/workflow.md` | The shot lifecycle and working practices |
| `knowledge/cost.md` | Prices, budgeting, where money actually goes |
| `models.json` | Anything model-specific and machine-readable |

**Prefer amending an existing rule over adding a new one.** Two rules that overlap are worse
than one rule stated well — the reader has to reconcile them, and the reconciliation is where
they stop reading. If your finding sharpens an existing rule, sharpen it in place.

Keep the house style: short, direct, and every rule followed by the failure it prevents. No
hedging where a thing is known; visible hedging where it isn't.

---

## Corrections

If a row is wrong, that's a PR, and a welcome one. Include:

- what the doc says
- what's actually true now
- **how you verified it** — `aar audit` output is ideal
- the date

Corrections don't need to pass the cost test. Being wrong is cost enough.

If two contributions conflict:

- **Structural claims** are resolved on mechanism. Whichever explanation predicts more
  observations wins.
- **Measured claims** coexist. Two numbers from two subjects are two data points, not a
  contradiction — publish both with their dates and subjects.
- **Capability claims** are resolved by probe. Run the audit; the API is the referee.

---

## What does not go in

- Client names, project names, brand names, asset paths, anything under NDA
- Credentials, `.env` files, keys of any kind — even revoked ones
- Generated media. This repo ships knowledge, not footage
- `learnings.local.md`. It's gitignored; keep it that way
- Prompts that only make sense with your subject in them
- Vendor benchmarks or rankings. These are field notes, not a leaderboard, and a leaderboard
  would be stale in a fortnight anyway

---

## Running the checks

```bash
aar audit          # is models.json still true? free, creates no tasks
aar audit --deep   # also re-checks keyframe-pair support
```

`--deep` creates tasks on models that validate lazily. Each one is cancelled immediately and
cancelling straight away has been observed to cost nothing — but be aware it's happening, and
never leave a probe task running.

`aar audit` exits non-zero when the table has drifted, so you can wire it into whatever you
like locally. There's deliberately no scheduled CI for it: that would mean an API key living in
repo settings, and this repo isn't worth a stored credential.
