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
