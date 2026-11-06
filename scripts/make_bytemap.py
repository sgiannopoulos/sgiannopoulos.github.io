#!/usr/bin/env python3
"""Build the data behind the byte map figure from the model's own 391-byte binary.

Run from the repo root: python3 scripts/make_bytemap.py
Reads blog/machine-code-programming/assets/wc391.bin and writes wc391.js beside it. The binary is only disassembled,
never run. Needs an objdump that understands ELF x86-64 (the one in the Xcode command line tools does).
"""
import json
import re
import subprocess
from pathlib import Path

ASSETS = Path("blog/machine-code-programming/assets")
BASE = 0x400000

EHDR = [("e_ident", 16, "magic, 64-bit, little-endian"), ("e_type", 2, "ET_EXEC"), ("e_machine", 2, "x86-64"),
        ("e_version", 4, ""), ("e_entry", 8, "entry point 0x400078"), ("e_phoff", 8, "program headers at 0x40"),
        ("e_shoff", 8, "no section headers"), ("e_flags", 4, ""), ("e_ehsize", 2, "64"), ("e_phentsize", 2, "56"),
        ("e_phnum", 2, "one segment"), ("e_shentsize", 2, ""), ("e_shnum", 2, ""), ("e_shstrndx", 2, "")]
PHDR = [("p_type", 4, "PT_LOAD"), ("p_flags", 4, "read + execute"), ("p_offset", 8, ""), ("p_vaddr", 8, "0x400000"),
        ("p_paddr", 8, ""), ("p_filesz", 8, "391 bytes"), ("p_memsz", 8, "391 bytes"), ("p_align", 8, "0x1000")]

# File offset where each part of the program starts: (end offset, region, what it does).
CODE = [(0x8f, "setup", "Reserve a 4,096-byte stack buffer and zero the counters"),
        (0xb2, "read", "read(0, buffer, 4096), retry on EINTR, leave the loop at end of input"),
        (0xf1, "count", "Scan each byte: lines, words and the current line's length"),
        (0x139, "format", "Build the output backward from the buffer's end: newline, longest, bytes, words, lines"),
        (0x166, "write", "write(1, ...), looping over partial writes"),
        (0x16f, "exit", "exit_group(0)"),
        (0x187, "itoa", "Helper: write a number as decimal, last digit first")]


def fields(start, table, region):
    out, off = [], start
    for name, size, note in table:
        out.append({"start": off, "len": size, "region": region, "label": name, "note": note})
        off += size
    return out


def main():
    data = (ASSETS / "wc391.bin").read_bytes()
    assert len(data) == 391
    dump = subprocess.run(["objdump", "-d", "--start-address=0x400078", str(ASSETS / "wc391.bin")], capture_output=True, text=True, check=True).stdout

    groups = fields(0, EHDR, "ehdr") + fields(64, PHDR, "phdr")
    branches = 0
    for line in dump.splitlines():
        m = re.match(r"\s+([0-9a-f]+):\s+((?:[0-9a-f]{2} )+)\s*\t(.*)", line)
        if not m:
            continue
        off = int(m[1], 16) - BASE
        if off < 0x78:
            continue
        size = len(m[2].split())
        asm = re.sub(r"\s+", " ", m[3].split("#")[0].strip())
        asm = re.sub(r" <PT_LOAD.*$", "", asm)
        branches += bool(re.match(r"(j[a-z]+|callq) 0x", asm))
        end, region, note = next(c for c in CODE if off < c[0])
        groups.append({"start": off, "len": size, "region": region, "label": asm, "note": note})

    covered = sum(g["len"] for g in groups)
    assert covered == 391, covered
    payload = {"bytes": list(data), "groups": groups}
    (ASSETS / "wc391.js").write_text("window.WC391 = " + json.dumps(payload, separators=(",", ":")) + ";\n")
    print(f"{len(groups)} groups, {branches} relative jumps and calls")


if __name__ == "__main__":
    main()
