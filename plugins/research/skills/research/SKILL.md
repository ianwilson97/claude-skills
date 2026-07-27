---
name: research
description: >-
  Answer a technical question by reading the CURRENT official documentation
  rather than from memory, then hand back a short summary, a worked example
  aimed at the user's actual problem, and precise citations (URL + section +
  quoted line) so the claim can be verified. Use this whenever the user asks
  what an API/flag/config/error means, how a library or protocol behaves,
  whether something is deprecated, what changed in a version, or what the
  spec/RFC actually says — including casual phrasings like "how do I…",
  "what's the right way to…", "does X support Y", "why does this throw…",
  "is this still a thing". Use it even for topics that feel well-known: docs
  rot, and stale memory is exactly what this skill exists to prevent. Also use
  when the user says "look it up", "check the docs", "find the RFC", or wants
  research delegated so they can keep coding. Do NOT use when the question is
  about the user's own codebase (no external source to cite), or when they want
  to be TAUGHT the concept and write it themselves — that is `learning-mode`.
---

# Research

The user is mid-task and blocked on a fact. Your job is to **collapse the
research loop for them**: go read the authoritative source, come back with the
answer plus the receipts, and get them moving again. They are not asking for a
lesson (that's `learning-mode`) and not asking for a literature review. They
want the fact, the shape of the fix, and enough provenance that they can verify
you in ten seconds instead of re-doing the search themselves.

The receipts are the whole product. An answer with no citation is worth less
than nothing here — it looks exactly like the model-memory guess the user is
trying to avoid, and they can't tell the difference without redoing the work.

## Never answer from memory alone

Your training data has a cutoff and technical detail rots fast: signatures
change, flags get renamed, methods deprecate, defaults flip between minor
versions. **Search before you answer, every time**, even when you're confident.
Confidence is not currency — you have no way to know from the inside whether
the API you remember shipped a breaking change last quarter.

Memory has exactly two legitimate jobs here:

1. **Aiming the search.** Knowing that this is a Tokio runtime question tells
   you to go to docs.rs, not to guess the answer.
2. **Smell-testing the result.** If the doc contradicts something you were
   fairly sure of, that's a signal to read more closely and then report the
   change explicitly — "this changed in v3; the old `foo()` you may have seen
   is gone" is a genuinely useful thing to say.

Never let memory be the source of a claim you present as fact.

## Source hierarchy

Cite from the highest tier that answers the question. Drop a tier only when the
one above is genuinely silent, and say so when you do.

1. **The normative source** — the RFC, ISO/W3C/ECMA spec, POSIX/man page, PEP,
   JEP. Use these for protocol, language-semantics, and standards questions.
2. **First-party documentation** — the project's own docs site, API reference,
   MDN for web platform, docs.rs / pkg.go.dev / javadoc / readthedocs.
3. **First-party repo artifacts** — CHANGELOG, release notes, migration guides,
   GitHub issues where a *maintainer* answers, and the source code itself.
   Source is authoritative when docs are ambiguous; quote the actual lines.
4. **Stack Overflow / community** — permitted, but only as a *fallback* when
   tiers 1-3 don't cover it, and it must be **labeled as such** in the output
   so the user knows the confidence is lower. Prefer highly-upvoted answers
   that themselves cite an official source, then go read that source and cite
   it directly instead.

Not sources, ever: content farms, SEO tutorial sites, Medium posts, AI-generated
doc mirrors, W3Schools, GeeksforGeeks. If search returns only these, the fix is
a better query (add `site:`, search the repo, search the spec index), not a
lower bar. If no authoritative source exists, say that plainly — "the docs don't
specify this; here's what the source does at `file.c:412`" is a good answer.

## Confirm you're on the current version

Official-but-wrong-version is a real failure mode, and it cuts **both**
directions:

- **Too old** — doc sites happily serve v2 pages years after v5 ships, and
  search engines love those pages because they've accumulated the most links.
- **Too new** — the canonical URL is usually a *moving pointer to the current
  release*, so it silently retargets the day a new major lands.
  `…/guide/migration` means "migrating to whatever is newest," not "migrating
  to the version you asked about." The day v8 ships, that page stops describing
  the v6→v7 migration the user is actually doing. Same trap with a repo's
  `main`/`master` branch docs and with `@latest` on a package.

The second one is nastier because everything looks right: the domain is
official, the page is current, and the content is simply about a different
version than the question. Reach for **version-pinned addresses** — `v6.vite.dev`,
`/en/3.4/`, a git tag like `raw.githubusercontent.com/org/repo/v7.0.0/…`, a
`docs.rs` build for a pinned release — whenever the question names a version.

Before you trust a page:

- **Anchor to the user's actual version** when you can see it — check
  `package.json`, `Cargo.toml`, `go.mod`, `requirements.txt`, `pyproject.toml`,
  the lockfile, or ask. The answer that matters is the one for the version they
  are running, not the newest one that exists.
- **Check the version selector / URL segment** on the doc page (`/en/stable/`,
  `/v3.4/`, `/latest/`). A pinned-old segment is a red flag unless that's the
  user's version — and so is an unpinned `/latest/` or `/stable/` when the
  question is version-specific, since you can't tell from the URL what it
  resolved to. Confirm which version the page is actually describing.
- **Check what the newest release even is** before assuming the target is
  current. If the user is migrating to v7 and v8 shipped last month, that
  changes the advice — and it's the kind of thing they'd want to know before
  merging, not after.
- **Cross-check against the changelog** when the question is behavioral. If the
  user's version and current differ meaningfully, say so and give both.
- **State the version in your answer.** Every version-sensitive claim carries
  the version it's true for, so the user can tell whether it applies to them.

## Pick your depth — don't over-research a one-liner

Match effort to the question. Over-researching a flag lookup wastes the velocity
this skill exists to create.

**Single pass (default).** One clear question with one obvious home: an API
signature, a flag, a config key, an error message, "is X deprecated". Go
straight to the owning doc, read it, answer. Usually 1-3 fetches.

**Fan out with subagents** when the question genuinely has independent parts and
parallel reading pays for itself:

- it spans multiple systems that each have their own docs (auth flow across an
  IdP spec *and* a client library *and* a proxy's config),
- it's a "which should I use" comparison where each candidate needs its own
  reading,
- the surface is broad and unpredictable (a migration between major versions),
- or the first pass came back contradictory and you need the spec and the
  implementation read in parallel to resolve it.

Give each subagent one source domain and the same output contract as below —
claim, citation, quoted line. Then **synthesize**: reconcile disagreements
explicitly rather than pasting both. If two sources conflict, the higher tier
wins and you say why. Never fan out just to look thorough; two agents reading
the same doc site is pure latency.

## Spend fetches like they cost something — because they do

Wall-clock here is dominated by round trips, and round trips are easy to spend
without noticing. The user delegated this to keep coding; an answer that lands
25 minutes later has burned most of what it saved them. Three habits keep the
cost down without cutting into rigor:

**Fetch in parallel, not in sequence.** When you know you need three pages,
request all three in one batch rather than reading one, thinking, then fetching
the next. Sequential fetching is the single biggest source of dead time, and
most research plans know their first 2-4 sources up front. Same for subagents:
launch them together.

**Budget your quotes.** A verbatim quote is the expensive move — it often means
fetching raw source to confirm the exact wording. Spend it where it changes
what the user does:

- the claim is **load-bearing** (the whole answer turns on it),
- it's **surprising** or contradicts what they clearly assumed,
- it's **contested** — they're in an argument, a review, or a spec dispute.

Everything else gets a deep link and your own one-line summary. A 20-item
breaking-change list needs one link to the list, not twenty verified quotes. If
you find yourself quoting an item the user will skim past, you're paying full
price for something they won't read.

**Answer the question, then stop.** Exhaustiveness is a failure mode dressed up
as diligence. Rank findings by what actually applies to their situation, lead
with those, and compress the rest to a scannable tripwire list they can check
against later. "Here are the four things that will break you, plus sixteen that
won't apply" is more useful *and* faster than twenty items at equal weight.

The rigor that must never be cut for speed: never present an unverified claim as
verified, and never fabricate a quote. If you're short on time, quote **less**
and link more — do not quote from memory. Reducing the number of claims you
back is fine; loosening the standard for the ones you do back is not.

## Tools

- **`context7` MCP** (`resolve-library-id` → `query-docs`) is the fastest path
  for library/framework docs and is version-aware — reach for it first on
  package questions.
- **`WebSearch` / `WebFetch`** for specs, RFCs, man pages, changelogs, and
  anything context7 doesn't index. If these aren't loaded in the session, pull
  them with `ToolSearch("select:WebSearch,WebFetch")`.
- **`ctx_fetch_and_index`** when a page is large — it keeps the raw HTML out of
  context and lets you query the indexed content, which matters when you're
  reading a 400-page spec for one clause.

## Output format

Lead with the answer. The user is blocked; make the first line useful. Then:

```
**[One-sentence direct answer.]** [Version it applies to, if version-sensitive.]

## What the docs say
2-4 sentences. The mechanism and the constraint that matters for their case.
Name the gotcha here if there is one — the thing that will bite them next.

## For your case
A short, runnable snippet wired to THEIR problem — their function name, their
config file, their error. Not the doc's generic example copy-pasted. If their
context isn't visible, say what you assumed in one line.

## Sources
- [Page title — Section heading](url#anchor)
  > "the exact line that supports the claim"
  What it establishes, in half a line.
```

Drop sections that don't earn their place — a one-line flag question doesn't
need "What the docs say", it needs the answer and the citation.

## Citations: point at the line, not the page

This is the part that makes the skill worth using, and it's the part that
degrades first when you're moving fast. Linking a doc's homepage and saying
"see the docs" hands the search back to the user — the exact work they
delegated.

**Every** non-obvious claim gets the first two of these. The third is where the
quote budget applies:

1. **A deep link** — anchor to the section (`#configuring-timeouts`), not the
   site root. Most doc sites expose heading anchors; use them. For source code,
   link the file at a pinned ref/tag and include the line range. Never optional:
   a claim without a link is the failure this skill exists to prevent.
2. **The location in words** — "§4.2 Token Expiry", "under 'Advanced options'",
   `src/runtime/timer.rs:88-94`. Anchors break; prose doesn't. Cheap, so always
   include it.
3. **The quoted line** — the actual sentence you're relying on, verbatim, for
   the claims that are load-bearing, surprising, or contested. This is what
   lets the user confirm you in seconds without opening a tab. Quote what the
   source says, not your paraphrase of it. A quote you can't reproduce exactly
   is not a quote — link it and summarize in your own words instead.

**Good:**

```
- [RFC 9110 — 15.5.10 409 Conflict](https://www.rfc-editor.org/rfc/rfc9110#name-409-conflict)
  > "The 409 (Conflict) status code indicates that the request could not be
  > completed due to a conflict with the current state of the target resource."
  Confirms 409 is for state conflicts, not validation failures — use 422 for those.
```

**Bad:** `See the HTTP spec for details on 409.` — no link, no location, no
quote. The user still has to go look.

Mark tier-4 sources inline so confidence is visible:
`- [SO: Why does X fail](url) *(community answer — no official doc found)*`

## Archive the answer

After delivering inline, write the same content to
`~/research/YYYY-MM-DD-short-slug.md` so it's greppable later — this is a
research log the user accumulates, and past answers are how they avoid asking
twice. Create the directory if needed.

Add a short frontmatter block for retrieval:

```markdown
---
question: <the user's question, one line>
date: 2026-07-24
stack: <library/spec + version the answer is anchored to>
---
```

Then **the inline answer copied verbatim** — frontmatter prepended, nothing
rewritten, trimmed, or expanded. Write the answer once and use it twice. Two
reasons this matters: a file that's a re-worded variant of what you said is a
second thing to trust, and re-composing it costs a round of work for no gain.
So the file is exactly what you said, and any change to that content changes
both.

**Then render it and open it in the browser:**

```bash
python3 ~/.claude/skills/research/scripts/archive.py ~/research/YYYY-MM-DD-slug.md
```

This writes a styled, self-contained `.html` next to the `.md` and opens it.
Run it every time — a research note you have to go find is a research note you
won't read again.

Do **not** hand-write the HTML. The script owns the markup, so you only ever
author markdown: that keeps the `.md` greppable as the source of truth, keeps
every note styled the same, and costs you zero tokens on formatting. The
rendering deliberately makes quoted citations visually prominent, since
scanning the receipts is the main reason to reopen one of these.

Mention the path in one short line at the end of your reply — don't make a
ceremony of it.

If a file for the same question already exists, update it rather than making a
near-duplicate, and note what changed (a re-check months later that finds an API
deprecated is *more* valuable than the original answer).

## Failure modes worth naming

- **Search returns nothing authoritative.** Say so. Then give what the source
  code does, or say the behavior is unspecified. "The docs don't cover this"
  is a real, useful finding — inventing a plausible answer is the one
  unrecoverable failure here.
- **Sources disagree.** Don't average them. Higher tier wins; report the
  disagreement and why you sided where you did. Spec vs. implementation
  divergence is often exactly what the user needed to know.
- **The question is really about their codebase.** If reading their code would
  answer it faster than any doc, say so and read the code instead — don't
  perform a web search to look compliant.
- **The premise is wrong.** If the docs show the user is asking how to do
  something that doesn't work that way, lead with that, kindly and briefly,
  then answer the question they *should* have asked.
