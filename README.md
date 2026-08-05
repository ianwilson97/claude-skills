# Ian's Claude Skills

Personal collection of Claude Code skills distributed as a plugin marketplace.

## Skills

### learning-mode (plugin)

Three skills that cover a full learn → apply → retain loop:

- **learning-mode** — teaching-first: Claude explains concepts deeply and helps
  you write the solution yourself instead of handing over finished code. Writes
  an HTML artifact per session to `~/learning-mode/`.
- **learning-exercise** — generates one small runnable exercise (spec, stubs
  with TODOs, failing tests, one-command runner) into
  `~/learning-mode/exercises/`, then grades your attempt.
- **learning-review** — spaced recall over past `~/learning-mode/` artifacts:
  quizzes you closed-book, grades the gap, schedules the next review.

### research

Answers technical questions by reading current official documentation instead
of relying on memory, then hands back a summary, a worked example, and precise
citations.

## Installation

```bash
# Add the marketplace
claude plugin marketplace add ianwilson97/claude-skills

# Install a plugin (learning-mode brings all three learning skills)
claude plugin install learning-mode@claude-skills
claude plugin install research@claude-skills
```

## Development

```bash
# Test plugin structure locally
claude plugin list --plugin-dir plugins/learning-mode

# Create a version tag (after pushing to GitHub)
cd plugins/learning-mode
claude plugin tag --push
```