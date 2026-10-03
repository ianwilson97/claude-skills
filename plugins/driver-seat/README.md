# driver-seat — user guide

Pair programming with Claude, roles taken literally: **you drive** (you write the code), **Claude navigates** (it keeps the plan, looks things up, briefs each step, reviews, and takes only the chores you hand it).

The idea comes from turion's [How to keep enjoying programming in a world of LLMs](https://discourse.haskell.org/t/14705): a codebase nobody writes by hand becomes one only agents can work in, coding skill fades within weeks of handing it off, and generated code is alien to debug. The speed-up comes from offloading everything *around* the coding, not the coding itself.

Use driver-seat when you want to build something **and** stay the person who understands every line of it. If you just want code written for you, use plain Claude Code instead.

---

## Contents

- [Install](#install)
- [Quick start](#quick-start)
- [The working loop](#the-working-loop)
- [What Claude will and won't do](#what-claude-will-and-wont-do)
- [Files it keeps](#files-it-keeps)
- [Handing off chores](#handing-off-chores) — including [red tests first](#red-tests-first)
- [Research and receipts](#research-and-receipts)
- [Reviews](#reviews)
- [Other skills inside the mode](#other-skills-inside-the-mode)
- [Cheap workers (`cw`)](#cheap-workers-cw) — optional, keeps costs down
- [Tips for using it well](#tips-for-using-it-well)
- [Troubleshooting](#troubleshooting)
- [Known limitations](#known-limitations)

---

## Install

```bash
claude plugin marketplace add ianwilson97/claude-skills
claude plugin install driver-seat@claude-skills
claude plugin install research@claude-skills   # recommended: driver-seat sends research questions here
```

driver-seat is **user-invoked only**: Claude never turns it on by itself. You start it with `/driver-seat`.

## Quick start

1. Open the project folder you want to work in, and make it a git repo if it isn't one (`git init`). driver-seat keeps its files in that folder, and the optional cheap workers need git.
2. Start Claude Code **in that folder**: `cd my-project && claude`.
3. Type `/driver-seat`.
4. Describe what you want to build, or point Claude at an existing spec. If you already have todos from an earlier session, Claude picks up where you left off instead.

Turn it off with **"stop driver-seat"** or **"normal mode"**. Your todo files stay where they are.

> Start a fresh session per project. A long-running session that has been used for other things re-reads all of that history on every turn, which burns usage for nothing.

## The working loop

```
 plan ──► todos ──► briefing ──► you code ──► "done" ──► review your diff ──► next todo
  ▲                                                                              │
  └──────────────────── new findings, bugs, scope changes ◄──────────────────────┘
```

1. **Planning.** Claude turns the conversation (or your spec, test results, bug list) into todo files, one per step. Anything crucial or hard to reverse — language, architecture, data model, API shape, a new dependency — comes to you as a question with the options and trade-offs. You decide; Claude records the answer in the todo.
2. **Briefing.** When you start a todo or ask "what's next", you get a short briefing: what "done" means, every edit site as `path:line`, the pitfalls, and reminders from linked research notes. Then Claude steps back.
3. **You code.** Ask questions as you go. "How do I implement X?" gets the approach, the edit sites and the relevant API with its docs link. It does not get your code written for you.
4. **Done.** Tell Claude the todo is done. It offers to review your diff and reports bugs and omissions only, one line each.
5. **Runway.** Claude keeps the current todo plus the next two fully briefed, so you always know what comes next.

If the same problem comes back a third time, Claude will say so and suggest stepping away from the screen to think it through. That's deliberate.

## What Claude will and won't do

| Claude does | Claude doesn't (unless you hand it over) |
|---|---|
| Plans, writes and updates todo files | Write your source code |
| Web-searches before stating any outside fact, and cites it | Answer from memory without saying it's unverified |
| Briefs each todo with edit sites and pitfalls | Make architecture, data-model, API or dependency choices for you |
| Reviews its own output with a second agent before you see it | Show you unreviewed machine output |
| Reviews your diffs on request | Write commit messages, PR descriptions or code reviews for colleagues |
| Takes chores you explicitly hand over | Design something complex from scratch as a "chore" |

**Human-facing writing stays yours.** Asked to "write the commit/PR", Claude produces a collapsed `Tool output (AI-generated)` block (diffstat, test results, a mechanical change summary) plus three prompts for what a reviewer needs to hear in your own words.

## Files it keeps

Everything lives in `.driver-seat/` in your project. Claude offers once to add it to `.gitignore` (when `cw` runs, it also adds it to the repo-local `.git/info/exclude`).

```
.driver-seat/
├── todos/NNN-slug.md     the plan: one file per step (source of truth)
├── tasks/NNN-slug.md     briefs for cheap workers          (cw only)
├── results/NNN-slug.md   what workers produced             (cw only)
├── wt/NNN-slug/          git worktrees for chore workers   (cw only)
├── tmp/                  worker scratch space              (cw only)
└── workers.tsv           one row per worker attempt        (cw only)
```

A todo looks like this:

```markdown
---
status: todo        # todo | doing | done | blocked
owner: driver       # driver | navigator (chore)
decisions: []       # open questions for you, then your answers
research: []        # ~/research/... notes this todo leans on
---
# <title>
## Edit sites
- `path:line` `symbol` — what changes
## Interface
- <signatures you agreed: names, parameters, return and error types> (optional; needed for red tests)
## Pitfalls
- <pitfall> — <link, if external>
## Done when
- <checkable condition>
```

**The files are the source of truth, not the chat.** After a context compaction, a crash, or running out of tokens, Claude re-reads them. You can keep working offline from the files when Claude is unavailable, and it catches up when it's back. You can also edit them by hand.

## Handing off chores

Some work isn't worth your keystrokes. Hand it over explicitly:

- **"just write it"** — turns the current thing into a chore.
- **"I'm afk, finish this"** — for remaining low-risk todos.

Good chores: FIXMEs, mechanical renames, the remaining cases of a pattern you've already established, dependency swaps, low-risk refactors, benchmarking, and filling in bodies for signatures you already wrote.

Every chore goes through the review cycle before you see it, and Claude reports what changed, where, and how many review rounds it took.

Before generating "the 7 boring cases" of something, Claude asks whether it's really an abstraction (a higher-order function, a table-driven loop, a type-class instance). LLMs default to copy-paste; you probably want readable code.

**Set your own split.** Write 5–10 lines in `~/.claude/driver-seat-split.md` about what you enjoy writing and what you'd rather hand off; Claude reads it on entry and uses it to decide what counts as a chore. It lives outside the plugin so updates never overwrite it. Without it, the default is: you write all logic, types and tests. Example:

```markdown
# My split
- I write all implementation logic and types.
- Red tests first: before I start a todo, a cheap worker writes the stubs (from the
  todo's ## Interface) and all its tests, and verifies they fail.
- I read every test before coding and may change any I disagree with.
```

### Red tests first

If your split hands test-writing over, every todo gets failing tests before you start it (test-driven development, with you doing the green part):

1. **You agree the interface first.** The todo's `## Interface` lists the signatures. Tests encode the API, so a missing interface is a design question for you, not something the worker guesses.
2. **A worker writes stubs and tests.** Stubs are your agreed signatures copied exactly, with not-implemented bodies (`raise NotImplementedError`, `panic("not implemented")`, `todo!()`…), so each test fails on its own assertion instead of on a compile or import error (in C, Go or Rust one missing symbol would stop the whole test build). Tests cover every **Done when** condition and the edge cases the pitfalls name.
3. **It runs them and confirms they fail for the right reason**, and existing tests still pass. Claude re-runs them on its side and reviews the tests before you see them.
4. **You merge the tests branch and read the tests first.** They're the spec for the todo. They're also a proposal: change any test you disagree with.

The tests for the next todo are written while you code the current one, so you don't wait. With `cw` enabled this runs on the cheap model (task `NNN-slug-tests`); otherwise on a Sonnet subagent.

## Research and receipts

Every claim about the outside world — library behaviour, flags, versions, error meanings, best practices — has to come from a search made in that session, with a link. Memory only aims the search.

- **Real questions** go to the `research` skill (or to a cheap worker, see below). You get a short answer plus a path; the full answer, with quotes and links, is a markdown file in `~/research/`.
- **Quick facts** inside a briefing get a fast search and an inline citation.
- **Before longer research**, Claude first gives you 2–3 search queries or primary links, so you can read along. You're delegating the googling, not the understanding.
- **Confidence is stated.** For odd APIs and platform quirks, Claude says whether it found the best solution or a common workaround.
- **Pushback is welcome.** If you disagree, Claude goes back to the note and quotes the source. Often that exposes its own mistake.

Past answers are greppable: `grep -ril <topic> ~/research/`.

## Reviews

Nothing Claude produces reaches you until a separate reviewer agent has run out of findings (or 3 rounds have passed, in which case you see what's left alongside the result).

| What | Reviewer |
|---|---|
| Plans and todos | a Sonnet subagent: checks ordering holes, missing edit sites, uncited claims, and decisions Claude made that belong to you |
| Chore code | a small-model diff reviewer; branch-sized changes go to a full code review |
| Your diffs (on request) | bugs and omissions only, one line each |

Claude asks once per session whether minor nits should just be fixed silently.

## Other skills inside the mode

driver-seat is a frame; other skills run inside it under the same rules (if a skill would write your code, Claude keeps the method and hands the writing back). Some are model-invoked; others (marked ✋) you type yourself.

| Situation | Skill |
|---|---|
| Outside fact, API, error, version | `research` |
| You want to understand a concept deeply | `learning-mode`, then `learning-exercise` / `learning-review` |
| Stress-test a plan | `grilling`, ✋ `/grill-me` |
| Fuzzy new feature | `superpowers:brainstorming` (output: todos) |
| Module or API shape, coupling smells | `design-an-interface`, `codebase-design` |
| Bug, failing test, slowness | `diagnosing-bugs` / `superpowers:systematic-debugging` — Claude finds the cause and location, you fix it |
| Test-first | `tdd` — Claude writes red tests per **Your split**, you make them green |
| Throwaway exploration | `prototype` |

These come from other plugins; driver-seat uses whichever are installed.

---

## Cheap workers (`cw`)

Optional. On a personal Claude plan, research and chores are the jobs that burn the most usage. With `cw` enabled, they run **off your plan** on a cheap pinned OpenRouter model, each in a fresh Claude Code session that you can watch and talk to in tmux. Planning, decisions and all reviews stay on your plan, because checking work costs far fewer tokens than producing it.

In testing with the default model (`deepseek/deepseek-v4.1-flash`), a research task cost about **1.4¢** and a small chore about **0.3¢**.

### Setup

1. Create a **dedicated** OpenRouter key with a **credit limit** (the hard cap on spend).
2. Export it from `~/.zshenv` (not `~/.zshrc`: tmux panes and scripts only read `.zshenv`):
   ```zsh
   export CW_OPENROUTER_API_KEY=sk-or-...
   ```
3. Install tmux (tested with 3.7) and use a git repo for your project.
4. To watch workers, split your terminal (Ghostty: **Cmd+D**) and run `tmux new -A -s cw` in the new split.

Without the key (for example on a work machine where cost doesn't matter), driver-seat behaves exactly as without `cw`. `scripts/cw --check` exits 0 when `cw` is enabled.

### How a task flows

1. Claude writes a self-contained brief to `.driver-seat/tasks/NNN-slug.md` (the worker never sees your conversation).
2. `cw` opens a pane labelled `cw-NNN-slug` in the `cw` tmux session, tiled with the others.
3. The worker writes `.driver-seat/results/NNN-slug.md` and messages Claude `done NNN-slug`. If it's stuck it messages `blocked NNN-slug: <question>`, and Claude answers or asks you.
4. Claude prices the run, closes the pane, and reviews the result on your plan: research quotes are re-checked against their sources; chore diffs go through the reviewer.
5. **Pass:** research is archived to `~/research/` and briefed to you; a chore is shown as a diff on branch `cw/NNN-slug` for **you** to merge.
   **Fail:** one retry on the cheap model with the review findings; a second failure moves the task to a Sonnet subagent on your plan.

### Watching and talking to workers

| Do | How |
|---|---|
| See all workers | the `cw` split (`tmux new -A -s cw`) |
| Focus a worker | click its pane |
| Prompt a worker | type into its Claude input, like any session |
| Full-screen one / back | `Ctrl-b z` |
| Leave, workers keep running | `Ctrl-b d` |
| Keep a worker after it finishes | tell Claude "keep cw-NNN-slug" |

If you started Claude itself inside tmux, use `tmux switch-client -t cw` (or `prefix s`) instead of attaching.

### Chores and your branches

- Each chore gets its own branch `cw/NNN-slug` and worktree `.driver-seat/wt/NNN-slug`, cut from the HEAD of the checkout you're working in, so it never touches files you're editing.
- You merge: `git merge cw/NNN-slug`, then `git worktree remove .driver-seat/wt/NNN-slug` and `git branch -d cw/NNN-slug`.
- A chore task can name a test command (`test: npm test` in its frontmatter). Besides that, the worker may run only `git status/diff/add/commit` and read-only commands such as `ls` or `cat`.

### Is it working?

Every attempt is logged in `.driver-seat/workers.tsv` (model, tokens, cost, verdict, escalation). The first 5 research tasks also run on your plan as a **shadow** comparison. After 10 tasks of a kind, if 20% or more needed escalation, Claude suggests a different model.

To change models, export `CW_RESEARCH_MODEL` and/or `CW_CHORE_MODEL` (any OpenRouter model id that supports tool calling) in `~/.zshenv`, or edit the two variables at the top of `scripts/cw`.

### What workers can and can't do

| | Research worker | Chore worker |
|---|---|---|
| Working folder | `.driver-seat/` | its own worktree |
| Edits auto-approved | inside `.driver-seat/` only | inside its worktree and `.driver-seat/` |
| Shell | none (denied) | `git status/diff/add/commit`, read-only commands, and the task's test command |
| Web | WebFetch, WebSearch | none |
| Your hooks, plugins, MCP servers | not loaded | not loaded |

Anything outside these lines makes the worker stop at a permission prompt, which you'll see in its pane.

**Security note.** Research workers read untrusted web pages and can read files anywhere on your machine. A malicious page could, in principle, trick one into reading a secret and leaking it in a fetched URL. The credit limit caps spend, not that. Keep secrets you care about out of plain-text files the worker can read, and use `cw` for public-docs research.

### Testing `cw`

```bash
zsh scripts/test-cw.sh          # free offline checks
zsh scripts/test-cw.sh --live   # two real workers, a few cents
```

The live test needs a repo that Claude Code already trusts, because Claude Code never trusts a brand-new folder on its own. It uses `CW_TEST_REPO` (default `~/.cache/cw-test-repo`): run `claude` there once, choose "Yes, I trust this folder", and exit. The live test refuses to run against a repo that has real driver-seat state.

---

## Tips for using it well

- **Write your split** (`~/.claude/driver-seat-split.md`) before your first real session. It's the biggest lever on how much Claude does versus you.
- **Agree each todo's interface during planning** if you use red tests first; it's what the tests are written against.
- **Bring a spec.** A one-page description of the goal and constraints makes the planning round short and the todos sharp.
- **Answer the decision questions.** If a question doesn't give you enough to decide, say so; Claude should add context rather than decide for you.
- **Edit the todo files freely.** They're plain markdown and Claude re-reads them.
- **Read the briefing before coding**, especially the pitfalls and the linked research notes.
- **Ask for a diff review when you finish a todo.** It's cheap and catches the things you'd find later.
- **Push back** when something sounds wrong. You'll get the source quoted back to you.
- **Take breaks.** If Claude suggests one, it's because the same problem has come back three times.
- **Keep the main session lean**: one session per project, and let research go to the `research` skill or `cw` workers rather than pasting docs into the chat.

## Troubleshooting

| Symptom | Likely cause and fix |
|---|---|
| `/driver-seat` doesn't exist | The plugin isn't installed, or you typed it in a session started before installing. Restart Claude Code. |
| Claude writes your code anyway | Say "you're the navigator" or re-run `/driver-seat`; check that **Your split** doesn't hand off more than you meant. |
| `cw --check` fails | `CW_OPENROUTER_API_KEY` isn't exported from `~/.zshenv`, or tmux isn't on your `PATH`. |
| Worker never starts, capture shows a trust dialog | The project folder hasn't been trusted yet: run `claude` in it once and accept. |
| Worker pane sits at a permission prompt | It tried something outside its allowlist. Answer it yourself in the pane, or kill the pane and let Claude retry. |
| No `done` message after a Claude restart | Workers message the session name that dispatched them, so a new session misses it. On entry, driver-seat reconciles `results/` and the tmux panes instead. |
| A `workers.tsv` cost shows `NA` | The worker made no API calls, its transcript is older than 3 days, or its last call was an API error (for example, the key hit its credit limit). |
| Leftover `cw/*` branches or `.driver-seat/wt/*` | Failed or merged chores aren't cleaned up automatically yet: `git worktree remove` and `git branch -D` them. |

## Known limitations

- Research briefs point workers at `~/.agents/skills/research/SKILL.md` for the method. If your `research` skill is installed elsewhere, adjust the path in the task template in `SKILL.md`.
- `cw` targets the tmux session `cw` by prefix, so another session whose name starts with `cw` (e.g. `cwork`) can be mistaken for it when no `cw` session exists.
- `cw` relies on Claude Code's per-session messaging socket (`/tmp/cc-socks/<pid>.sock`) to know a worker is ready. If a Claude Code update changes that, launches fail and the work falls back to your plan.
- Worker sessions skip your user-level settings, so your user-level permission deny rules and guard hooks don't apply to them; their own allowlists are narrow instead.

Design notes and the measurements behind `cw`: [`docs/superpowers/specs/2026-10-03-driver-seat-cheap-workers-design.md`](../../docs/superpowers/specs/2026-10-03-driver-seat-cheap-workers-design.md).
