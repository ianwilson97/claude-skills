---
name: learning-review
description: >-
  Spaced-recall review of past learning-mode sessions. Picks a due artifact from
  ~/learning-mode/, quizzes the user closed-book on what they retained, grades
  the gap, and schedules the next review. Use when the user says "learning
  review", "quiz me", "review what I've learned", "test my recall", "what have I
  forgotten", "am I retaining this", or asks to revisit a past topic they
  studied. Also use when they name a specific past topic to be re-tested on
  ("quiz me on smart pointers"). Do NOT use to teach a new topic — that is
  `learning-mode`.
---

# Learning Review

The learning archive at `~/learning-mode/` is write-only by default: sessions
accumulate, nothing pulls them back. That makes it external memory substituting
for internal memory, which is the exact failure the archive was meant to
prevent. This skill closes the loop.

**The whole point is the retrieval attempt, not the reading.** Re-reading an
artifact feels productive and does almost nothing — it produces recognition
("right, I knew that"), which is not recall. The value is entirely in the user
trying to reproduce the content from an empty head *first*, being partly wrong,
and then seeing the gap. Protect that: **the user must not see the artifact
until after they have answered.**

## Pick what to review

1. **List the archive**: `ls ~/learning-mode/*.html`. Filenames are
   `YYYY-MM-DD-topic-slug.html` — date and topic are right there, no parsing
   needed.
2. **Read the review log** if it exists: `~/learning-mode/.reviews.log`, one
   line per past review:
   ```
   2026-07-31 cpp17-memory-management good
   ```
   (date reviewed, slug, grade of `miss` | `partial` | `good`)
3. **Choose the most-due item.** Next-review interval is set by the last grade:

   | Last grade | Review again after |
   |---|---|
   | never reviewed | 3 days after the session date |
   | `miss` | 2 days |
   | `partial` | 7 days |
   | `good` | 21 days |

   Pick the item that is most overdue. Ties go to the older session date.
   If the user named a topic, use that one instead and ignore scheduling.
4. **Nothing due?** Say so in one line and offer the most-overdue-anyway item
   or the oldest never-reviewed one. Don't manufacture a session.

Review **one** artifact per invocation. Two is a study marathon nobody
finishes.

## Run the review

**Read the artifact yourself. Do not show it, quote it, paste it, or summarize
it to the user.** You are holding the answer key.

Then, in one message:

- Name the topic and when they studied it ("Smart pointers — you did this 8
  days ago").
- Ask them to recall, cold: **the three takeaways**, and **one gotcha**. Those
  map to the artifact's "Three things to remember" and "Gotchas" sections.
- Add **one applied question** drawn from the artifact — not a definition, a
  judgment call. "Which pointer type would you reach for here, and why?" A
  concept you can define but can't apply wasn't learned.
- Say plainly that partial and wrong answers are the useful ones, and that
  "gone, no memory of it" is a legitimate and informative answer.

**Then stop and wait.** Do not include hints, do not include the answers
collapsed below, do not soften it with a recap of the topic. Anything visible
gets read, and the retrieval never happens.

## Grade the gap

When they answer, compare against the artifact and reply with:

- **What they got** — name it specifically. Retained knowledge deserves to be
  confirmed as retained.
- **What drifted** — where their version is subtly off. This is the most
  valuable part: a confidently-held wrong model does more damage than a blank,
  and it is invisible without a test like this.
- **What's gone** — state it flatly, then re-teach it *briefly*. Two or three
  sentences, aimed at the specific gap. Do not re-teach the whole topic; the
  artifact already exists and they can reopen it.
- **One grade**: `miss` (little came back), `partial` (shape retained, details
  gone), `good` (reproduced it, including a gotcha).

If a gap is large enough that re-teaching it properly needs a real lesson, say
so and suggest a fresh `learning-mode` session on that sub-topic rather than
cramming it in here.

## Close the loop

1. **Append to the log** with the Write/Edit tools:
   ```
   2026-07-31 cpp17-memory-management partial
   ```
   Create `~/learning-mode/.reviews.log` if missing.
2. **Say when it comes up next**, per the interval table — one line.
3. **If the grade is `miss` or `partial`, hand them one concrete action** in
   their own code: a thing to write, from scratch, that exercises the part that
   drifted. Not a reread. Re-reading the artifact is the least effective option
   available and it's the one they'll otherwise pick. If the drifted part is
   sharp enough to drill, offer a `learning-exercise` session on it — that skill
   scaffolds a runnable, gradable version of exactly this action.

Then stop. A review is five minutes; don't turn it into a lesson.
