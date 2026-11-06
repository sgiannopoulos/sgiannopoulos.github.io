#!/usr/bin/env python3
"""Copy every run's input and output from the logs repo into the post, for the run viewers in js/runs.js.

Run from the repo root: python3 scripts/make_runs.py <path to the logs repo>
Writes assets/runs/<exp>/<program>/ and assets/runs/manifest.js.

Files are copied byte for byte, with one exception for the malware sample (Experiments 4 and 5): its hex dump is left
out of the prompt (WITHHOLD_SAMPLE). The server address in the replies is shown as is; MASK_ADDRESS masks it again.

The script fails rather than publish a record that doesn't hold up. It checks each prompt against the hash in run.json,
each hex dump and patch against the binaries, each scored file against the reply it came from, and the numbers the post
quotes against the logs.

Only what the viewers show is copied: not the reasoning summaries, the run records or Experiment 1's executables.

Experiment 5 isn't in the logs repo. Its files come from the local OpenCode database when that exists, and otherwise the
copies already in assets/runs/exp5 are kept.
"""
import hashlib
import json
import os
import re
import shutil
import sqlite3
import sys
from pathlib import Path

if len(sys.argv) != 2:
    sys.exit("usage: python3 scripts/make_runs.py <path to the logs repo>")
LOGS = Path(sys.argv[1])
OUT = Path("blog/machine-code-programming/assets/runs")
OPENCODE_DB = Path.home() / ".local/share/opencode/opencode.db"
OPENCODE_SESSION = "ses_e4e9f7cddffe5dw08Kx00HCPVz"
THINKING = Path("blog/machine-code-programming/assets/deepseek-thinking.txt")

WITHHOLD_SAMPLE = True
MASK_ADDRESS = False
MASK = "[address withheld]"
HEX_ROW = re.compile(r"^[0-9a-f]{8}: ", re.M)
IPV4 = re.compile(r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b")

MINISTAT_NOTE = "This binary's hex dump stays under the licenses of ministat and musl."
SAMPLE_NOTE = ""

# The numbers the post quotes, checked against the logs: output tokens, seconds, and for Exps 2 and 3 tests and bytes.
EXPECTED = {
    ("exp2", "prog1"): (3440, 93, 18, 74),
    ("exp2", "prog2"): (9324, 201, 28, 544),
    ("exp2", "prog3"): (6859, 140, 31, 379),
    ("exp3", "prog1"): (6035, 124, 18, 391),
    ("exp3", "prog2"): (22812, 474, 28, 4144),
    ("exp3", "prog3"): (25069, 504, 31, 3584),
}

EXPERIMENTS = {
    "exp1": {"logs": "exp1_understand", "kind": "read", "runs": [
        ("prog1", "wordcount", "wordcount", None),
        ("prog2", "aes", "AES tool", None),
        ("prog3", "ledger", "Bank ledger", None),
        ("prog5", "ministat", "ministat", MINISTAT_NOTE),
    ]},
    "exp2": {"logs": "exp2_patch", "kind": "patch", "runs": [
        ("prog1", "wordcount", "wordcount + longest line", None),
        ("prog2", "aes", "AES + dec", None),
        ("prog3", "ledger", "Ledger + transfer", None),
    ]},
    "exp3": {"logs": "exp3_construct", "kind": "write", "runs": [
        ("prog1", "wordcount", "wordcount + longest line", None),
        ("prog2", "aes", "AES + dec", None),
        ("prog3", "ledger", "Ledger + transfer", None),
    ]},
    # The prog4 run is logged under Experiment 1, and the post reports it as Experiment 4.
    "exp4": {"logs": "exp1_understand", "kind": "read", "runs": [
        ("prog4", "sample", "Windows sample", SAMPLE_NOTE),
    ]},
}


def redact(text):
    """Mask every dotted address in the text, and the separate pieces it is built from."""
    addresses = set(IPV4.findall(text))
    text = IPV4.sub(MASK, text)
    for address in addresses:
        octets = address.split(".")
        pieces = [o + "." for o in octets[:-1]] + octets[-1:]
        text = re.sub(r"^" + r"\n".join(re.escape(p) for p in pieces) + r"$", MASK, text, flags=re.M)
        for piece in pieces:
            text = text.replace(f'"{piece}"', f'"{MASK}"')
    assert not IPV4.search(text)
    for address in addresses:
        for octet in address.split(".")[:-1]:
            assert not re.search(rf"(?<![\w.]){octet}\.(?!\d)", text), "an address fragment is still in the text"
    return text


def split_prompt(prompt):
    """The text before the hex dump, and the rows of the dump."""
    match = HEX_ROW.search(prompt)
    if not match:
        return prompt, []
    head, dump = prompt[:match.start()], prompt[match.start():]
    rows = dump.rstrip("\n").split("\n")
    assert all(HEX_ROW.match(row) for row in rows), "text follows the hex dump"
    return head, rows


def decode_rows(rows):
    return bytes.fromhex("".join(row.split(": ", 1)[1] for row in rows))


def last_block(reply, tag):
    blocks = re.findall(rf"```{tag}\n(.*?)```", reply, flags=re.S)
    assert blocks, f"no {tag} block in the reply"
    return blocks[-1]


def copy_text(text, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


def copy_file(src, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(src, path)


def tests_summary(tests):
    assert tests["passed"] == sum(r["pass"] for r in tests["results"]) and tests["total"] == len(tests["results"])
    return {"passed": tests["passed"], "total": tests["total"], "byTag": tests["by_tag"]}


def build_run(exp, config, prog, slug, label, note):
    logs = LOGS / config["logs"]
    run_dir = logs / "runs" / prog
    dest = OUT / exp / slug
    rel = f"{exp}/{slug}"
    kind = config["kind"]

    prompt_raw = (run_dir / "prompt.txt").read_bytes()
    run = json.loads((run_dir / "run.json").read_text())
    assert hashlib.sha256(prompt_raw).hexdigest() == run["prompt_sha256"], f"{exp} {prog}: prompt doesn't match run.json"
    assert run["audit"]["tool_free"] and run["audit"]["lockdown_ok"], f"{exp} {prog}: failed the tool audit"

    prompt = prompt_raw.decode()
    reply = (run_dir / "answer.md").read_text()
    head, rows = split_prompt(prompt)
    withheld = WITHHOLD_SAMPLE and prog == "prog4"
    if rows and not withheld:
        size = (logs / "binaries" / f"{prog}.bin").stat().st_size
        assert decode_rows(rows) == (logs / "binaries" / f"{prog}.bin").read_bytes(), f"{exp} {prog}: dump != binary"

    entry = {
        "label": label, "note": note, "dir": rel,
        "model": run["model"], "effort": run["effort"],
        "usage": {"input": run["audit"]["usage"]["input_tokens"], "output": run["audit"]["usage"]["output_tokens"],
                  "reasoning": run["audit"]["usage"]["reasoning_output_tokens"]},
        "seconds": round(run["wall_s"]),
        "promptBytes": len(prompt_raw),
        "promptHead": head,
        "hexRows": len(rows),
        "files": {"prompt": "prompt.txt", "reply": "reply.md"},
    }

    if withheld:
        size = len(decode_rows(rows))
        withheld_line = f"[Hex dump withheld: {len(rows)} rows, {size:,} bytes]\n"
        copy_text(head + withheld_line, dest / "prompt.txt")
        copy_text(redact(reply) if MASK_ADDRESS else reply, dest / "reply.md")
        entry.update(promptHead=head + withheld_line, hexRows=0, hexWithheld=True, inputBytes=size)
    else:
        copy_text(prompt, dest / "prompt.txt")
        copy_text(reply, dest / "reply.md")

    if kind == "read" and not withheld:
        entry["inputBytes"] = size

    if kind == "patch":
        original = (logs / "binaries" / f"{prog}.bin").read_bytes()
        patched = (logs / "binaries" / f"{prog}_patched.bin").read_bytes()
        patch = json.loads((logs / "binaries" / f"{prog}_patch.json").read_text())
        assert patch == json.loads(last_block(reply, "json")), f"{exp} {prog}: patch isn't the reply's last json block"
        assert decode_rows(rows) == original
        rebuilt = bytearray(original)
        for edit in patch["edits"]:
            offset, old, new = int(edit["offset"], 16), bytes.fromhex(edit["old"]), bytes.fromhex(edit["new"])
            assert len(old) == len(new) and original[offset:offset + len(old)] == old, f"{exp} {prog}: bad edit {edit}"
            rebuilt[offset:offset + len(new)] = new
        rebuilt += bytes.fromhex(patch.get("append", ""))
        assert bytes(rebuilt) == patched, f"{exp} {prog}: the edits don't produce the scored file"
        changed = sum(a != b for a, b in zip(original, patched)) + abs(len(patched) - len(original))
        copy_file(logs / "binaries" / f"{prog}.bin", dest / "original.bin")
        copy_file(logs / "binaries" / f"{prog}_patched.bin", dest / "patched.bin")
        copy_file(logs / "binaries" / f"{prog}_patch.json", dest / "patch.json")
        entry["files"].update(original="original.bin", patched="patched.bin", patch="patch.json")
        entry["inputBytes"] = len(original)
        entry["bytes"] = {"kind": "patch", "size": len(patched), "changed": changed, "edits": len(patch["edits"])}

    if kind == "write":
        built = (logs / "binaries" / f"{prog}_constructed.bin").read_bytes()
        assert bytes.fromhex(last_block(reply, "hex")) == built, f"{exp} {prog}: file isn't the reply's last hex block"
        copy_file(logs / "binaries" / f"{prog}_constructed.bin", dest / "program.bin")
        entry["files"]["program"] = "program.bin"
        entry["bytes"] = {"kind": "write", "size": len(built)}

    if kind in ("patch", "write"):
        tests = json.loads((logs / "eval" / f"{prog}.json").read_text())
        entry["tests"] = tests_summary(tests)
        copy_file(logs / "eval" / f"{prog}.json", dest / "tests.json")
        entry["files"]["tests"] = "tests.json"
        tokens, seconds, total, byte_count = EXPECTED[(exp, prog)]
        assert entry["usage"]["output"] == tokens and entry["seconds"] == seconds, f"{exp} {prog}: post disagrees on usage"
        assert tests["passed"] == tests["total"] == total, f"{exp} {prog}: post disagrees on tests"
        got = entry["bytes"].get("changed", entry["bytes"]["size"])
        assert got == byte_count, f"{exp} {prog}: post disagrees on bytes: {got}"

    if exp == "exp4":
        assert entry["seconds"] == 211 and entry["usage"]["reasoning"] == 5178, "post disagrees on Exp 4"
    return entry


def build_exp5(sample_rows):
    """DeepSeek's run, from the local OpenCode session when it's available."""
    dest = OUT / "exp5" / "sample"
    if OPENCODE_DB.exists():
        db = sqlite3.connect(f"file:{OPENCODE_DB}?mode=ro", uri=True)
        messages = db.execute("select type, data from session_message where session_id=? order by seq",
                              (OPENCODE_SESSION,)).fetchall()
        user = next(json.loads(d) for t, d in messages if t == "user")
        assistant = next(json.loads(d) for t, d in messages if t == "assistant")
        parts = {p["type"]: p["text"] for p in assistant["content"]}
        assert parts["reasoning"].strip() == THINKING.read_text().strip(), "the transcript in the post has changed"
        assert user["text"].startswith('"') and user["text"].rstrip().endswith('"')
        head, rows = split_prompt(user["text"].rstrip()[:-1])
        assert decode_rows(rows) == decode_rows(sample_rows), "Exp 5 had a different sample from Exp 4"
        seconds = (assistant["time"]["completed"] - assistant["time"]["created"]) / 1000
        size = len(decode_rows(rows))
        copy_text(f'{head}[Hex dump withheld: {len(rows)} rows, {size:,} bytes]"\n', dest / "prompt.txt")
        copy_text(redact(parts["text"]) if MASK_ADDRESS else parts["text"], dest / "reply.md")
        copy_text(json.dumps({
            "source": "OpenCode 2.2.5 session record",
            "model": assistant["model"]["id"], "provider": assistant["model"]["providerID"],
            "effort": assistant["model"]["variant"], "finish": assistant["finish"],
            "tool_calls_recorded": sum(p["type"] not in ("reasoning", "text") for p in assistant["content"]),
            "tokens": assistant["tokens"], "wall_s": round(seconds, 1), "input_bytes": size,
        }, indent=1) + "\n", dest / "run.json")

    run = json.loads((dest / "run.json").read_text())
    assert run["tool_calls_recorded"] == 0 and round(run["wall_s"]) == 859 and run["tokens"]["reasoning"] == 89902
    prompt = (dest / "prompt.txt").read_text()
    return {
        "label": "Windows sample", "note": SAMPLE_NOTE,
        "dir": "exp5/sample", "model": run["model"], "effort": run["effort"],
        "usage": {"input": run["tokens"]["input"], "output": run["tokens"]["output"],
                  "reasoning": run["tokens"]["reasoning"]},
        "seconds": round(run["wall_s"]),
        "audit": "No tool calls recorded, no relay",
        "promptBytes": len(prompt.encode()), "promptHead": prompt, "hexRows": 0, "hexWithheld": True,
        "inputBytes": run["input_bytes"],
        "files": {"prompt": "prompt.txt", "reply": "reply.md"},
    }


def main():
    manifest = {}
    for exp, config in EXPERIMENTS.items():
        shutil.rmtree(OUT / exp, ignore_errors=True)
        runs = [build_run(exp, config, *spec) for spec in config["runs"]]
        manifest[exp] = {"kind": config["kind"], "runs": runs}
    _, sample_rows = split_prompt((LOGS / "exp1_understand/runs/prog4/prompt.txt").read_text())
    manifest["exp5"] = {"kind": "read", "runs": [build_exp5(sample_rows)]}

    if WITHHOLD_SAMPLE:
        for exp in ("exp4", "exp5"):
            for path in (OUT / exp).rglob("*"):
                if path.is_file():
                    text = path.read_text()
                    # 127.0.0.1 is the local relay, named in run.json's command line.
                    if MASK_ADDRESS:
                        assert set(IPV4.findall(text)) <= {"127.0.0.1"}, f"{path} still holds an address"
                    assert not HEX_ROW.search(text), f"{path} still holds the hex dump"

    (OUT / "manifest.js").write_text(
        "// Generated by scripts/make_runs.py from the logs repo. Don't edit by hand.\n"
        f"window.RUNS = {json.dumps(manifest, indent=1)};\n")
    total = sum(f.stat().st_size for f in OUT.rglob("*") if f.is_file())
    print(f"{sum(len(e['runs']) for e in manifest.values())} runs, {total:,} bytes in {OUT}")


if __name__ == "__main__":
    os.umask(0o022)
    main()
