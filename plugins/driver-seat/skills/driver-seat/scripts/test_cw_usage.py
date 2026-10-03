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
