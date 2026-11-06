#!/usr/bin/env python3
"""Build the data behind the showcase at the top of the post (Understand / Extend / Create).

Run from the repo root: python3 scripts/make_showcase.py
Reads, all copied from the d2a0e1f runs in the logs repo:
  assets/wordcount-original.bin  the stripped 5,368-byte binary Sol was given (binaries/prog1/original.bin)
  assets/wordcount-report.md     Sol's Exp 1 report on it (exp1_understand/.../prog1/a1/turns/t001/answer.md)
  assets/wordcount-patch.json    Sol's Exp 2 patch (exp2_patch/.../prog1/a1/patch.json)
and writes assets/showcase.js. The Create tab reuses assets/wc391.js (see make_bytemap.py).

Every quote below is checked against the report text, and every highlighted byte range against the binary, so the
script fails rather than ship a quote or a highlight that isn't real.
"""
import json
import re
from pathlib import Path

ASSETS = Path("blog/machine-code-programming/assets")

original = (ASSETS / "wordcount-original.bin").read_bytes()
report = (ASSETS / "wordcount-report.md").read_text()
patch = json.loads((ASSETS / "wordcount-patch.json").read_text())["edits"]


def plain(md):
    """The report's Markdown as plain text, for checking quotes."""
    return re.sub(r"\*\*|`", "", md)


REPORT = plain(report)

# ---- Understand: the main counting loop, with the lines of Sol's report that explain its bytes ----------------------
WINDOW = (0x1000, 0x10c0)  # file offsets of the main routine's loop (loaded at 0x401000)

# (quote from the report, [(file offset, expected bytes as hex)]): the bytes each quote is about, from a disassembly.
EVIDENCE = [
    ("This is a small, self-contained Linux x86-64 word-count utility.", []),
    ("The main routine reads in blocks of 4,096 bytes",
     [(0x1013, "ba00100000"), (0x1071, "0f05")]),                          # mov edx, 0x1000 ... syscall
    ("rbx: byte count", [(0x104B, "4883c301")]),                            # add rbx, 1
    ("The central loop explicitly tests the current byte against 0x0a for line counting.",
     [(0x1052, "4180fb0a")]),                                               # cmp r11b, 0xa
    ("Other whitespace is recognized by subtracting 9 and checking whether the resulting byte is at most 4, "
     "then separately testing for 0x20.",
     [(0x1058, "83e909"), (0x105B, "80f904"), (0x1060, "4183fb20")]),       # sub ecx, 9; cmp cl, 4; cmp r11d, 0x20
    ("rbp: word count", [(0x1095, "4883c501")]),                            # add rbp, 1
    ("r10: line count", [(0x10A8, "4983c201")]),                            # add r10, 1
]

understand = {"base": WINDOW[0], "bytes": list(original[WINDOW[0]:WINDOW[1]]), "steps": []}
for quote, spans in EVIDENCE:
    assert quote in REPORT, f"not in the report: {quote!r}"
    ranges = []
    for off, hexbytes in spans:
        want = bytes.fromhex(hexbytes)
        assert original[off:off + len(want)] == want, f"bytes at {off:#x} are not {hexbytes}"
        assert WINDOW[0] <= off and off + len(want) <= WINDOW[1]
        ranges.append([off, len(want)])
    understand["steps"].append({"quote": quote, "ranges": ranges})

# ---- Extend: every byte the patch changed, grouped into Sol's three moves -----------------------------------------
GROUPS = [
    ("Make room", "Mark the first segment executable and grow it to 0x1000, so its zero padding can hold code.",
     {0x44, 0x60}),
    ("Write new code", "Three routines in the padding: zero the counters, track line length, print the longest.",
     {0x200, 0x220, 0x230, 0x240, 0x250}),
    ("Hook it in", "Overwrite three instructions with calls into the new code.", {0x102A, 0x104B, 0x10E9}),
]
patched = bytearray(original)
extend = {"size": len(original), "bytes": list(original), "groups": []}
for title, note, offsets in GROUPS:
    changed = []
    for e in patch:
        off = int(e["offset"], 16)
        if off not in offsets:
            continue
        old = bytes.fromhex(e["old"].replace(" ", ""))
        new = bytes.fromhex(e["new"].replace(" ", ""))
        assert original[off:off + len(old)] == old
        patched[off:off + len(new)] = new
        changed += [[off + i, new[i]] for i in range(len(new)) if new[i] != old[i]]
    extend["groups"].append({"title": title, "note": note, "changed": changed})
total = sum(len(g["changed"]) for g in extend["groups"])
assert total == sum(a != b for a, b in zip(original, patched)) == 74, total

# ---- Outputs, from running the real files under qemu-x86_64 (binary-space/run.sh x86) -----------------------------
# echo "hello world" | original -> "1 2 12"; Sol's patched build and Sol's 391-byte build -> "1 2 12 11".
outputs = {"command": 'echo "hello world" | ./wordcount', "before": "1 2 12", "after": "1 2 12 11"}

data = {"understand": understand, "extend": extend, "outputs": outputs}
(ASSETS / "showcase.js").write_text("window.SHOWCASE = " + json.dumps(data, separators=(",", ":")) + ";\n")
print(f"wrote {ASSETS / 'showcase.js'}: {len(understand['steps'])} report steps, {total} changed bytes")
