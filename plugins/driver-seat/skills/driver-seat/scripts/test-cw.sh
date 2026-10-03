#!/bin/zsh
# test-cw.sh — checks for cw. Offline by default (free: no tmux, no claude).
#   --live  also runs one real research and one real chore worker (costs cents). Needs tmux,
#           CW_OPENROUTER_API_KEY, and CW_TEST_REPO (default ~/.cache/cw-test-repo) trusted once
#           in Claude Code: Claude Code never pre-trusts a new repo, so live runs reuse this one.
here=${0:A:h}
cw=$here/cw
fails=0 owned=0 nl=$'\n'
check() { if eval "$2"; then print -- "ok   $1"; else print -- "FAIL $1"; (( fails++ )); fi }
st() { "$@" >/dev/null 2>&1; print $? }
z() { CW_DRY_RUN=1 CW_OPENROUTER_API_KEY=${CW_OPENROUTER_API_KEY:-dummy} zsh -f $cw "$@" }

live=0; [[ ${1:-} == --live ]] && live=1
L=${CW_TEST_REPO:-$HOME/.cache/cw-test-repo}
# the live run wipes $L/.driver-seat, so refuse a repo that holds real driver-seat state
(( live )) && [[ -e $L/.driver-seat/todos || -e $L/.driver-seat/workers.tsv ]] && {
  print "live: $L has real driver-seat state (todos/ or workers.tsv); refusing"; exit 1 }
tmp=$(mktemp -d ${TMPDIR%/}/cw-test.XXXXXX)
cleanup() { (( owned )) && tmux kill-session -t cw 2>/dev/null; rm -rf $tmp }
trap cleanup EXIT

repo=$tmp/repo
git init -q $repo && git -C $repo commit -q --allow-empty -m init
mkdir -p $repo/.driver-seat/tasks $repo/sub
print -l -- '---' 'job: research' '---' \
  '# What is the latest tmux release? Cite its GitHub release page.' \
  '## Context' 'Follow the method and output format in ~/.agents/skills/research/SKILL.md; write the answer to your result file, not to ~/research/.' \
  '## Done when' '- the result names the version and links the release page' \
  > $repo/.driver-seat/tasks/001-res.md
print -l -- '---' 'job: chore' 'test: true   # trivial test command' '---' \
  '# Append the line "<!-- cw test -->" to README.md (create it if missing), then git add and commit it.' \
  'test: this-line-is-body-not-frontmatter' \
  '## Done when' '- README.md ends with that line and the change is committed' \
  > $repo/.driver-seat/tasks/002-chore.md
print x > "$repo/.driver-seat/tasks/001 Bad.md"   # so an id check, not a missing file, must reject it
cd $repo
real=$(pwd -P)
head=$(git rev-parse HEAD)

check "no args exits 2"                 '[[ $(st z) == 2 ]]'
check "unknown job exits 2"             '[[ $(st z deploy 001-res boss) == 2 ]]'
check "unsafe task id exits 2"          '[[ $(st z research "001 Bad" boss) == 2 ]]'
check "uppercase task id exits 2"       '[[ $(st z research 001-RES boss) == 2 ]]'
check "missing task file exits 2"       '[[ $(st z research 009-nope boss) == 2 ]]'
check "--check is off without key"      '[[ $(st env -u CW_OPENROUTER_API_KEY zsh -f $cw --check) == 1 ]]'
check "--check is off without tmux"     '[[ $(st env PATH=/usr/bin:/bin CW_OPENROUTER_API_KEY=k zsh -f $cw --check) == 1 ]]'
check "--check is on with key and tmux" '[[ $(st env CW_OPENROUTER_API_KEY=k zsh -f $cw --check) == 0 ]]'
check "launch without key exits 2"      '[[ $(st env -u CW_OPENROUTER_API_KEY CW_DRY_RUN=1 zsh -f $cw research 001-res boss) == 2 ]]'
check "research launch validates"       '[[ $(z research 001-res boss) == "repo=$real${nl}"* ]]'
check "research runs in .driver-seat"   '[[ $(z research 001-res boss) == *"${nl}dir=$real/.driver-seat${nl}"* ]]'
check "works from a subdirectory"       '[[ $(cd sub && z research 001-res boss) == "repo=$real${nl}"* ]]'
git worktree add -q -b side $tmp/other-wt
git -C $tmp/other-wt commit -q --allow-empty -m side-only
mkdir -p $tmp/other-wt/.driver-seat && cp -R .driver-seat/tasks $tmp/other-wt/.driver-seat/
wt=$(cd $tmp/other-wt && pwd -P); wthead=$(git -C $wt rev-parse HEAD)
check "linked worktree is its own repo" '[[ $(cd $wt && z research 001-res boss) == "repo=$wt${nl}"* ]]'
check "chore branches from caller HEAD" '[[ $(cd $wt && z chore 002-chore boss) == *"${nl}base=$wthead${nl}"* ]]'
check "outside a repo exits 2"          '[[ $(cd $tmp && st z research 001-res boss) == 2 ]]'
git branch -q cw/002-chore
check "existing chore branch exits 2"   '[[ $(st z chore 002-chore boss) == 2 ]]'
git branch -q -D cw/002-chore
check "chore launch validates"          '[[ $(z chore 002-chore boss) == "repo=$real${nl}"* ]]'
check "model override is resolved at launch" '[[ $(CW_CHORE_MODEL=x/override z chore 002-chore boss) == *"${nl}model=x/override" ]]'
fake=$tmp/fake-bin; mkdir -p $fake; print -l '#!/bin/sh' 'exit 1' > $fake/tmux; chmod +x $fake/tmux
check "failed launch removes chore branch and worktree" \
  '[[ $(st env PATH=$fake:$PATH CW_OPENROUTER_API_KEY=k zsh -f $cw chore 002-chore boss) == 1 ]] && ! git show-ref -q --verify refs/heads/cw/002-chore && [[ ! -e .driver-seat/wt/002-chore ]]'
chore=$(z --run chore 002-chore boss $real m/chore)
research=$(z --run research 001-res boss $real m/res)
check "run mode uses the passed model"  '[[ $chore == "model=m/chore${nl}claude${nl}"* ]]'
check "chore allows its test command"   '[[ $chore == *"Bash(true:*)"* ]]'
check "body test: line is ignored"      '[[ -n $chore && $chore != *this-line-is-body* ]]'
check "research cannot git commit"      '[[ -n $research && $research != *"git commit"* ]]'
check "research cannot run curl"        '[[ -n $research && $research != *curl* ]]'
check "research denies the shell"       '[[ $research == *"${nl}--disallowedTools${nl}Bash${nl}"* && $research == *"You have no shell"* ]]'
check "chore keeps its shell"           '[[ -n $chore && $chore != *--disallowedTools* ]]'
check "research prompt marks repo read-only" '[[ $research == *"Repo under study: $real (read it, never edit it)."* ]]'
check "lean flags present"              '[[ $chore == *"${nl}--setting-sources${nl}project,local${nl}--strict-mcp-config${nl}"* ]]'
check "prompt follows permission mode"  '[[ $chore == *"${nl}--permission-mode${nl}acceptEdits${nl}You are cw-002-chore, a chore worker for boss."* ]]'
check "result path in prompt"           '[[ $chore == *"Write your result to $real/.driver-seat/results/002-chore.md."* ]]'

if (( live )); then
  [[ -n ${CW_OPENROUTER_API_KEY:-} ]] || { print "live: CW_OPENROUTER_API_KEY is unset"; exit 1 }
  tmux has-session -t cw 2>/dev/null && { print "live: tmux session cw exists; close it first"; exit 1 }
  [[ -d $L/.git ]] || { git init -q $L && git -C $L commit -q --allow-empty -m init }
  rm -rf $L/.driver-seat; git -C $L worktree prune; git -C $L branch -q -D cw/002-chore 2>/dev/null
  mkdir -p $L/.driver-seat/tasks && cp $repo/.driver-seat/tasks/00?-*.md $L/.driver-seat/tasks/
  cd $L
  owned=1
  tmux new-session -d -s cw            # a cw session without a workers window (Review Focus 4)
  p1=$($cw research 001-res test-cw-nobody)
  p2=$($cw chore 002-chore test-cw-nobody)
  [[ -z $p1$p2 ]] && print "live: no worker started; if the capture shows a trust dialog, trust $L once (cd $L && claude, pick 'Yes, I trust this folder', exit)"
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
  git worktree remove --force .driver-seat/wt/002-chore; git branch -q -D cw/002-chore; rm -rf .driver-seat
fi

(( fails == 0 )) && print "all passed" || { print "$fails failed"; exit 1 }
