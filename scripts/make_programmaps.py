#!/usr/bin/env python3
"""Build the data behind Figure 3's AES and Ledger tabs: every byte of the two larger files Sol wrote from scratch.

Run from the repo root, with GNU objdump (the macOS one can't read raw binaries), for example in Docker:
    docker run --rm -v "$PWD":/w -w /w <image with python3 and binutils> python3 scripts/make_programmaps.py
Set OBJDUMP if yours has another name (x86_64-linux-gnu-objdump, say).

Reads assets/aes4144.bin and assets/ledger3584.bin, copied from the d2a0e1f Exp 3 runs in the logs repo
(exp3_construct/runs/gpt-6.1-sol-high/prog2 and prog3), and writes assets/programmaps.js. The files are only
disassembled, never run.

Sol put each routine at a 16-byte boundary with zero padding between, so a plain linear sweep falls out of step after
padding. The decoder restarts at the next nonzero byte whenever it meets opcode 00, which only ever appears here as
padding. The script then checks that the result is sound: no invalid instructions, every nonzero code byte inside an
instruction, every direct and indirect branch target on an instruction, every routine start on an instruction, and the
AES tables equal to the real S-box, inverse S-box and ShiftRows orders. The routine names and groups are ours.
"""
import json
import os
import re
import subprocess
from pathlib import Path

ASSETS = Path("blog/machine-code-programming/assets")
OBJDUMP = os.environ.get("OBJDUMP", "objdump")
BASE = 0x400000

GROUPS = {
    "head": "Headers", "io": "Input and output", "parse": "Parsing", "logic": "", "out": "Output",
    "err": "Errors", "table": "Tables", "text": "Strings", "pad": "Zero padding",
}

PROGRAMS = {
    "aes": {
        "file": "aes4144.bin", "code_end": 0xD80, "logic": "AES",
        "routines": {
            0x100: ("io", "Main loop: gather a line, one byte at a time"),
            0x130: ("io", "On a newline: handle the line, then start the next"),
            0x140: ("io", "At end of input: handle the last line, then exit_group(0)"),
            0x180: ("parse", "Strip a trailing CR, then parse the line"),
            0x200: ("io", "Read one byte, refilling a 4 KiB buffer with read()"),
            0x280: ("io", "write(1, ...), retrying partial writes"),
            0x300: ("parse", "Split the line into words"),
            0x400: ("parse", "Check the command (enc or dec) and the key size"),
            0x500: ("logic", "Decode key and data, expand the key, run each 16-byte block"),
            0x600: ("parse", "Hex text to bytes"),
            0x680: ("parse", "One hex digit to its value"),
            0x700: ("logic", "Key expansion"),
            0x800: ("logic", "SubWord: four S-box lookups"),
            0x880: ("logic", "AddRoundKey"),
            0x900: ("logic", "SubBytes and ShiftRows, or their inverses, by table"),
            0xA00: ("logic", "MixColumns; for dec, InvMixColumns through a pre-step"),
            0xAF0: ("logic", "xtime: multiply by 2 in GF(2^8)"),
            0xB00: ("logic", "Encrypt or decrypt one block, round by round"),
            0xC00: ("out", "Print the result as hex"),
            0xD00: ("err", "Pick the error message"),
            0xD60: ("err", "Write the error message"),
        },
        "data": [
            (0xD80, 0xDD5, "text", "Error messages"),
            (0xE00, 0xF00, "table", "S-box"),
            (0xF00, 0x1000, "table", "Inverse S-box"),
            (0x1000, 0x1010, "table", "ShiftRows byte order"),
            (0x1010, 0x1020, "table", "InvShiftRows byte order"),
            (0x1020, 0x1030, "table", "Hex digits"),
        ],
        "first": 0xB00,
    },
    "ledger": {
        "file": "ledger3584.bin", "code_end": 0xC00, "logic": "Accounts",
        "routines": {
            0x100: ("io", "Main loop: read a line, split it, run it, flush the output"),
            0x180: ("io", "Read a line with read(), a byte at a time, and strip a trailing CR"),
            0x200: ("parse", "Split the line into up to five words"),
            0x300: ("parse", "Look up the command, check its arguments, jump to its handler"),
            0x500: ("logic", "open: add an account"),
            0x580: ("logic", "deposit, withdraw and transfer"),
            0x700: ("out", "report: sort the accounts by name, print them and the total"),
            0x880: ("logic", "Find an account by name"),
            0x900: ("out", "Write a number in decimal"),
            0x980: ("io", "Flush the output buffer with write()"),
            0xA00: ("logic", "Compare two names, byte by byte"),
            0xB00: ("err", "Pick the error message, one entry per error"),
            0xB80: ("err", "Copy the error message to the output"),
        },
        "data": [
            (0xC00, 0xC50, "table", "Command names and their lengths"),
            (0xC50, 0xC55, "table", "Word count per command"),
            (0xC60, 0xC74, "table", "Handler address per command"),
            (0xC80, 0xCB8, "table", "Error message addresses and lengths"),
            (0xD00, 0xDD8, "text", "Error messages"),
        ],
        "first": 0x580,
    },
}


def decode(path, a, b):
    out = subprocess.run([OBJDUMP, "-D", "-b", "binary", "-m", "i386:x86-64", "-M", "intel", f"--adjust-vma={BASE}",
                          f"--start-address={BASE + a}", f"--stop-address={BASE + b}", str(path)],
                         capture_output=True, text=True, check=True).stdout
    ins = []
    for line in out.splitlines():
        m = re.match(r"\s*([0-9a-f]+):\s+((?:[0-9a-f]{2} )+)\s*(.*)", line)
        if not m:
            continue
        off, size, asm = int(m[1], 16) - BASE, len(m[2].split()), re.sub(r"\s+", " ", m[3]).strip()
        if not asm:  # objdump wraps long instructions onto a second line
            ins[-1][1] += size
            continue
        ins.append([off, size, asm])
    return ins


def disassemble(path, data, code_end):
    result, cur = [], 0x100
    while cur < code_end:
        for off, size, asm in decode(path, cur, code_end):
            if data[off] == 0:  # opcode 00 only ever appears here as zero padding: resync after it
                cur = off
                while cur < code_end and data[cur] == 0:
                    cur += 1
                break
            result.append([off, size, asm])
        else:
            cur = code_end
    return result


def aes_tables():
    def mul(a, b):
        p = 0
        while b:
            if b & 1:
                p ^= a
            a = ((a << 1) ^ 0x11B) if a & 0x80 else a << 1
            b >>= 1
        return p
    inv = [0] + [next(y for y in range(1, 256) if mul(x, y) == 1) for x in range(1, 256)]
    rot = lambda x, s: ((x << s) | (x >> (8 - s))) & 0xFF
    sbox = [inv[x] ^ rot(inv[x], 1) ^ rot(inv[x], 2) ^ rot(inv[x], 3) ^ rot(inv[x], 4) ^ 0x63 for x in range(256)]
    inv_sbox = [sbox.index(x) for x in range(256)]
    shift = [(r + 4 * ((c + r) % 4)) for c in range(4) for r in range(4)]
    inv_shift = [(r + 4 * ((c - r) % 4)) for c in range(4) for r in range(4)]
    return {"S-box": sbox, "Inverse S-box": inv_sbox, "ShiftRows byte order": shift, "InvShiftRows byte order": inv_shift}


def build(key, spec):
    path = ASSETS / spec["file"]
    data = path.read_bytes()
    end = spec["code_end"]
    ins = disassemble(path, data, end)
    starts = {i[0] for i in ins}

    assert not [i for i in ins if "(bad)" in i[2]], "invalid instruction"
    inside = set(o for s, n, _ in ins for o in range(s, s + n))
    assert all(o in inside for o in range(0x100, end) if data[o]), "a nonzero code byte is outside every instruction"
    direct = [int(t, 16) - BASE for i in ins for t in re.findall(r"^(?:j[a-z]+|call) 0x([0-9a-f]+)$", i[2])]
    indirect = [int(t, 16) - BASE for i in ins for t in re.findall(r"^mov e[a-d]x,0x(4[0-9a-f]{5})$", i[2])]
    assert all(t in starts for t in direct), "a branch lands between instructions"
    assert all(t in starts for t in indirect if 0x100 <= t < end), "a jump target lands between instructions"
    assert all(r in starts for r in spec["routines"]), "a routine start is not an instruction"
    if key == "aes":
        for name, want in aes_tables().items():
            a, b = next((a, b) for a, b, _, n in spec["data"] if n == name)
            assert list(data[a:b]) == want, f"{name} does not match AES"
        assert data[0x1020:0x1030] == b"0123456789abcdef"

    # One region per header, routine, table and padding run; every byte belongs to exactly one.
    regions = [{"start": 0, "end": 64, "group": "head", "name": "ELF header"},
               {"start": 64, "end": 120, "group": "head", "name": "Program header: one read-write-execute segment"}]
    bounds = sorted(spec["routines"]) + [end]
    for a, b in zip(bounds, bounds[1:]):
        last = max(s + n for s, n, _ in ins if a <= s < b)
        group, name = spec["routines"][a]
        regions.append({"start": a, "end": last, "group": group, "name": name})
    for a, b, group, name in spec["data"]:
        regions.append({"start": a, "end": b, "group": group, "name": name})
    regions.sort(key=lambda r: r["start"])
    filled, cur = [], 0
    for r in regions:
        if r["start"] > cur:
            assert not any(data[cur:r["start"]]), f"unlabeled nonzero bytes at {cur:#x}"
            filled.append({"start": cur, "end": r["start"], "group": "pad", "name": "Zero padding"})
        filled.append(r)
        cur = r["end"]
    if cur < len(data):
        assert not any(data[cur:])
        filled.append({"start": cur, "end": len(data), "group": "pad", "name": "Zero padding"})

    first = next(i for i, r in enumerate(filled) if r["start"] == spec["first"])
    groups = dict(GROUPS, logic=spec["logic"])
    print(f"{key}: {len(data)} bytes, {len(ins)} instructions, {len(direct)} branches, {len(filled)} regions")
    return {"bytes": list(data), "regions": filled, "ins": ins, "groups": groups, "first": first}


def main():
    payload = {key: build(key, spec) for key, spec in PROGRAMS.items()}
    (ASSETS / "programmaps.js").write_text("window.PROGRAMMAPS = " + json.dumps(payload, separators=(",", ":")) + ";\n")


if __name__ == "__main__":
    main()
