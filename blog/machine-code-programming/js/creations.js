// Figure 3: the three programs Sol 6.1 wrote from an empty file, laid out like the finished state of the showcase's Create tab
// (js/showcase.js), with no animation. Each tab shows the whole file colored by region, a legend, and the file run on a
// sample input. Hovering, focusing or tapping a byte shows the field, instruction or table it belongs to.
//   wordcount: 391 bytes in hex, labeled by header field and instruction (assets/wc391.js).
//   AES, ledger: too large for hex, so one square per byte, labeled by routine or table (assets/programmaps.js).
(() => {
  const hex = (n, w = 2) => n.toString(16).padStart(w, "0");
  const el = (tag, cls, text) => {
    const e = document.createElement(tag);
    if (cls) e.className = cls;
    if (text != null) e.textContent = text;
    return e;
  };

  const WC_REGION = {
    ehdr: "ELF header", phdr: "Program header", setup: "Setup", read: "Read loop", count: "Counting",
    format: "Format output", write: "Write loop", exit: "Exit", itoa: "Number helper",
  };

  // Each run below was checked by running Sol 6.1's file on this input.
  const RUNS = {
    wordcount: {
      command: 'echo "hello world" | ./wordcount',
      output: "1 2 12 11",
      note: "Same output as GCC's build, which is 5,432 bytes",
    },
    aes: {
      command: "echo \"enc 128 000102030405060708090a0b0c0d0e0f 00112233445566778899aabbccddeeff\" | ./aes",
      output: "69c4e0d86a7b0430d8cdb78070b4c55a",
      note: "The FIPS-197 test vector. GCC's build is 9,408 bytes",
    },
    ledger: {
      command: "printf 'open alice 100\\nopen bob 50\\ntransfer alice bob 30\\nreport\\n' | ./ledger",
      output: "OK\nOK\nOK 70 80\nalice 70\nbob 80\nTOTAL 150",
      note: "Same output as GCC's build, which is 8,896 bytes",
    },
  };

  // Both data sets become one shape: the bytes, and spans of them with a color class, a region name, a label and a note.
  function wordcount() {
    const { bytes, groups } = window.WC391;
    return {
      bytes, hexView: true,
      spans: groups.map((g) => ({
        start: g.start, end: g.start + g.len, cls: `r-${g.region}`, region: WC_REGION[g.region], label: g.label, note: g.note || "",
      })),
    };
  }

  function program(name) {
    const p = window.PROGRAMMAPS[name];
    const ins = new Map();
    p.ins.forEach((x) => { for (let k = x[0]; k < x[0] + x[1]; k++) ins.set(k, x); });
    const line = (off, r) => {
      const x = ins.get(off);
      if (x) return `0x${hex(x[0], 3)}  ${x[2]}`;
      if (r.group === "text") {
        let a = off;
        while (a > r.start && p.bytes[a - 1] >= 0x20) a--;
        let b = off;
        while (b < r.end && p.bytes[b] >= 0x20) b++;
        return `0x${hex(off, 3)}  "${String.fromCharCode(...p.bytes.slice(a, b))}"`;
      }
      return `0x${hex(off, 3)}  ${hex(p.bytes[off])}`;
    };
    return {
      bytes: p.bytes, hexView: false, line,
      spans: p.regions.map((r) => ({
        start: r.start, end: r.end, cls: `g-${r.group}`, region: p.groups[r.group], label: r.name, pad: r.group === "pad", raw: r,
      })),
    };
  }

  // One finished file: the grid with every byte in its region's color, the regions as a legend, a readout for the
  // byte under the pointer, and the file run on a sample input.
  function render(stage, name) {
    const prog = name === "wordcount" ? wordcount() : program(name);
    const { bytes, spans } = prog;
    const n = bytes.length;
    const spanOf = new Uint16Array(n);
    spans.forEach((s, i) => { for (let k = s.start; k < s.end; k++) spanOf[k] = i; });

    // The file: a hex grid like the showcase's for wordcount, squares for the larger two.
    const visual = el("div", "sc-visual");
    const cells = [];
    let grid;
    if (prog.hexView) {
      grid = el("div", "sc-hexgrid sc-create");
      for (let row = 0; row < n; row += 16) {
        grid.append(el("span", "sc-addr", "0x" + hex(0x400000 + row, 6)));
        for (let i = row; i < row + 16; i++) {
          if (i >= n) { grid.append(el("span", "sc-b pad")); continue; }
          const c = el("span", `sc-b ${spans[spanOf[i]].cls}`, hex(bytes[i]));
          c.dataset.off = i;
          cells.push(c);
          grid.append(c);
        }
      }
      visual.append(el("div", "sc-label", `Output: a complete ELF executable · ${n} bytes in hex`), grid);
    } else {
      grid = el("div", "cr-squares");
      grid.style.setProperty("--cols", Math.ceil(n / 56));
      for (let i = 0; i < n; i++) {
        const c = el("span", `cr-b w ${spans[spanOf[i]].cls}`);
        c.dataset.off = i;
        cells.push(c);
        grid.append(c);
      }
      visual.append(el("div", "sc-label", `Output: a complete ELF executable · ${n.toLocaleString()} bytes, one square each`), grid);
    }

    const side = el("div", "sc-side");
    const now = el("div", "sc-now");
    const nowRegion = el("div", "sc-now-region");
    const nowLabel = el("div", "sc-now-label");
    const nowNote = el("div", "sc-now-note");
    now.append(nowRegion, nowLabel, nowNote);
    // For the larger files the label is the routine's name in prose and the note is the instruction, so swap their fonts.
    if (!prog.hexView) now.classList.add("cr-asm");
    const legend = el("ul", "sc-legend");
    const seen = new Set();
    for (const s of spans) {
      if (s.pad || seen.has(s.cls)) continue;
      seen.add(s.cls);
      legend.append(el("li", s.cls, s.region));
    }
    const r = RUNS[name];
    const term = el("div", "sc-term");
    term.append(el("div", "sc-cmd", r.command), el("div", "sc-out new", r.output), el("div", "sc-term-note", r.note));
    side.append(el("div", "sc-label", "Written by Sol 6.1 in one reply, no assembler"), now, legend, term);
    stage.append(visual, side);

    // Hovering, focusing or tapping a byte lights up its field, routine or table and says what it is.
    let lit = -1;
    let here = null;
    const show = (off) => {
      const si = spanOf[off];
      const s = spans[si];
      if (si !== lit) {
        if (lit >= 0) for (let k = spans[lit].start; k < spans[lit].end; k++) cells[k].classList.remove("hl");
        for (let k = s.start; k < s.end; k++) cells[k].classList.add("hl");
        lit = si;
      }
      if (here) here.classList.remove("here");
      here = cells[off];
      here.classList.add("here");
      nowRegion.textContent = s.region;
      nowRegion.className = `sc-now-region ${s.cls}`;
      if (prog.hexView) {
        nowLabel.textContent = `0x${hex(off, 3)}  ${s.label}`;
        nowNote.textContent = s.note;
      } else {
        nowLabel.textContent = s.label;
        nowNote.textContent = prog.line(off, s.raw);
      }
    };
    const pick = (e) => { if (e.target.dataset && e.target.dataset.off !== undefined) show(Number(e.target.dataset.off)); };
    grid.addEventListener("mouseover", pick);
    grid.addEventListener("click", pick);
    grid.classList.add("done");
    // Start on the first instruction after the headers.
    show(spans.find((s) => !s.pad && !/hdr|head/.test(s.cls) && s.start >= 64).start);
  }

  const ORDER = ["wordcount", "aes", "ledger"];

  function select(root, name) {
    root.querySelectorAll(".sc-tabs [data-cr]").forEach((t) => {
      const on = t.dataset.cr === name;
      t.setAttribute("aria-selected", String(on));
      t.tabIndex = on ? 0 : -1;
    });
    const stage = root.querySelector(".sc-stage");
    stage.replaceChildren();
    stage.setAttribute("aria-labelledby", `cr-tab-${name}`);
    render(stage, name);
  }

  document.addEventListener("click", (event) => {
    const tab = event.target.closest(".sc-tabs [data-cr]");
    if (tab) select(tab.closest(".cr"), tab.dataset.cr);
  });

  // Arrow keys move between tabs, as in the ARIA tabs pattern.
  document.addEventListener("keydown", (event) => {
    const tab = event.target.closest && event.target.closest(".sc-tabs [data-cr]");
    if (!tab || !["ArrowLeft", "ArrowRight", "Home", "End"].includes(event.key)) return;
    event.preventDefault();
    const i = ORDER.indexOf(tab.dataset.cr);
    const j = event.key === "Home" ? 0 : event.key === "End" ? ORDER.length - 1
      : (i + (event.key === "ArrowRight" ? 1 : ORDER.length - 1)) % ORDER.length;
    const root = tab.closest(".cr");
    select(root, ORDER[j]);
    root.querySelector(`[data-cr="${ORDER[j]}"]`).focus();
  });

  // The Distill template re-renders the article after load, so draw the first tab once that is done.
  window.addEventListener("load", () => {
    const setup = () => {
      const root = document.querySelector(".cr");
      if (!root || root.dataset.ready || !window.WC391 || !window.PROGRAMMAPS) return;
      root.dataset.ready = "1";
      select(root, "wordcount");
    };
    setup();
    setTimeout(setup, 300);
    setTimeout(setup, 1200);
  });
})();
