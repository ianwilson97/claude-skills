# driver-seat cheap workers — design

**Date:** 2026-10-03 · **Status:** approved in brainstorming, awaiting spec review · **Branch:** `driver-seat-cheap-workers`

## Goal

Run driver-seat on a personal Claude plan without burning usage limits, at the quality of the current Opus-driven setup, by moving the token-heavy navigator jobs to cheap models running as separate Claude Code sessions that the orchestrator talks to by message.

What the driver asked for: Claude Code stays the harness; cheaper models; same performance; multiple agents with message passing; shared state; the ability to watch and prompt the agents.

Assumed and confirmed: the driver still writes the code (driver rule unchanged), so workers do navigator jobs only.

## Background (probe, 2026-10-03)

A throwaway probe ran a Claude Code worker on OpenRouter (`deepseek/deepseek-v4.1-flash`, pinned) in a detached tmux session and drove it from a plan-billed orchestrator:

- `ListAgents` listed the OpenRouter worker; `SendMessage` delivered a task; the worker replied by `SendMessage` and wrote a notes file; `notify_when_idle` fired. Cross-session messaging works across providers.
- 26 turns, 2.59M prompt tokens, 71% cache hits, about $0.26. The cache plateaued at ~78k tokens, so the growing conversation tail was re-sent uncached each turn (~760k uncached tokens, ~$0.23). One full cache miss mid-session (turn 22). Causes not verified.
- Turn 1 sent 71k tokens: the global config (hooks, MCP schemas with ToolSearch off over OpenRouter, skill listing). Cheap when cached, expensive on a miss.
- In auto mode the worker hit a blocking dialog: auto-mode classifier calls are billed through OpenRouter.
- The two spot-checked worker claims (Pi README line 19, `anthropic.ts:270`) were accurate.

Already shipped alongside this work: the `research` skill runs as `context: fork` + `model: sonnet` (on plan, off the Opus main thread).

## Decisions

| Question | Decision |
|---|---|
| Where the orchestrator runs | Claude Code on the Claude plan (Opus/Sonnet). Keeps planning, decisions, review. |
| Jobs moved off-plan | **Research** and **chores**. Recon stays on plan haiku; review stays on plan (it is the quality gate). |
| Worker lifetime | Fresh worker per task; it exits after reporting. |
| Where chores edit | Own git branch + worktree per chore; the driver merges. |
| Rejected result | One cheap retry with the review findings; second failure goes to a plan-side Sonnet subagent. |
| Mechanism | Interactive Claude Code workers in tmux + cross-session messaging (approach A). Fallback: headless `claude -p` workers (approach B) if Phase 0 fails. |
| Machines without cost concern (work laptop) | `cw` is off when `CW_OPENROUTER_API_KEY` is unset; driver-seat then behaves exactly as today. |

## Non-goals

- Pi or any non-Claude-Code harness (subscription OAuth is restricted to Claude Code/Claude.ai; Pi sessions are not reachable by `SendMessage`).
- Agent teams (teammates inherit the lead's provider, so they cannot be cheap).
- Orchestrator off-plan, recon or review off-plan.
- SQLite, daemons, worker pools, a config file. Files are the shared database.

## Components

All new files live in the driver-seat skill: `plugins/driver-seat/skills/driver-seat/`. The local install `~/.claude/skills/driver-seat` becomes a symlink to that directory, so there is one source of truth (today the two copies are identical).

### `scripts/cw` (zsh, ~40 lines)

```
cw <research|chore> <task-id> <orchestrator-name>
```

1. Refuse to run unless `CW_OPENROUTER_API_KEY` is set (dedicated OpenRouter key with a credit limit — the spend cap) and `.driver-seat/tasks/<task-id>.md` exists.
2. Model per job: two variables at the top, `CW_RESEARCH_MODEL` and `CW_CHORE_MODEL`, both defaulting to `deepseek/deepseek-v4.1-flash`. Resolved at launch and passed to the pane in the run string, because a tmux pane gets the server's env, not the caller's.
3. Working directory. "Repo" means the caller's checkout (`git rev-parse --show-toplevel`); a linked worktree is its own checkout.
   - research: `<repo>/.driver-seat`, so `acceptEdits` auto-approves edits there only, never in the driver's code. The repo is read-only for the worker. The shell is denied (`--disallowedTools Bash`), because an unlisted shell call would wait on a permission prompt nobody answers.
   - chore: `git worktree add .driver-seat/wt/<task-id> -b cw/<task-id> <caller's HEAD>`, cwd = that worktree.
   - Any launch failure removes the chore's branch and worktree, so a relaunch starts clean.
4. Environment (as the probe launcher): `ANTHROPIC_BASE_URL=https://openrouter.ai/api`, `ANTHROPIC_AUTH_TOKEN=$CW_OPENROUTER_API_KEY`, `ANTHROPIC_API_KEY=""`, and every `ANTHROPIC_DEFAULT_*_MODEL` plus `CLAUDE_CODE_SUBAGENT_MODEL` set to the job's model.
5. Command:
   ```
   claude -n cw-<task-id> --model sonnet --bare --strict-mcp-config \
     --permission-mode acceptEdits --add-dir <repo>/.driver-seat \
     --allowedTools <job allowlist> "<first prompt>"
   ```
   - research allowlist: `Read Grep Glob Write Edit WebFetch WebSearch ListAgents SendMessage` (no shell; see Phase 0 results for the final flags, which replace `--bare`)
   - chore allowlist: `Read Grep Glob Write Edit Bash(git status:*) Bash(git diff:*) Bash(git add:*) Bash(git commit:*) ListAgents SendMessage`, plus `Bash(<test>:*)` when the task frontmatter has `test:`.
6. tmux: session `cw`, window `workers`. Create the session detached if missing (`tmux new-session -d -s cw -n workers`), else `split-window` into `cw:workers`; then `select-layout tiled`. Label the pane with a pane option, `set -p @cw cw-<task-id>` (not `select-pane -T`: Claude Code overwrites the pane title), and for the `cw` session only set `mouse on`, `pane-border-status top`, `pane-border-format " #{@cw} "`.
7. Ready check, polling `capture-pane` for up to 30 s: ready when the capture contains the model id (it appears in Claude Code's status line) and none of the blocking-dialog strings `trust this folder`, `Enter to continue`. On a dialog string or timeout: print the pane capture, kill the pane, exit 1. Never send keystrokes to a dialog.
8. On success print the pane id (`#{pane_id}`, e.g. `%12`) on stdout; the orchestrator uses it to kill the pane later.

First prompt (exact):

```
You are cw-<task-id>, a <job> worker for <orchestrator-name>.
Read <repo>/.driver-seat/tasks/<task-id>.md and do exactly that task.
Scratch files go in <repo>/.driver-seat/tmp/ only.
Write your result to <repo>/.driver-seat/results/<task-id>.md.
If blocked, SendMessage to <orchestrator-name>: "blocked <task-id>: <question>" and wait.
When done, SendMessage to <orchestrator-name>: "done <task-id>" plus a summary of at most 5 lines.
```

### Task file — `.driver-seat/tasks/<task-id>.md`

Written by the orchestrator. Task ids follow the todo convention, `NNN-slug`; a retry uses `<task-id>-r1`.

```markdown
---
job: research | chore
todo: NNN-slug          # the driver-seat todo this serves, if any
test: npm test          # chores only, optional
---
# <one-line task>
## Context
<everything the worker needs — it never sees the conversation>
## Done when
- <checkable condition>
## Previous review findings
<retry only>
```

Research tasks add: "Follow the method and output format in `~/.agents/skills/research/SKILL.md`; write the answer to your result file, not to `~/research/`." (Read as a file, because `--bare` may not load skills.)

### Result file — `.driver-seat/results/<task-id>.md`

- research: the research skill's output format (answer, what the docs say, for your case, sources with quotes).
- chore: what changed, test command + result, commit hash on `cw/<task-id>`.

### Worker log — `.driver-seat/workers.tsv`

One row per attempt, appended by the orchestrator:

```
date  task_id  job  model  attempt  input_tok  cache_read_tok  output_tok  cost_usd  verdict  escalated  shadow
```

`verdict` ∈ `pass | fail | infra`; `escalated` ∈ `0 | 1`; `shadow` ∈ `agree | disagree | -`.

### `scripts/cw-usage` (python, stdlib)

The probe's `usage.py`, extended: given a task id, finds the worker transcript (`~/.claude/projects/<encoded cwd>/*.jsonl` for session `cw-<task-id>`), sums tokens, prices them from the public `https://openrouter.ai/api/v1/models` entry for the model, and prints one TSV row fragment.

### driver-seat `SKILL.md` edits

- **On entry:** also scan `results/` for files with no `workers.tsv` row and `tmux list-panes -t cw:workers`; collect, review, or mark `infra` accordingly.
- **Research:** when `CW_OPENROUTER_API_KEY` is set, "real questions" go to `cw research`; one-line facts inside a briefing stay inline. Otherwise, unchanged (forked `research` skill).
- **Chores:** when `cw` is enabled, chores go to `cw chore`.
- **Review cycle:** unchanged reviewers, plus the escalation rule and the research receipt check (below).
- **Keep the machine small:** name `cw` as the first choice for research and chores.

## Task flow

1. **Dispatch.** Orchestrator writes the task file, runs `cw <job> <task-id> <own name from ListAgents>`, then `SendMessage(to: cw-<task-id>, notify_when_idle: true)` as a backstop.
2. **Work.** Worker does the task; may send `blocked <task-id>: …`, which the orchestrator answers or turns into an `AskUserQuestion` for the driver if it is the driver's decision.
3. **Report.** Worker sends `done <task-id>`.
4. **Collect.** Orchestrator runs `cw-usage`, then `tmux kill-pane -t <pane id printed by cw>` unless the driver said "keep cw-<task-id>". (After a restart, pane ids come from `tmux list-panes -t cw:workers -F '#{pane_id} #{@cw}'`.)
5. **Review (plan-side).**
   - research: re-fetch each load-bearing quote's source and confirm the quoted line exists.
   - chore: `git diff <base>...cw/<task-id>` through `caveman:cavecrew-reviewer`, or `code-review` when branch-sized.
6. **Outcome.**
   - pass: research copied to `~/research/YYYY-MM-DD-slug.md`, then briefed; chore shown as a diff summary for the driver to merge (`git merge cw/<task-id>`, `git worktree remove`).
   - first fail: findings appended to the task file, `cw` relaunched as `<task-id>-r1`.
   - second fail: plan-side Sonnet subagent does the task from the same task file.
   - every attempt: one `workers.tsv` row.

## Visibility and interaction

Driver's setup (Ghostty, no tmux config needed): `Cmd+D` to split; in the new split run `tmux new -A -s cw`. Workers appear as labelled, tiled panes.

| Do | Keys |
|---|---|
| Focus a worker | click its pane |
| Prompt it | type into its Claude input |
| Full-screen one worker / back | `Ctrl-b z` |
| Leave, workers keep running | `Ctrl-b d` |

If the orchestrator runs inside tmux, `tmux switch-client -t cw` instead of attaching.

## Failure handling

Files are the source of truth; messages are only notifications.

| Failure | Handling |
|---|---|
| Worker never starts | `cw` exits 1 with a pane capture. Verdict `infra`; one relaunch, then plan-side subagent. Does not count toward model escalation. |
| Blocking dialog at startup | `cw` detects known dialog text and fails as above. |
| Hang, loop, or waiting on a permission prompt | No `done` and the idle subscription expires: inspect pane, kill it, verdict `fail`. |
| Runaway spend | Credit limit on the dedicated OpenRouter key. |
| Worker writes outside its area | Allowlist + `acceptEdits` (auto-approves edits only in cwd and `--add-dir`); anything else prompts and stalls → hang row. |
| Orchestrator restarts mid-task | Re-entry scan on driver-seat entry. |
| Bad research passes review | Accepted residual risk; the log is the audit trail; high-stakes questions can be re-run with the plan-side research skill. |
| Chore branch conflicts | Driver merges; `resolving-merge-conflicts` skill available. |

## Testing and acceptance

**Phase 0 — throwaway probe, before any code.** Five yes/no checks:

1. `--bare` keeps cross-session messaging (worker listed by `ListAgents`, can `SendMessage`).
2. A worker started in `.driver-seat/wt/<id>` of a trusted repo gets no folder-trust prompt.
3. `--permission-mode acceptEdits` avoids the auto-mode billing dialog.
4. Orchestrator (auto mode) → worker (`acceptEdits`) messages are delivered, not held for approval.
5. `--add-dir <repo>/.driver-seat` lets an `acceptEdits` worker write its result file without a prompt.

Any "no": adjust the affected flag or fall back to approach B before writing `cw`.

**`scripts/test-cw.sh`** — the runnable self-check: in a scratch git repo, run one research task ("latest tmux release; cite the release page") and one chore ("add a comment line to README"). Assert: pane `cw-<id>` appears; result file with a URL within 5 minutes; chore commit on `cw/<id>`; panes killed cleanly.

**Proving "same performance":**
- Shadow run: the first 5 research tasks also run through the plan-side forked research skill; the orchestrator compares claims and receipts and records `shadow`.
- After 10 tasks per job: if 20% or more of those tasks have a row with `escalated = 1` (finished by the plan-side subagent), change that job's model variable and run 5 more. `infra` failures do not count.

## Build order

1. Phase 0 probe.
2. Symlink `~/.claude/skills/driver-seat` → repo copy.
3. `cw`, `cw-usage`, task/result templates, `test-cw.sh`; `test-cw.sh` passes.
4. driver-seat `SKILL.md` edits.
5. Shadow run, then the 10-task review.

## Known risks

- **Cache tail stall** (probe): only the ~78k prefix stayed cached. Fresh-per-task workers keep sessions short, which limits it; cause unverified.
- **Unknown-model window:** Claude Code assumes a 200k context for the pinned model and auto-compacts there. Fine for short-lived workers.
- **`--bare` scope:** if it disables something workers need beyond Phase 0's checks, drop it and keep `--strict-mcp-config` (the MCP schemas were the bulk of the 71k).

## Phase 0 results (2026-10-03)

| Check | Result | Decision applied |
|---|---|---|
| 0 auth under --bare | `token` works (`ANTHROPIC_AUTH_TOKEN` accepted) | keep `token` auth |
| 1 --bare keeps messaging | **no**: a `--bare` worker creates no socket and is absent from `ListAgents` | drop `--bare`; use `--setting-sources project,local` (skips user settings, so user hooks and plugins) + `--strict-mcp-config`. Messaging works. Startup: 35k tokens (vs 71k full config, 1.1k bare); about 1 cent uncached per worker start. `--disable-slash-commands` measured no gain (39k) and is not used. |
| 2a new repo under trusted folder | **prompts**: trust is not inherited by a new repo under a trusted folder | the live test uses a persistent test repo (`CW_TEST_REPO`, default `~/.cache/cw-test-repo`) trusted once |
| 2b worktree under repo | trusted: no dialog in `.driver-seat/wt/<id>` of a trusted repo | none |
| 3 billing dialog with acceptEdits | absent | none |
| 4 orchestrator→worker delivery | delivered both ways (orchestrator in auto mode, worker in acceptEdits) | none |
| 5 --add-dir write without prompt | yes | none |
| 6 socket = pane pid; precedes dialogs | socket is named by claude's pid and did **not** appear while the trust dialog was up; but pane pid ≠ claude pid, because `~/.zshenv` defines a `claude` shell function, so `exec claude` runs the function, which forks | `cw` runs `exec command claude …`; the ready check looks for the socket of the pane process **or** its direct children (also covers PATH shims) |
