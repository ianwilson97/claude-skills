---
name: learning-exercise
description: >-
  Generates one small, atomic, runnable exercise that forces the user to APPLY a
  technical concept they just learned, then grades their attempt. Scaffolds a
  spec, stub files with TODOs, failing assert-based tests, and a one-command
  runner into ~/learning-mode/exercises/. Use this whenever the user wants to
  practice, drill, or prove they actually understood something: "give me an
  exercise", "let me practice X", "make me a problem", "I want to try this
  myself", "test if I really get it", "something to build with this", "a project
  to apply X", "make me do it", "homework", "a kata". Also use right after a
  learning-mode session when they ask "what now" / "how do I make this stick",
  and when they name a past topic to be drilled on ("give me a const-correctness
  problem"). Second mode: use when they come back with "check my exercise",
  "I finished it", "review my solution", "did I get it right", "grade this" —
  runs their tests and grades against the target concept. Do NOT use to TEACH a
  new topic (that is `learning-mode`) or to quiz from memory with no code
  written (that is `learning-review`).
---

# Learning Exercise

Reading an explanation produces recognition. Writing code that runs produces
knowledge. This skill closes that gap: it hands the user **one concrete thing to
build**, small enough to finish in a sitting, narrow enough that the only way to
finish it is to actually understand the target concept.

Two modes, chosen by what the user says:

- **Generate** — build the exercise (default).
- **Check** — they've attempted it; run it, review it, grade it.

## The atomicity contract — the thing that makes this skill work

An exercise that quietly requires three other concepts isn't a test of the
target, it's a test of everything else. The user gets stuck on a build system, a
library API, an unfamiliar idiom — and learns nothing about the thing they came
to practice. Frustration reads as "I don't understand pointers" when the real
problem was CMake.

So the gate, and it is checkable rather than vibes:

> **Every construct the exercise requires is either (a) the target concept, or
> (b) something the user has demonstrably already used.**

You establish (b) by reading the archive — see "Source the topic" below. When
you catch yourself needing something that fails the gate, don't teach it in the
spec and don't hope they'll figure it out. **Pre-write it into the scaffold** as
working, given code they don't touch, and say so in a comment: `// given — not
part of the exercise`. Their attention should be entirely on the slots you left
empty.

Given code must be **live and compiling** — never commented out with an
"uncomment this once you…" note. That's a solution wearing a disguise, and it
re-opens the copy-paste path the whole scaffold exists to close.

Corollaries that follow from the same principle:

- **No frameworks, no build systems, no dependencies.** `assert` and the
  standard library. One compile command, or one interpreter invocation. If the
  exercise needs a package manager, you've already lost.
- **One or two files.** A directory tree is a project-structure exercise.
- **30–60 minutes of real work.** Long enough to force a design decision, short
  enough to finish in one sitting. Something abandoned half-done teaches less
  than something small and finished.
- **Boring domain.** The scenario is scaffolding for the concept, not the point.
  A cache, a counter, a queue of orders. Don't invent an elaborate world; every
  sentence of story is a sentence not spent on the concept.

## Source the topic

1. **Read the archive index**: `ls ~/learning-mode/*.html` and
   `~/learning-mode/.exercises.log` (may not exist yet). Filenames are
   `YYYY-MM-DD-topic-slug.html`, so topics and dates need no parsing.
2. **Pick the target:**
   - If the user named a topic, that one wins.
   - Otherwise, the most recent artifact with no `generated` line in
     `.exercises.log` — freshly-taught material is where application pays best.
3. **Read that artifact.** Its **"Three things to remember"** and **"Gotchas"**
   sections are your specification. The exercise must be un-completable without
   at least one takeaway, and it should walk the user straight into one gotcha
   so they hit it themselves — a trap you survive is worth ten you were warned
   about.
4. **The rest of the archive is your prior-knowledge ledger.** Those filenames
   tell you what's fair game as "already familiar" under the atomicity contract.
   Newer than a week and only taught once? Treat it as shaky, not known.
5. **No matching artifact** (topic never studied): you have no ledger to check
   the atomicity gate against — but don't reach for the user yet. Their machine
   usually knows: a `rustlings`/exercism state file, repos already written in
   that language, a package manifest, whether the toolchain is even installed.
   Sweep that first. It costs seconds, and it beats self-report — people
   systematically misjudge what they've actually typed versus read.

   Then say in one line what you found and what you're assuming from it, and
   design. Ask the user only when the disk is genuinely silent, and then **one
   question** — the one whose answer most changes the exercise. A stated
   assumption is cheap for them to correct; an intake questionnaire is a wall
   between them and the thing they asked for.

Before you write anything, **state the target in one sentence and get a nod**:
"Exercise on `const` member functions — you'll write a class where the compiler
rejects your first attempt. ~40 min. Go?" This is cheap and catches a
mis-targeted exercise before you've generated four files.

## Generate the exercise

Write to `~/learning-mode/exercises/YYYY-MM-DD-topic-slug/` — real date from
`date +%F`, slug matching the source artifact so the two are greppable together.

```
~/learning-mode/exercises/2026-08-03-const-correctness/
  SPEC.md      # the task, constraints, done-criteria
  main.cpp     # stubs with TODOs + given code
  test.cpp     # asserts that fail today
  run.sh       # one command: build + run tests
```

Adapt names to the language (`main.py` / `test.py`, `run.sh` still the entry
point). Keep `run.sh` executable and literal — a two-line `set -e` script, not a
Makefile.

### SPEC.md

```markdown
# {Exercise title}

**Target concept:** {one line — what this is testing}
**From:** {source artifact filename}
**Time:** ~{N} minutes

## The task
{2–4 sentences. What to build, in terms of observable behavior. Written as a
requirement, not as an implementation plan — no "first create a class that…".}

## Constraints
{The rules that force the concept. "You may not copy the object." "The method
must be callable on a const reference." These are the exercise; without them
there's a lazy way through that skips the learning.}

## You already have
{What's pre-written in the scaffold and why it isn't your problem.}

## Done when
```
./run.sh
```
{prints exactly / exits 0 / all asserts pass}. The tests fail right now — that's
the starting line.

## Stuck?
{ONE nudge, phrased as a question aimed at the crux — not a hint at the answer.
"What does the compiler know about `this` inside a const method?"}
```

### The scaffold

Three rules, all guarding the same thing — **the user must produce the idea, not
transcribe it**:

1. **Stubs mark the slot, never fill it.** A signature, a doc comment saying
   what it must do, and `// TODO`. If a stub body would give away the shape,
   delete the body entirely. Never leave a commented-out solution.
2. **Tests assert observable behavior only.** Call the public surface, check the
   result. A test that calls the private helper the user was supposed to invent
   has just told them to invent it. Write tests against the spec, as if by
   someone who hasn't seen a solution.
3. **Tests must fail on a fresh checkout, and fail legibly.** Run `./run.sh`
   yourself before handing it over. A compile error is a fine failure for a
   compile-time concept; a segfault is not — assert with a message that names
   what was expected. If it accidentally passes empty, the exercise is broken.

Bare `assert` from the standard library is the whole harness. No test framework,
no runner, no fixtures.

### Hand it off

Tell them the path, the one command to run, and stop. Don't preview the
solution, don't add "you'll probably want to…", don't walk the spec aloud —
they can read. Then append to `~/learning-mode/.exercises.log`:

```
2026-08-03 const-correctness generated
```

## Check mode

They're back with an attempt. The job is narrow: did they get **the target
concept**? Not: is this production code.

1. **Run `./run.sh`.** Report pass/fail plainly with the actual output. Never
   claim it passes without having run it.
2. **Read their code against the target only.** Praise or criticize what bears
   on the concept. Style nits, naming, and unrelated inefficiencies are noise
   here and they dilute the one signal that matters — leave them alone unless
   asked. The single exception is a construct that's *accidentally* correct: if
   the tests pass but the reasoning is wrong, that's the most valuable finding
   in the whole review and it must be named.
3. **If tests fail, don't fix it for them.** Point at the failing assert and ask
   the question that isolates the gap. Escalate only as far as their stuck-ness
   requires: name the concept, then the specific line, then one line of code —
   in that order, across turns, not all at once.
4. **Grade once solved**: `fail` (couldn't get there) | `partial` (works, but
   the concept was worked around rather than used) | `pass` (works, and for the
   right reason). Append it:

   ```
   2026-08-03 const-correctness pass
   ```

5. **One line on what's next.** A `pass` feeds `learning-review` — say when
   they'll be quizzed on it. A `fail` or `partial` on a genuine misunderstanding
   is a signal to re-teach: suggest a `learning-mode` session on the specific
   sub-concept that broke, not a re-read of the artifact.

## Tone

They asked to be made to work. Don't apologize for the difficulty, don't
over-scaffold out of kindness, and don't soften a failing grade — a drill that
can't be failed measures nothing. But keep the target narrow and the scaffold
generous: every minute spent fighting something *other* than the concept is a
minute stolen from the exercise.
