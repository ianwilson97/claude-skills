# driver-seat cheap workers Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let driver-seat hand research and chores to fresh Claude Code workers on a cheap pinned OpenRouter model, visible and promptable in tmux, coordinated by cross-session messages, with the plan-side orchestrator reviewing everything.

**Architecture:** A zsh launcher (`cw`) opens one interactive Claude Code worker per task in a tiled tmux pane, pointed at OpenRouter with a pinned model and lean flags. Workers read a task file, write a result file, and report with `SendMessage`. The driver-seat skill gains a **Cheap workers** section that dispatches, collects, reviews, escalates, and logs. `cw_usage.py` turns a worker's transcript into tokens and cost.

**Tech Stack:** zsh, tmux ≥ 3.1, git ≥ 2.31, python3 (stdlib only), Claude Code ≥ 2.1.248, OpenRouter.

**Spec:** `docs/superpowers/specs/2026-10-03-driver-seat-cheap-workers-design.md`

**Deviations from the spec (deliberate):**
- `scripts/cw-usage` is `scripts/cw_usage.py`, so its test can import it.
- `workers.tsv` puts `attempt` before `model`, so `cw_usage.py`'s output pastes in as one contiguous fragment.
- Phase 0 gains check 0 (auth under `--bare`: its help says Anthropic auth is "strictly ANTHROPIC_API_KEY or apiKeyHelper") and check 6 (ready signal = Claude Code's per-session socket `/tmp/cc-socks/<pid>.sock`).
- The live test makes its scratch repo under the current directory (must be inside a folder Claude Code trusts) instead of a temp dir.

## Global Constraints

- Default model for both jobs: `deepseek/deepseek-v4.1-flash`, overridable by `CW_RESEARCH_MODEL` / `CW_CHORE_MODEL`.
- Key: `CW_OPENROUTER_API_KEY` — a dedicated OpenRouter key with a credit limit, exported from `~/.zshenv`. Unset means `cw` is off and driver-seat behaves exactly as today.
- Paths: `.driver-seat/tasks/<task-id>.md`, `.driver-seat/results/<task-id>.md`, `.driver-seat/tmp/`, `.driver-seat/wt/<task-id>`, `.driver-seat/workers.tsv`.
- Names: task id `NNN-slug` (regex `^[0-9]{3}-[a-z0-9-]+$`), worker `cw-<task-id>`, branch `cw/<task-id>`, retry id `<task-id>-r1`.
- tmux: session `cw`, window `workers`, pane label in pane option `@cw`, layout `tiled`, `mouse on` for the `cw` session only.
- Worker flags: `--model sonnet --bare --strict-mcp-config --permission-mode acceptEdits --add-dir <repo>/.driver-seat`.
- Blocking-dialog strings: `trust this folder`, `Enter to continue`. Ready timeout: 30 s. Never send keystrokes to a worker dialog.
- Thresholds: shadow-run the first 5 research tasks; after 10 tasks per job, 20% or more escalated (infra excluded) → change that job's model.
- No new dependencies.

## Review Focus

1. **Unsafe task ids** (spaces, slashes, uppercase) must be rejected with exit 2 before anything touches git or tmux. → Task 3 test "unsafe task id exits 2".
2. **Re-running a chore whose branch already exists** (after a crash) must exit 2 without half-creating a worktree; a chore whose worker fails to start must leave no branch/worktree behind. → Task 3 test "existing chore branch exits 2"; cleanup code in `cw`.
3. **Running `cw` from a subdirectory or from inside a worktree** must still resolve the main repo. → Task 3 tests "works from a subdirectory", "works from inside a worktree".
4. **A `cw` tmux session the driver created first** (`tmux new -A -s cw`, no `workers` window) must get a `workers` window, not an error. → Task 3 live test pre-creates that session.
5. **A worker that never makes an API call** must produce a well-formed `NA` row, not a crash. → Task 2 test "missing transcript → NA row".

---

### Task 0 (driver, manual): OpenRouter key

Nothing below can run until this exists.

- [ ] **Step 1:** On openrouter.ai, create a new API key named `cw` with a credit limit (suggest $5).
- [ ] **Step 2:** Add to `~/.zshenv` (sourced by every zsh, including tmux panes and scripts):

```zsh
export CW_OPENROUTER_API_KEY=sk-or-...   # dedicated cw key with a credit limit
```

- [ ] **Step 3:** Verify in a new terminal:

Run: `zsh -c '[[ -n $CW_OPENROUTER_API_KEY ]] && echo set'`
Expected: `set`

---

### Task 1: Phase 0 probe (throwaway; gate for Task 3)

Runs in the **main session** — it needs `ListAgents`/`SendMessage` and receives the worker's reply. Nothing from this task is kept except the results table.

**Files:**
- Create (scratch, deleted at the end): `$S/p0.zsh` where `$S` is your scratch directory; scratch repo `~/Apps/.cw-phase0` (`~/Apps` is a trusted folder; the repo itself is new, so it also tests trust inheritance).
- Modify: `docs/superpowers/specs/2026-10-03-driver-seat-cheap-workers-design.md` (append results)

- [ ] **Step 1: Write the throwaway launcher** `$S/p0.zsh`

```zsh
#!/bin/zsh
# Phase 0 throwaway launcher: p0.zsh <token|helper|apikey> <cwd> <name> <add-dir> <prompt>
auth=$1 dir=$2 name=$3 adddir=$4 prompt=$5
M=deepseek/deepseek-v4.1-flash
export ANTHROPIC_BASE_URL=https://openrouter.ai/api
export ANTHROPIC_DEFAULT_OPUS_MODEL=$M ANTHROPIC_DEFAULT_SONNET_MODEL=$M
export ANTHROPIC_DEFAULT_HAIKU_MODEL=$M CLAUDE_CODE_SUBAGENT_MODEL=$M
extra=()
case $auth in
  token)  export ANTHROPIC_AUTH_TOKEN=$CW_OPENROUTER_API_KEY ANTHROPIC_API_KEY= ;;
  helper) unset ANTHROPIC_AUTH_TOKEN ANTHROPIC_API_KEY
          extra=(--settings '{"apiKeyHelper":"printf %s \"$CW_OPENROUTER_API_KEY\""}') ;;
  apikey) unset ANTHROPIC_AUTH_TOKEN; export ANTHROPIC_API_KEY=$CW_OPENROUTER_API_KEY ;;
esac
cd $dir && exec claude -n $name --model sonnet --bare --strict-mcp-config $extra \
  --allowedTools "Read,Write,Edit,ListAgents,SendMessage" --add-dir $adddir \
  --permission-mode acceptEdits $prompt
```

- [ ] **Step 2: Create the scratch repo and worktree**

```zsh
P0=$HOME/Apps/.cw-phase0
git init -q $P0 && git -C $P0 commit -q --allow-empty -m init
mkdir -p $P0/.driver-seat/{tasks,results,tmp}
git -C $P0 worktree add -q -b cw/001-p0 $P0/.driver-seat/wt/001-p0
```

- [ ] **Step 3: Checks 0, 2a, 3, 6 — repo-root worker, `token` auth**

```zsh
tmux new-session -d -s p0 -x 200 -y 50 \
  "exec zsh $S/p0.zsh token $P0 p0-a $P0/.driver-seat 'What is 17*3? Reply with the number only.'"
pid=$(tmux display -p -t p0 '#{pane_pid}')
for i in {1..30}; do
  sleep 1; s=$(tmux capture-pane -p -t p0)
  print "$i $([[ $s == *("trust this folder"|"Enter to continue")* ]] && echo dialog || echo -) $([[ -S /tmp/cc-socks/$pid.sock ]] && echo sock || echo -)"
done | uniq -c -f1
tmux capture-pane -p -t p0 | grep -v '^\s*$' | tail -15
```

Read the output:
- **Check 0 (auth):** the pane shows a reply `51` → `token` works. An auth error (401, "invalid", "API key") → `tmux kill-session -t p0`, rerun this step with `helper`, then `apikey`. Note which works, or "none".
- **Check 2a (trust inheritance):** `dialog` with "trust this folder" in the capture → a new repo under a trusted folder is **not** trusted.
- **Check 3 (billing dialog):** "Enter to continue" in the capture → yes.
- **Check 6 (ready signal):** `sock` appears → the socket is named by the pane pid. If `sock` ever appears on a line that also says `dialog`, the socket can precede a dialog.

Then: `tmux kill-session -t p0`.

- [ ] **Step 4: Checks 1, 2b, 4, 5 — worktree worker, messaging**

Use the auth that passed in Step 3 (`token` if "none"; then also remove `--bare` from `p0.zsh` for this step and record it).

```zsh
tmux new-session -d -s p0w -x 200 -y 50 \
  "exec zsh $S/p0.zsh <AUTH> $P0/.driver-seat/wt/001-p0 cw-001-p0 $P0/.driver-seat 'Wait for a message from another Claude session and do what it says.'"
pid=$(tmux display -p -t p0w '#{pane_pid}')
for i in {1..30}; do [[ -S /tmp/cc-socks/$pid.sock ]] && break; sleep 1; done
tmux capture-pane -p -t p0w | grep -v '^\s*$' | tail -15
```

- **Check 2b (worktree trust):** "trust this folder" in the capture → yes, worktrees prompt.
- **Check 1a:** call `ListAgents` → `cw-001-p0` is listed?
- **Checks 1b + 4 + 5:** `SendMessage(to: "cw-001-p0", message: "Phase 0 check: write the single word ok to <P0>/.driver-seat/results/001-p0.md, then SendMessage me the word pong.")`. Expected: a `pong` message arrives (1b: `--bare` keeps messaging; 4: not held for approval — a `[Cross-session delivery notice]` saying it was held means 4 failed), and `cat $P0/.driver-seat/results/001-p0.md` prints `ok` with no permission prompt visible in the pane (5).

Then: `tmux kill-session -t p0w`.

- [ ] **Step 5: Record results and decisions**

Append to the spec:

```markdown
## Phase 0 results (YYYY-MM-DD)

| Check | Result | Decision applied |
|---|---|---|
| 0 auth under --bare | token / helper / apikey / none | … |
| 1 --bare keeps messaging | yes / no | … |
| 2a new repo under trusted folder | trusted / prompts | … |
| 2b worktree under repo | trusted / prompts | … |
| 3 billing dialog with acceptEdits | absent / present | … |
| 4 orchestrator→worker delivery | delivered / held | … |
| 5 --add-dir write without prompt | yes / no | … |
| 6 socket = pane pid; precedes dialogs | yes/no; yes/no | … |
```

Decision table — apply the matching edits to Task 3's code before starting Task 3:

| Failed check | Edit to `cw` (Task 3 Step 3) |
|---|---|
| 0: `helper` works | Replace the `ANTHROPIC_AUTH_TOKEN` export line with `export ANTHROPIC_BASE_URL=https://openrouter.ai/api; unset ANTHROPIC_AUTH_TOKEN ANTHROPIC_API_KEY` and add `--settings '{"apiKeyHelper":"printf %s \"$CW_OPENROUTER_API_KEY\""}'` to `cmd` right after `--strict-mcp-config`. |
| 0: `apikey` works | Replace the export line with `export ANTHROPIC_BASE_URL=https://openrouter.ai/api ANTHROPIC_API_KEY=$CW_OPENROUTER_API_KEY; unset ANTHROPIC_AUTH_TOKEN`. |
| 0: none, or 1 fails | Remove `--bare` from `cmd` (keep `--strict-mcp-config`) and from the "flags present" test; keep `token` auth. |
| 2b fails | Chores run from the repo root: set `dir=$repo` for chores, change `--add-dir $ds` to `--add-dir $ds $ds/wt/$id` (still before `--permission-mode`), replace the four git tools with `"Bash(git -C $ds/wt/$id status:*)" "Bash(git -C $ds/wt/$id diff:*)" "Bash(git -C $ds/wt/$id add:*)" "Bash(git -C $ds/wt/$id commit:*)"`, and add the prompt line `Your worktree is $ds/wt/$id: edit files there and run git as git -C $ds/wt/$id.` Update the "research cannot git commit" test to match `git -C`. |
| 2a fails | Run the live test with `CW_TEST_PARENT=<a folder you have explicitly trusted in Claude Code>`. |
| 3 fails | Stop. Report to the driver: workers would need approach B (headless `claude -p`); re-plan. |
| 4 fails | Keep `cw` as is; in Task 4's SKILL.md text replace "answer by `SendMessage`" with "tell the driver to answer in the worker's pane (`tmux new -A -s cw`)". |
| 5 fails | Add `"Write(/$ds/**)" "Edit(/$ds/**)"` to both `tools` arrays (a leading `//` marks an absolute path in permission rules; `$ds` already starts with `/`). |
| 6: socket not at pane pid | In the ready check use `pid=$(pgrep -P $(tmux display -p -t $pane '#{pane_pid}') | head -1)`. |
| 6: socket precedes dialogs | Change `(( ++clean >= 2 ))` to `(( ++clean >= 4 ))`. |

- [ ] **Step 6: Clean up and commit**

```zsh
rm -rf $HOME/Apps/.cw-phase0 $S/p0.zsh
cd ~/Apps/claude-skills
git add docs/superpowers/specs/2026-10-03-driver-seat-cheap-workers-design.md
git commit -m "Record Phase 0 probe results for cheap workers"
```

---

### Task 2: `cw_usage.py` — worker tokens and cost

**Files:**
- Create: `plugins/driver-seat/skills/driver-seat/scripts/cw_usage.py`
- Test: `plugins/driver-seat/skills/driver-seat/scripts/test_cw_usage.py`

**Interfaces:**
- Consumes: Claude Code transcripts `~/.claude/projects/*/*.jsonl`; `cw`'s first prompt begins `You are cw-<task-id>, ` (Task 3).
- Produces: CLI `cw_usage.py <task-id>` → one line `model\tinput_tok\tcache_read_tok\toutput_tok\tcost_usd`, exit 0; `NA\t0\t0\t0\tNA` when no transcript; exit 2 on bad usage. Functions `find_transcript(task_id, projects=None) -> str|None`, `sum_usage(path) -> (model, {"input","cache_read","output"})`, `cost(tot, pricing) -> float`.

All paths below are relative to `plugins/driver-seat/skills/driver-seat/`.

- [ ] **Step 1: Write the failing test** `scripts/test_cw_usage.py`

```python
"""Run: python3 scripts/test_cw_usage.py"""
import contextlib, io, json, os, sys, tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cw_usage


def write_transcript(projects, task_id, responses):
    proj = os.path.join(projects, "-tmp-repo")
    os.makedirs(proj, exist_ok=True)
    path = os.path.join(proj, "s1.jsonl")
    with open(path, "w") as f:
        first = f"You are cw-{task_id}, a research worker for boss."
        f.write(json.dumps({"type": "user", "message": {"role": "user", "content": first}}) + "\n")
        for mid, model, usage in responses:
            for _ in range(2):  # one API response spans two transcript lines
                f.write(json.dumps({"type": "assistant", "message": {"id": mid, "model": model, "usage": usage}}) + "\n")
        f.write("not json\n")
    return path


with tempfile.TemporaryDirectory() as d:
    path = write_transcript(d, "001-res", [
        ("m1", "x/y", {"input_tokens": 100, "cache_creation_input_tokens": 0, "cache_read_input_tokens": 0, "output_tokens": 10}),
        ("m2", "x/y", {"input_tokens": 20, "cache_read_input_tokens": 100, "output_tokens": 5}),
    ])
    assert cw_usage.find_transcript("001-res", projects=d) == path
    assert cw_usage.find_transcript("001-re", projects=d) is None       # prefix of another id
    assert cw_usage.find_transcript("001-res-r1", projects=d) is None   # a retry is another worker
    model, tot = cw_usage.sum_usage(path)
    assert model == "x/y"
    assert tot == {"input": 120, "cache_read": 100, "output": 15}, tot  # duplicate lines counted once
    usd = cw_usage.cost(tot, {"prompt": "0.000001", "completion": "0.000002", "input_cache_read": "0.0000001"})
    assert abs(usd - (120e-6 + 100e-7 + 30e-6)) < 1e-12, usd
    usd = cw_usage.cost(tot, {"prompt": "0.000001", "completion": "0.000002"})  # no cache price
    assert abs(usd - (220e-6 + 30e-6)) < 1e-12, usd

# missing transcript -> NA row (Review Focus 5)
cw_usage.PROJECTS = tempfile.mkdtemp()
out = io.StringIO()
with contextlib.redirect_stdout(out):
    rc = cw_usage.main(["cw_usage.py", "404-none"])
assert rc == 0 and out.getvalue() == "NA\t0\t0\t0\tNA\n", out.getvalue()
with contextlib.redirect_stderr(io.StringIO()):
    assert cw_usage.main(["cw_usage.py"]) == 2
print("ok")
```

- [ ] **Step 2: Run it to verify it fails**

Run: `python3 scripts/test_cw_usage.py`
Expected: FAIL with `ModuleNotFoundError: No module named 'cw_usage'`

- [ ] **Step 3: Write the implementation** `scripts/cw_usage.py`

```python
#!/usr/bin/env python3
"""cw_usage — token use and cost of one cw worker, as a workers.tsv fragment.

usage: cw_usage.py <task-id>
prints: model<TAB>input_tok<TAB>cache_read_tok<TAB>output_tok<TAB>cost_usd
"""
import glob, json, os, sys, time, urllib.request

PROJECTS = os.path.expanduser("~/.claude/projects")
MODELS_URL = "https://openrouter.ai/api/v1/models"


def find_transcript(task_id, projects=None, max_age_s=3 * 86400):
    """Newest recent transcript whose opening lines hold cw's first prompt for this task."""
    marker = f"You are cw-{task_id}, "
    now = time.time()
    paths = glob.glob(os.path.join(projects or PROJECTS, "*", "*.jsonl"))
    for path in sorted(paths, key=os.path.getmtime, reverse=True):
        if now - os.path.getmtime(path) > max_age_s:
            break  # newest first, so everything after is older
        with open(path, errors="replace") as f:
            head = "".join(next(f, "") for _ in range(50))
        if marker in head:
            return path
    return None


def sum_usage(path):
    """Sum usage over unique API responses (one response can span several transcript lines)."""
    seen, model = set(), None
    tot = {"input": 0, "cache_read": 0, "output": 0}
    with open(path, errors="replace") as f:
        for line in f:
            try:
                e = json.loads(line)
            except ValueError:
                continue
            m = e.get("message") or {}
            u = m.get("usage")
            if e.get("type") != "assistant" or not u or m.get("id") in seen:
                continue
            seen.add(m.get("id"))
            model = m.get("model") or model
            # ponytail: cache writes billed at the prompt price; off by <=25% only on models with a write premium
            tot["input"] += u.get("input_tokens", 0) + u.get("cache_creation_input_tokens", 0)
            tot["cache_read"] += u.get("cache_read_input_tokens", 0)
            tot["output"] += u.get("output_tokens", 0)
    return model, tot


def cost(tot, pricing):
    """USD from OpenRouter per-token prices (strings); cache reads fall back to the prompt price."""
    prompt = float(pricing["prompt"])
    read = float(pricing.get("input_cache_read") or prompt)
    return tot["input"] * prompt + tot["cache_read"] * read + tot["output"] * float(pricing["completion"])


def fetch_pricing(model):
    with urllib.request.urlopen(MODELS_URL, timeout=20) as resp:
        for m in json.load(resp)["data"]:
            if m["id"] == model:
                return m["pricing"]
    return None


def main(argv):
    if len(argv) != 2:
        print(__doc__.strip(), file=sys.stderr)
        return 2
    path = find_transcript(argv[1])
    if not path:
        print("NA\t0\t0\t0\tNA")  # worker never made an API call: log verdict=infra
        return 0
    model, tot = sum_usage(path)
    try:
        pricing = fetch_pricing(model) if model else None
    except (OSError, ValueError):
        pricing = None
    usd = f"{cost(tot, pricing):.4f}" if pricing else "NA"
    print(f"{model or 'NA'}\t{tot['input']}\t{tot['cache_read']}\t{tot['output']}\t{usd}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `chmod +x scripts/cw_usage.py && python3 scripts/test_cw_usage.py`
Expected: `ok`

- [ ] **Step 5: Commit**

```bash
git add plugins/driver-seat/skills/driver-seat/scripts/cw_usage.py plugins/driver-seat/skills/driver-seat/scripts/test_cw_usage.py
git commit -m "Add cw_usage: token use and cost of a cw worker"
```

---

### Task 3: `cw` launcher and `test-cw.sh`

**Files:**
- Create: `plugins/driver-seat/skills/driver-seat/scripts/cw`
- Test: `plugins/driver-seat/skills/driver-seat/scripts/test-cw.sh`

**Interfaces:**
- Consumes: Task 1's decision table (apply its edits to Step 3's code first); task files written by the orchestrator (Task 4).
- Produces: `cw --check` (exit 0 = enabled, 1 = off); `cw <research|chore> <task-id> <orchestrator-name>` → prints the tmux pane id (e.g. `%12`), exit 0; exit 2 on bad input; exit 1 when the worker fails to start (pane killed, chore branch/worktree removed). Worker first prompt starts `You are cw-<task-id>, ` (Task 2 depends on this). `CW_DRY_RUN=1`: launch mode validates and prints `repo=<main repo>`; `--run` mode prints the claude command, one argument per line.

All paths below are relative to `plugins/driver-seat/skills/driver-seat/`.

- [ ] **Step 1: Write the failing test** `scripts/test-cw.sh`

```zsh
#!/bin/zsh
# test-cw.sh — checks for cw. Offline by default (free: no tmux, no claude).
#   --live  also runs one real research and one real chore worker (costs cents). Needs tmux,
#           CW_OPENROUTER_API_KEY, and the current directory inside a folder Claude Code trusts
#           (or CW_TEST_PARENT pointing at one).
here=${0:A:h}
cw=$here/cw
fails=0 owned=0 nl=$'\n'
check() { if eval "$2"; then print -- "ok   $1"; else print -- "FAIL $1"; (( fails++ )); fi }
st() { "$@" >/dev/null 2>&1; print $? }
z() { CW_DRY_RUN=1 CW_OPENROUTER_API_KEY=${CW_OPENROUTER_API_KEY:-dummy} zsh -f $cw "$@" }

live=0; [[ ${1:-} == --live ]] && live=1
base=${CW_TEST_PARENT:-$TMPDIR}; (( live )) && base=${CW_TEST_PARENT:-$PWD}
tmp=$(mktemp -d ${base%/}/cw-test.XXXXXX)
cleanup() { (( owned )) && tmux kill-session -t cw 2>/dev/null; rm -rf $tmp }
trap cleanup EXIT

repo=$tmp/repo
git init -q $repo && git -C $repo commit -q --allow-empty -m init
mkdir -p $repo/.driver-seat/tasks $repo/sub
print -l -- '---' 'job: research' '---' \
  '# What is the latest tmux release? Cite its GitHub release page.' \
  '## Done when' '- the result names the version and links the release page' \
  > $repo/.driver-seat/tasks/001-res.md
print -l -- '---' 'job: chore' 'test: true   # trivial test command' '---' \
  '# Append the line "<!-- cw test -->" to README.md (create it if missing), then git add and commit it.' \
  'test: this-line-is-body-not-frontmatter' \
  '## Done when' '- README.md ends with that line and the change is committed' \
  > $repo/.driver-seat/tasks/002-chore.md
cd $repo
real=$(pwd -P)

check "no args exits 2"                 '[[ $(st z) == 2 ]]'
check "unknown job exits 2"             '[[ $(st z deploy 001-res boss) == 2 ]]'
check "unsafe task id exits 2"          '[[ $(st z research "1 bad/ID" boss) == 2 ]]'
check "missing task file exits 2"       '[[ $(st z research 009-nope boss) == 2 ]]'
check "--check is off without key"      '[[ $(st env -u CW_OPENROUTER_API_KEY zsh -f $cw --check) == 1 ]]'
check "--check is on with key"          '[[ $(st env CW_OPENROUTER_API_KEY=k zsh -f $cw --check) == 0 ]]'
check "launch without key exits 2"      '[[ $(st env -u CW_OPENROUTER_API_KEY CW_DRY_RUN=1 zsh -f $cw research 001-res boss) == 2 ]]'
check "research launch validates"       '[[ $(z research 001-res boss) == "repo=$real" ]]'
check "works from a subdirectory"       '[[ $(cd sub && z research 001-res boss) == "repo=$real" ]]'
git worktree add -q -b side $tmp/other-wt
check "works from inside a worktree"    '[[ $(cd $tmp/other-wt && z research 001-res boss) == "repo=$real" ]]'
check "outside a repo exits 2"          '[[ $(cd $tmp && st z research 001-res boss) == 2 ]]'
git branch -q cw/002-chore
check "existing chore branch exits 2"   '[[ $(st z chore 002-chore boss) == 2 ]]'
git branch -q -D cw/002-chore
check "chore launch validates"          '[[ $(z chore 002-chore boss) == "repo=$real" ]]'
chore=$(z --run chore 002-chore boss $real)
research=$(z --run research 001-res boss $real)
check "chore allows its test command"   '[[ $chore == *"Bash(true:*)"* ]]'
check "body test: line is ignored"      '[[ -n $chore && $chore != *this-line-is-body* ]]'
check "research cannot git commit"      '[[ -n $research && $research != *"git commit"* ]]'
check "lean flags present"              '[[ $chore == *"${nl}--bare${nl}--strict-mcp-config${nl}"* ]]'
check "prompt follows permission mode"  '[[ $chore == *"${nl}--permission-mode${nl}acceptEdits${nl}You are cw-002-chore, a chore worker for boss."* ]]'
check "result path in prompt"           '[[ $chore == *"Write your result to $real/.driver-seat/results/002-chore.md."* ]]'

if (( live )); then
  [[ -n ${CW_OPENROUTER_API_KEY:-} ]] || { print "live: CW_OPENROUTER_API_KEY is unset"; exit 1 }
  tmux has-session -t cw 2>/dev/null && { print "live: tmux session cw exists; close it first"; exit 1 }
  owned=1
  tmux new-session -d -s cw            # a cw session without a workers window (Review Focus 4)
  p1=$($cw research 001-res test-cw-nobody)
  p2=$($cw chore 002-chore test-cw-nobody)
  check "research pane opened"          '[[ $p1 == %* ]]'
  check "chore pane opened"             '[[ $p2 == %* ]]'
  check "both labelled in cw:workers"   '[[ $(tmux list-panes -t cw:workers -F "#{@cw}" | sort | paste -sd " " -) == "cw-001-res cw-002-chore" ]]'
  check ".driver-seat/ excluded"        'grep -qx ".driver-seat/" .git/info/exclude'
  for i in {1..60}; do
    [[ -s .driver-seat/results/001-res.md && -s .driver-seat/results/002-chore.md ]] && break
    sleep 5
  done
  check "research result has a link"    'grep -q "https://" .driver-seat/results/001-res.md'
  check "chore committed on its branch" '[[ $(git rev-list --count HEAD..cw/002-chore) -ge 1 ]]'
  tmux kill-pane -t $p1; tmux kill-pane -t $p2
  check "panes closed"                  '! tmux list-panes -a -F "#{pane_id}" | grep -qxE "$p1|$p2"'
fi

(( fails == 0 )) && print "all passed" || { print "$fails failed"; exit 1 }
```

- [ ] **Step 2: Run it to verify it fails**

Run: `zsh scripts/test-cw.sh`
Expected: every line `FAIL …` (no `cw` yet), last line `19 failed`, exit 1.

- [ ] **Step 3: Write the implementation** `scripts/cw` (apply Task 1's decision-table edits here)

```zsh
#!/bin/zsh
# cw — run one driver-seat research/chore task on a cheap pinned OpenRouter model,
# as an interactive Claude Code worker in a tiled tmux pane (session `cw`, window `workers`).
#
#   cw --check                         exit 0 if cw is enabled on this machine
#   cw <research|chore> <id> <boss>    launch worker cw-<id>; prints its tmux pane id
#   cw --run <job> <id> <boss> <repo>  (inside the pane) exec the worker
#
# CW_DRY_RUN=1 validates and prints instead of touching git/tmux/claude (used by test-cw.sh).
# ponytail: models are two variables, not a config file.
CW_RESEARCH_MODEL=${CW_RESEARCH_MODEL:-deepseek/deepseek-v4.1-flash}
CW_CHORE_MODEL=${CW_CHORE_MODEL:-deepseek/deepseek-v4.1-flash}

die() { print -u2 -- "cw: $1"; exit ${2:-2} }

[[ $1 == --check ]] && { [[ -n $CW_OPENROUTER_API_KEY ]]; exit }

if [[ $1 == --run ]]; then
  (( $# == 5 )) || die "usage: cw --run <job> <task-id> <orchestrator-name> <repo>"
  mode=run job=$2 id=$3 boss=$4 repo=$5
else
  (( $# == 3 )) || die "usage: cw <research|chore> <task-id> <orchestrator-name>"
  mode=launch job=$1 id=$2 boss=$3
  # the common dir is the main repo's .git, so this works from a subdir or a chore worktree too
  repo=$(git rev-parse --path-format=absolute --git-common-dir 2>/dev/null) || die "not inside a git repo"
  repo=${repo:h}
fi

[[ $job == (research|chore) ]] || die "job must be research or chore, got '$job'"
[[ $id =~ '^[0-9]{3}-[a-z0-9-]+$' ]] || die "task id must look like 012-slug, got '$id'"
[[ -n $CW_OPENROUTER_API_KEY ]] || die "CW_OPENROUTER_API_KEY unset: cw is off on this machine"
ds=$repo/.driver-seat
task=$ds/tasks/$id.md
[[ -f $task ]] || die "missing task file $task"

if [[ $job == research ]]; then
  model=$CW_RESEARCH_MODEL dir=$repo
  tools=(Read Grep Glob Write Edit WebFetch WebSearch 'Bash(curl:*)' ListAgents SendMessage)
else
  model=$CW_CHORE_MODEL dir=$ds/wt/$id
  tools=(Read Grep Glob Write Edit 'Bash(git status:*)' 'Bash(git diff:*)' 'Bash(git add:*)' 'Bash(git commit:*)' ListAgents SendMessage)
  # `test:` from the frontmatter only, trailing comment dropped
  test_cmd=$(awk '/^---$/ {n++; next} n > 1 {exit} n == 1 && sub(/^test:[ \t]*/, "") {sub(/[ \t]+#.*$/, ""); print; exit}' $task)
  [[ -n $test_cmd ]] && tools+=("Bash($test_cmd:*)")
fi

if [[ $mode == run ]]; then
  prompt="You are cw-$id, a $job worker for $boss.
Read $task and do exactly that task.
Scratch files go in $ds/tmp/ only.
Write your result to $ds/results/$id.md.
If blocked, SendMessage to $boss: \"blocked $id: <question>\" and wait.
When done, SendMessage to $boss: \"done $id\" plus a summary of at most 5 lines."
  export ANTHROPIC_BASE_URL=https://openrouter.ai/api ANTHROPIC_AUTH_TOKEN=$CW_OPENROUTER_API_KEY ANTHROPIC_API_KEY=
  export ANTHROPIC_DEFAULT_OPUS_MODEL=$model ANTHROPIC_DEFAULT_SONNET_MODEL=$model
  export ANTHROPIC_DEFAULT_HAIKU_MODEL=$model CLAUDE_CODE_SUBAGENT_MODEL=$model
  # --permission-mode stays last: --allowedTools and --add-dir are variadic and would swallow the prompt
  cmd=(claude -n cw-$id --model sonnet --bare --strict-mcp-config
       --allowedTools ${(j:,:)tools} --add-dir $ds --permission-mode acceptEdits $prompt)
  [[ -n $CW_DRY_RUN ]] && { print -l -- $cmd; exit 0 }
  exec $cmd
fi

if [[ $job == chore ]]; then
  git -C $repo show-ref --quiet --verify refs/heads/cw/$id && die "branch cw/$id already exists"
  [[ -e $dir ]] && die "$dir already exists"
fi
[[ -n $CW_DRY_RUN ]] && { print -- "repo=$repo"; exit 0 }

mkdir -p $ds/results $ds/tmp $repo/.git/info
grep -qx '.driver-seat/' $repo/.git/info/exclude 2>/dev/null || print '.driver-seat/' >> $repo/.git/info/exclude
[[ $job == chore ]] && { git -C $repo worktree add -q -b cw/$id $dir || die "git worktree add failed" 1 }

# `exec` twice (shell → cw → claude) keeps pane_pid == claude's pid for the ready check
run="exec ${(q)${0:A}} --run $job $id ${(q)boss} ${(q)repo}"
if ! tmux has-session -t cw 2>/dev/null; then
  pane=$(tmux new-session -d -s cw -n workers -x 200 -y 50 -c $dir -P -F '#{pane_id}' $run)
elif ! tmux list-windows -t cw -F '#W' | grep -qx workers; then
  pane=$(tmux new-window -t cw: -n workers -c $dir -P -F '#{pane_id}' $run)
else
  pane=$(tmux split-window -d -t cw:workers -c $dir -P -F '#{pane_id}' $run)
fi
[[ -n $pane ]] || die "tmux could not open a pane" 1
tmux set -p -t $pane @cw cw-$id \; set -t cw mouse on \; \
  set -w -t cw:workers pane-border-status top \; set -w -t cw:workers pane-border-format ' #{@cw} ' \; \
  set -w -t cw:workers remain-on-exit on \; select-layout -t cw:workers tiled

pid=$(tmux display -p -t $pane '#{pane_pid}')
clean=0
for i in {1..30}; do
  sleep 1
  screen=$(tmux capture-pane -p -t $pane)
  [[ $screen == *("trust this folder"|"Enter to continue")* ]] && break
  [[ $(tmux display -p -t $pane '#{pane_dead}') == 1 ]] && break
  # ponytail: Claude Code names its messaging socket after its pid (checked in Phase 0)
  [[ -S /tmp/cc-socks/$pid.sock ]] && (( ++clean >= 2 )) && { print -- $pane; exit 0 }
done
print -u2 -- $screen
tmux kill-pane -t $pane
[[ $job == chore ]] && git -C $repo worktree remove --force $dir && git -C $repo branch -q -D cw/$id
die "worker cw-$id did not start cleanly (dialog, exit, or 30 s timeout)" 1
```

- [ ] **Step 4: Run the offline test to verify it passes**

Run: `chmod +x scripts/cw scripts/test-cw.sh && zsh scripts/test-cw.sh`
Expected: 19 `ok` lines, then `all passed`.

- [ ] **Step 5: Run the live test**

Run (from a trusted folder, with no `cw` tmux session open): `cd ~/Apps/claude-skills && zsh plugins/driver-seat/skills/driver-seat/scripts/test-cw.sh --live`
Run it with a 10-minute tool timeout (or in the background): it takes up to 5 minutes.
Expected: 26 `ok` lines, then `all passed`. Watch it in another split with `tmux attach -t cw` while it runs. If a worker fails to start, `cw`'s stderr shows the pane capture — match it against Task 1's decision table.

- [ ] **Step 6: Commit**

```bash
git add plugins/driver-seat/skills/driver-seat/scripts/cw plugins/driver-seat/skills/driver-seat/scripts/test-cw.sh
git commit -m "Add cw: launch cheap driver-seat workers in tmux"
```

---

### Task 4: Wire `cw` into driver-seat

**Files:**
- Modify: `plugins/driver-seat/skills/driver-seat/SKILL.md` (frontmatter; **On entry**; **Research**; **Chores**; **Keep the machine small**; new section before **Review cycle**)
- Modify: `README.md:26-34` (driver-seat section)
- Modify: `plugins/driver-seat/.claude-plugin/plugin.json:5` (version)
- Outside repo: `~/.claude/skills/driver-seat` → symlink to the repo copy

**Interfaces:**
- Consumes: `cw` CLI and pane-id output (Task 3); `cw_usage.py` output columns (Task 2).
- Produces: the orchestrator behaviour described in the spec's **Task flow**.

- [ ] **Step 1: Make the repo copy the live skill**

```zsh
diff ~/.claude/skills/driver-seat/SKILL.md ~/Apps/claude-skills/plugins/driver-seat/skills/driver-seat/SKILL.md && \
mv ~/.claude/skills/driver-seat ~/.claude/skills/driver-seat.bak && \
ln -s ~/Apps/claude-skills/plugins/driver-seat/skills/driver-seat ~/.claude/skills/driver-seat && \
readlink ~/.claude/skills/driver-seat
```

Expected: no diff output, then the repo path. Remove `~/.claude/skills/driver-seat.bak` only after Step 7 passes. Note: the live skill now follows whatever branch the repo has checked out.

- [ ] **Step 2: Frontmatter — let the skill run its scripts without prompts**

In `SKILL.md` replace:

```
disable-model-invocation: true
---
```

with:

```
disable-model-invocation: true
allowed-tools: Bash(${CLAUDE_SKILL_DIR}/scripts/cw *) Bash(${CLAUDE_SKILL_DIR}/scripts/cw_usage.py *) Bash(tmux kill-pane *) Bash(tmux list-panes *)
---
```

- [ ] **Step 3: Route research, chores, and small-machine guidance**

Replace:

```
- **Real questions** → invoke the `research` skill. It searches, reads primary sources, cites with quotes, and archives to `~/research/`.
```

with:

```
- **Real questions** → when `cw` is enabled, dispatch a `cw research` worker (see **Cheap workers**); otherwise invoke the `research` skill. Either way the answer arrives with quotes and is archived to `~/research/`.
```

Replace:

```
Every chore passes the review cycle before the driver sees it. Report: what changed, where, how many review rounds.
```

with:

```
Every chore passes the review cycle before the driver sees it. Report: what changed, where, how many review rounds.

When `cw` is enabled, chores run as `cw chore` workers in their own branch and worktree (see **Cheap workers**); the review cycle still applies.
```

Replace:

```
Run subagents on the smallest model that does the job:
```

with:

```
When `cw` is enabled, research and chores go to off-plan `cw` workers first. Run subagents on the smallest model that does the job:
```

- [ ] **Step 4: On entry — reconcile workers after a restart**

Replace:

```
2. Otherwise ask what we're working on and go to **Planning**.
```

with:

```
2. Otherwise ask what we're working on and go to **Planning**.
3. If `cw` is enabled (see **Cheap workers**), reconcile workers. A file in `.driver-seat/results/` with no row in `.driver-seat/workers.tsv` is uncollected: collect it. A pane in `tmux list-panes -t cw:workers -F '#{pane_id} #{@cw}'` with no result is still running or stuck: ask the driver whether to wait or kill it. Your session name may have changed since dispatch, so workers' messages to the old name are lost; the files are the truth.
```

- [ ] **Step 5: Add the Cheap workers section**

Replace:

```
## Review cycle
```

with:

````
## Cheap workers (`cw`)

Research and chores can run off-plan on a cheap pinned OpenRouter model, each as a fresh Claude Code session in a tmux pane that reports back by message. Once per session run `${CLAUDE_SKILL_DIR}/scripts/cw --check`: exit 0 means enabled; anything else means skip this section and use plan-side subagents as before.

**Dispatch.**
1. Write `.driver-seat/tasks/NNN-slug.md` from the template below. The worker never sees this conversation: put every fact it needs under **Context**.
2. Run `${CLAUDE_SKILL_DIR}/scripts/cw <research|chore> NNN-slug <your session name>`. Your name is the first line of `ListAgents`. Keep the pane id it prints. Exit 1 means the worker didn't start: log verdict `infra`, relaunch once, then do the task plan-side (see **Outcome**).
3. `SendMessage(to: "cw-NNN-slug", notify_when_idle: true)` with no message, as the backstop if the worker never reports.
4. Tell the driver in one line that worker `cw-NNN-slug` is running and `tmux new -A -s cw` shows it.

```markdown
---
job: research | chore
todo: NNN-slug          # the todo this serves, if any
test: <command>         # chores only: the test command the worker may run
---
# <one-line task>
## Context
<everything the worker needs>
## Done when
- <checkable condition>
- research: result uses the research skill's output format (answer, what the docs say, for your case, sources with quotes)
- chore: result lists what changed, the test command and its output, and the commit hash on cw/NNN-slug
## Previous review findings
<retries only>
```

Research tasks add to **Context**: "Follow the method and output format in `~/.agents/skills/research/SKILL.md`; skip its archive step."

**While it runs.** `blocked NNN-slug: …` → answer by `SendMessage` to `cw-NNN-slug`, or ask the driver with AskUserQuestion when it's their decision. Don't poll: the `done` message or the idle notice wakes you. An idle notice with no result file, or a subscription that expired, means the worker is stuck: look at the pane, kill it, verdict `fail`.

**Collect.** On `done` (or the idle notice):
1. `${CLAUDE_SKILL_DIR}/scripts/cw_usage.py NNN-slug` gives `model, input_tok, cache_read_tok, output_tok, cost_usd`.
2. `tmux kill-pane -t <pane id>`, unless the driver said "keep cw-NNN-slug".
3. Review, plan-side:
   - research: re-fetch the source of every load-bearing quote in `results/NNN-slug.md` and confirm the quoted line exists.
   - chore: `git diff <base>...cw/NNN-slug` through the chore reviewer from **Review cycle**.

**Outcome.**
- pass: research is copied to `~/research/YYYY-MM-DD-slug.md`, rendered with the research skill's `archive.py`, and briefed. A chore is shown as a diff summary; the driver merges (`git merge cw/NNN-slug`, then `git worktree remove .driver-seat/wt/NNN-slug`).
- first fail: copy the task to `NNN-slug-r1.md`, add the findings under **Previous review findings**, and run `cw` with id `NNN-slug-r1`.
- second fail: escalate. Research → the `research` skill (plan-side Sonnet). Chore → an Agent on `sonnet` with `isolation: "worktree"`, given the task file.

**Log.** One row per attempt in `.driver-seat/workers.tsv`; create it with this header if missing:

```
date	task_id	job	attempt	model	input_tok	cache_read_tok	output_tok	cost_usd	verdict	escalated	shadow
```

The five columns from `model` to `cost_usd` are `cw_usage.py`'s output. `verdict` is `pass`, `fail` or `infra`; `escalated` is `1` on the row of a task finished plan-side; `shadow` is `agree`, `disagree` or `-`.

**Shadow run.** While fewer than 5 research rows have a shadow value, also run the `research` skill on the same question and compare: same answer, receipts valid? Record `agree` or `disagree`.

**Is it working?** After 10 tasks of a job: if 20% or more of them were escalated (`infra` excluded), tell the driver and suggest a different model via `CW_RESEARCH_MODEL` or `CW_CHORE_MODEL`.

## Review cycle
````

- [ ] **Step 6: README and version**

In `README.md`, after line 34 (`hand it. Turn on with \`/driver-seat\`; off with "stop driver-seat".`), insert:

```markdown

**Cheap workers (optional).** Research and chores can run off your Claude plan on a
cheap OpenRouter model: each task gets a fresh Claude Code worker in a tiled tmux
pane that reports back by cross-session message, and the plan-side navigator reviews
everything before you see it. Setup: create a dedicated OpenRouter key with a credit
limit, add `export CW_OPENROUTER_API_KEY=...` to `~/.zshenv`, and install tmux. To
watch and talk to workers, split your terminal and run `tmux new -A -s cw`. Without
the key, driver-seat runs exactly as before. Design:
`docs/superpowers/specs/2026-10-03-driver-seat-cheap-workers-design.md`.
```

In `plugins/driver-seat/.claude-plugin/plugin.json` change `"version": "1.0.0"` to `"version": "1.1.0"`.

- [ ] **Step 7: Verify**

Run:

```zsh
cd ~/Apps/claude-skills
claude plugin validate plugins/driver-seat && claude plugin validate .
python3 plugins/driver-seat/skills/driver-seat/scripts/test_cw_usage.py
zsh plugins/driver-seat/skills/driver-seat/scripts/test-cw.sh
grep -c 'cw' plugins/driver-seat/skills/driver-seat/SKILL.md
```

Expected: both validations pass (warnings allowed, as before); `ok`; `all passed`; a count above 15.

- [ ] **Step 8: Commit**

```bash
git add plugins/driver-seat/skills/driver-seat/SKILL.md README.md plugins/driver-seat/.claude-plugin/plugin.json
git commit -m "driver-seat: dispatch research and chores to cheap cw workers"
```

- [ ] **Step 9 (driver, manual): First real use**

In a repo with `.driver-seat/`, start a new Claude Code session, run `/driver-seat`, ask one real research question, and watch it in a `tmux new -A -s cw` split. Check that a `workers.tsv` row appears. Then delete `~/.claude/skills/driver-seat.bak`.

---

## After rollout (not tasks)

- The shadow run covers the first 5 research tasks automatically.
- After 10 tasks per job, read `.driver-seat/workers.tsv` with the driver and act on the 20% rule.
