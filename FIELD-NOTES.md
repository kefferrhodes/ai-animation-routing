# Field notes

**Observations from the field. Lower confidence than [`knowledge/`](knowledge/) — read that first.**

This is where new learnings land. Entries are added by whoever's assistant noticed something
while doing real work, with the project-specific detail stripped out. They are **not** doctrine.
An entry here means *someone saw this once and thought it would help you*.

When an observation is confirmed — seen independently by someone else, or by the maintainer —
it graduates into the relevant `knowledge/` doc and comes out of this file. That's the whole
lifecycle:

```
something surprises you  →  learnings.local.md (private)  →  FIELD-NOTES.md (here)  →  knowledge/ (doctrine)
        automatic                    automatic                   1 PR, 1 file             maintainer folds it in
```

**This is the only file a contribution needs to touch.** New entries go at the top, under the
divider. Append; don't rewrite anyone else's.

---

## Entry format

Copy this shape exactly. It keeps the file skimmable and makes the maintainer's job a
five-second read per entry.

```markdown
### One-line statement of the rule, not the anecdote
**Class:** structural | measured | capability · **Added:** YYYY-MM-DD · **Status:** unconfirmed
**Cost:** what not knowing it cost — money, hours, a redo

Two or three sentences. What happens, why it happens, and what to do instead. No client names,
no project names, no subject that only makes sense in one job.
```

**Class** decides shelf life, so it's mandatory:

| Class | Means | Ages |
|---|---|---|
| `structural` | A fact about how these models work in general | Slowly |
| `measured` | A number from one subject on one date — say which | Quietly, so date it |
| `capability` | What one named model can do. **Needs `aar audit --deep` output** | In days |

**Status** is `unconfirmed` on arrival. The maintainer changes it to `confirmed` when a second
person sees the same thing, and that's the cue to promote it into `knowledge/`.

---

<!-- NEW ENTRIES GO DIRECTLY BELOW THIS LINE -->

### Nothing here yet

The first real entry replaces this one. If you're the assistant reading this: the format above
is the whole spec, and [`CONTRIBUTING.md`](CONTRIBUTING.md) has the four tests an entry must
pass before you add it.
