# Contributing

The most valuable thing you can add here is **a rule you paid for.** Not a tip, not a
preference — something that cost you money, hours, or a rejected delivery, stated so the next
person doesn't pay it again.

The second most valuable thing is **a correction.** This repo's core content is claims about
model behaviour, and model behaviour rots. Between 2026-08-15 and 2026-08-17, on the same API,
one documented model was removed and another gained a capability it demonstrably lacked. If a
row here is wrong, saying so is a real contribution.

---

## You almost certainly don't have to do anything

Contribution is your assistant's job, not yours. [`AGENTS.md`](AGENTS.md) instructs it to
capture learnings as they happen and to promote the ones that generalise before it commits.
Nobody has to remember a command.

What that looks like in practice:

1. You work. Something surprises you, or a shot fails oddly, or **you correct your assistant
   about how something works.**
2. Your assistant writes it to `learnings.local.md` — private, gitignored, stays on your
   machine with the client detail intact. You don't see this happen and don't need to.
3. Next time it commits, it checks that file, works out which entries would help a stranger,
   strips the project-specific detail, and adds them to [`FIELD-NOTES.md`](FIELD-NOTES.md).
4. It shows you the diff. You glance at it and commit.

**Your entire job is step 4.**

### Getting it back to the repo

**One file, always.** A contribution is an addition to `FIELD-NOTES.md`. Nothing else. That
makes it a small, additive diff that takes seconds to review — which is the point.

| If you… | Do this |
|---|---|
| Don't use git | Send the field-note text to the maintainer. Slack, email, whatever. Done. |
| Are comfortable on GitHub | Open `FIELD-NOTES.md` in the browser, pencil icon, paste, submit |
| Work in a terminal | Let your assistant open the pull request |

### Why there are two files

`learnings.local.md` is raw and private — it names the client, the subject, the exact prompt.
That detail is what makes an entry worth anything a week later, and it is exactly what must
never reach a public repo. `FIELD-NOTES.md` is the cleaned-up, general version.

**The raw file is private; the promotion is public.** Nothing crosses that line without a human
seeing the diff.

If you'd rather write an entry by hand, `aar learn "..."` does it. It's a convenience, not the
mechanism.

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

**Contributions go in [`FIELD-NOTES.md`](FIELD-NOTES.md). That's it — one file.**

Everything else is maintainer-edited, so a pull request is always a small addition to a single
file. That is deliberate: a diff you can review in ten seconds is a diff that actually gets
reviewed.

| File | Who edits it |
|---|---|
| `FIELD-NOTES.md` | **Anyone.** New observations, appended at the top |
| `knowledge/*.md` | Maintainer, when a field note is confirmed and graduates |
| `models.json` | Maintainer, from `aar audit` output |

Keep the house style: short, direct, and every rule followed by the failure it prevents. No
hedging where a thing is known; visible hedging where it isn't. And **state the rule, not the
anecdote** — the anecdote is evidence, one clause of it, subject stripped.

### What the maintainer does with it

A field note arrives as `unconfirmed`. It stays in `FIELD-NOTES.md` until either a second
person hits the same thing or the maintainer verifies it — then it moves into the relevant
`knowledge/` doc and comes out of field notes. Nothing is lost in between; it's just marked
honestly as one person's observation until it's more than that.

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
