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

### driver-seat

Pair-programming mode based on turion's
[How to keep enjoying programming in a world of LLMs](https://discourse.haskell.org/t/14705).
You are the driver and write the code; Claude is the navigator: it keeps the plan
as todo files in `.driver-seat/todos/`, web-searches before stating any external
fact (via `research`), briefs each todo with edit sites and pitfalls, runs an
automated review cycle on everything it produces, and takes only the chores you
hand it. Turn on with `/driver-seat`; off with "stop driver-seat".

**Cheap workers (optional).** Research and chores can run off your Claude plan on a
cheap OpenRouter model: each task gets a fresh Claude Code worker in a tiled tmux
pane that reports back by cross-session message, and the plan-side navigator reviews
everything before you see it. Setup: create a dedicated OpenRouter key with a credit
limit, add `export CW_OPENROUTER_API_KEY=...` to `~/.zshenv`, and install tmux. To
watch and talk to workers, split your terminal and run `tmux new -A -s cw`. Without
the key, driver-seat runs exactly as before. Design:
`docs/superpowers/specs/2026-10-03-driver-seat-cheap-workers-design.md`.

**Full user guide:** [plugins/driver-seat/README.md](plugins/driver-seat/README.md) covers the
working loop, files, chores, research, reviews, cheap workers, tips and troubleshooting.

## Installation

```bash
# Add the marketplace
claude plugin marketplace add ianwilson97/claude-skills

# Install a plugin (learning-mode brings all three learning skills)
claude plugin install learning-mode@claude-skills
claude plugin install research@claude-skills
claude plugin install driver-seat@claude-skills
```

## Development

```bash
# Test plugin structure locally
claude plugin list --plugin-dir plugins/learning-mode

# Create a version tag (after pushing to GitHub)
cd plugins/learning-mode
claude plugin tag --push
```