// The showcase at the top of the post: one program (wordcount) through all three tasks, replayed from the real data.
//   Understand: the main loop's bytes, lit up as each line of Sol 6.1's report explains them (assets/showcase.js).
//   Extend:     all 5,368 bytes as a map, with the 74 Sol 6.1 changed appearing in its three moves.
//   Create:     an empty file filling with the 391 bytes Sol 6.1 wrote, labeled by region (assets/wc391.js).
// It plays when scrolled into view and moves on to the next task by itself until the reader picks a tab. With
// prefers-reduced-motion it shows each task's finished state and never animates.
(() => {
  const reduce = window.matchMedia("(prefers-reduced-motion: reduce)");
  const hex = (b) => b.toString(16).padStart(2, "0");
  const addr = (n) => "0x" + n.toString(16).padStart(6, "0");
  const el = (tag, cls, text) => {
    const e = document.createElement(tag);
    if (cls) e.className = cls;
    if (text != null) e.textContent = text;
    return e;
  };

  const REGION = {
    ehdr: "ELF header", phdr: "Program header", setup: "Setup", read: "Read loop", count: "Counting",
    format: "Format output", write: "Write loop", exit: "Exit", itoa: "Number helper",
  };

  let run = 0;          // bumps on every (re)start, so a superseded animation stops at its next await
  let auto = true;      // move on to the next task by itself until the reader clicks a tab
  let current = "understand";

  const wait = (ms, id) => new Promise((done) => {
    if (reduce.matches) return done();
    setTimeout(done, ms);
  }).then(() => { if (id !== run) throw new Error("stopped"); });

  // ---------- Understand -----------------------------------------------------------------------------------------
  async function understand(stage, id) {
    const { base, bytes, steps } = window.SHOWCASE.understand;
    const visual = el("div", "sc-visual");
    const grid = el("div", "sc-hexgrid");
    const cells = [];
    for (let row = 0; row < bytes.length; row += 16) {
      grid.append(el("span", "sc-addr", addr(0x400000 + base + row)));
      for (let i = row; i < row + 16; i++) {
        const c = el("span", "sc-b", hex(bytes[i]));
        cells.push(c);
        grid.append(c);
      }
    }
    visual.append(el("div", "sc-label", "Input: the stripped binary as hex · its main loop"), grid);

    const side = el("div", "sc-side");
    side.append(el("div", "sc-label", "Sol 6.1's report, verbatim"));
    const list = el("ol", "sc-quotes");
    side.append(list, el("div", "sc-meta", "5,368 bytes in · one reply · 152 s · no tools"));
    stage.append(visual, side);

    for (const step of steps) {
      cells.forEach((c) => c.classList.remove("on"));
      list.querySelectorAll("li").forEach((li) => li.classList.remove("now"));
      const li = el("li", "now");
      list.append(li);
      const q = el("q");
      li.append(q);
      // Type the quote in a few characters at a time.
      for (let n = 0; n <= step.quote.length; n += 3) {
        q.textContent = step.quote.slice(0, n);
        await wait(14, id);
      }
      q.textContent = step.quote;
      for (const [off, len] of step.ranges) {
        for (let i = off - base; i < off - base + len; i++) cells[i].classList.add("on", "seen");
      }
      await wait(step.ranges.length ? 1700 : 1100, id);
    }
    cells.forEach((c) => c.classList.remove("on"));
    list.querySelectorAll("li").forEach((li) => li.classList.remove("now"));
  }

  // ---------- Extend ---------------------------------------------------------------------------------------------
  async function extend(stage, id) {
    const root = stage.closest(".sc");
    const { size, bytes, groups } = window.SHOWCASE.extend;
    const out = window.SHOWCASE.outputs;
    const COLS = 96;
    const rows = Math.ceil(size / COLS);

    const visual = el("div", "sc-visual");
    const mapWrap = el("div", "sc-mapwrap");
    const canvas = el("canvas", "sc-map");
    canvas.setAttribute("role", "img");
    canvas.setAttribute("aria-label", `A map of all ${size.toLocaleString()} bytes of the binary. The 74 bytes Sol 6.1 changed are marked in green.`);
    mapWrap.append(canvas);
    visual.append(el("div", "sc-label", `All ${size.toLocaleString()} bytes · one square per byte · dark = zero`), mapWrap);

    const side = el("div", "sc-side");
    const counter = el("div", "sc-counter");
    const big = el("b", null, "0");
    counter.append(big, el("span", null, ` of ${size.toLocaleString()} bytes changed`));
    const moves = el("ol", "sc-moves");
    const term = el("div", "sc-term");
    side.append(el("div", "sc-label", "Sol 6.1's patch: same length, nothing moves"), counter, moves, term);
    stage.append(visual, side);

    // Draw the map at device resolution once the canvas has its laid-out width.
    const ctx = canvas.getContext("2d");
    let cell = 4;
    const changed = new Map();
    const draw = () => {
      const w = canvas.clientWidth || 600;
      const dpr = window.devicePixelRatio || 1;
      cell = w / COLS;
      canvas.width = Math.round(w * dpr);
      canvas.height = Math.round(rows * cell * dpr);
      canvas.style.height = `${rows * cell}px`;
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      for (let i = 0; i < size; i++) paint(i);
      tags.forEach(place);
    };
    // A label beside where each move landed in the file.
    const tags = [];
    const place = (t) => {
      const x = (t.off % COLS) * cell;
      const y = Math.floor(t.off / COLS) * cell;
      const right = x > canvas.clientWidth * 0.6;
      t.node.style.top = `${y + cell / 2}px`;
      t.node.classList.toggle("below", y < 24);  // near the top, sit under the bytes instead of over the caption
      t.node.style.left = right ? "" : `${x}px`;
      t.node.style.right = right ? `${canvas.clientWidth - x - cell}px` : "";
    };
    // Colors come from the scheme's CSS tokens, so the map follows whichever scheme is set.
    const css = getComputedStyle(root);
    const color = { good: css.getPropertyValue("--sc-good").trim(), zero: css.getPropertyValue("--sc-map-zero").trim(),
      accent: css.getPropertyValue("--sc-accent").trim() };
    const paint = (i) => {
      const x = (i % COLS) * cell;
      const y = Math.floor(i / COLS) * cell;
      ctx.globalAlpha = 1;
      if (changed.has(i)) {
        ctx.fillStyle = color.good;
      } else if (bytes[i] === 0) {
        ctx.fillStyle = color.zero;
      } else {
        ctx.fillStyle = color.accent;
        ctx.globalAlpha = 0.16 + 0.34 * (bytes[i] / 255);
      }
      ctx.fillRect(x + 0.5, y + 0.5, Math.max(1, cell - 1), Math.max(1, cell - 1));
    };
    draw();
    const onResize = () => { if (canvas.isConnected) draw(); else window.removeEventListener("resize", onResize); };
    window.addEventListener("resize", onResize);

    let total = 0;
    for (const g of groups) {
      const li = el("li", "now");
      const head = el("div", "sc-move-head");
      const add = el("span", "sc-move-n", "+0");
      head.append(el("b", null, g.title), add);
      li.append(head, el("p", null, g.note));
      moves.querySelectorAll("li").forEach((x) => x.classList.remove("now"));
      moves.append(li);
      const tag = { off: g.changed[0][0], node: el("span", "sc-tag", g.title) };
      tags.push(tag);
      mapWrap.append(tag.node);
      place(tag);
      let n = 0;
      for (const [off] of g.changed) {
        changed.set(off, true);
        paint(off);
        n++;
        total++;
        add.textContent = `+${n}`;
        big.textContent = String(total);
        await wait(28, id);
      }
      await wait(900, id);
    }
    moves.querySelectorAll("li").forEach((x) => x.classList.remove("now"));
    big.textContent = "74";

    term.append(el("div", "sc-cmd", out.command));
    const before = el("div", "sc-out old", out.before);
    term.append(before);
    await wait(700, id);
    const after = el("div", "sc-out new", out.after);
    term.append(after);
    term.append(el("div", "sc-term-note", "Original, then patched: a fourth number, the longest line"));
  }

  // ---------- Create ---------------------------------------------------------------------------------------------
  async function create(stage, id) {
    const { bytes, groups } = window.WC391;
    const out = window.SHOWCASE.outputs;
    const regionOf = new Array(bytes.length);
    groups.forEach((g, gi) => { for (let i = g.start; i < g.start + g.len; i++) regionOf[i] = gi; });

    const visual = el("div", "sc-visual");
    const grid = el("div", "sc-hexgrid sc-create");
    const cells = [];
    for (let row = 0; row < bytes.length; row += 16) {
      grid.append(el("span", "sc-addr", addr(0x400000 + row)));
      for (let i = row; i < row + 16; i++) {
        const c = el("span", "sc-b", i < bytes.length ? "··" : "");
        if (i < bytes.length) cells.push(c);
        else c.classList.add("pad");
        grid.append(c);
      }
    }
    visual.append(el("div", "sc-label", "Output: a complete ELF executable, from scratch"), grid);

    const side = el("div", "sc-side");
    const counter = el("div", "sc-counter");
    const big = el("b", null, "0");
    counter.append(big, el("span", null, " of 391 bytes written"));
    const now = el("div", "sc-now");
    const nowRegion = el("div", "sc-now-region");
    const nowLabel = el("div", "sc-now-label");
    const nowNote = el("div", "sc-now-note");
    now.append(nowRegion, nowLabel, nowNote);
    const legend = el("ul", "sc-legend");
    const term = el("div", "sc-term");
    side.append(el("div", "sc-label", "Written by Sol 6.1 in one reply, no assembler"), counter, now, legend, term);
    stage.append(visual, side);

    const seenRegions = new Set();
    let lastGroup = -1;
    for (let i = 0; i < bytes.length; i++) {
      const gi = regionOf[i];
      const g = groups[gi];
      const c = cells[i];
      c.textContent = hex(bytes[i]);
      c.classList.add("on", `r-${g.region}`);
      if (i > 0) cells[i - 1].classList.remove("on");
      big.textContent = String(i + 1);
      if (gi !== lastGroup) {
        lastGroup = gi;
        nowRegion.textContent = REGION[g.region];
        nowRegion.className = `sc-now-region r-${g.region}`;
        nowLabel.textContent = g.label;
        nowNote.textContent = g.note || "";
        if (!seenRegions.has(g.region)) {
          seenRegions.add(g.region);
          const item = el("li", `r-${g.region}`, REGION[g.region]);
          legend.append(item);
        }
      }
      await wait(g.region === "ehdr" || g.region === "phdr" ? 22 : 15, id);
    }
    cells[bytes.length - 1].classList.remove("on");
    now.hidden = true;

    await wait(500, id);
    term.append(el("div", "sc-cmd", out.command));
    await wait(500, id);
    term.append(el("div", "sc-out new", out.after));
    term.append(el("div", "sc-term-note", "Same output as GCC's build, which is 5,432 bytes"));
  }

  const TASKS = { understand, extend, create };
  const ORDER = ["understand", "extend", "create"];

  async function play(root, name) {
    const id = ++run;
    current = name;
    root.querySelectorAll(".sc-tabs [data-sc]").forEach((t) => {
      const on = t.dataset.sc === name;
      t.setAttribute("aria-selected", String(on));
      t.tabIndex = on ? 0 : -1;
    });
    const stage = root.querySelector(".sc-stage");
    stage.replaceChildren();
    stage.setAttribute("aria-labelledby", `sc-tab-${name}`);
    stage.classList.toggle("is-static", reduce.matches);
    try {
      await TASKS[name](stage, id);
      if (auto && !reduce.matches) {
        await wait(2600, id);
        const next = ORDER[ORDER.indexOf(name) + 1];
        if (next) play(root, next);
      }
    } catch (e) {
      if (e.message !== "stopped") throw e;
    }
  }

  document.addEventListener("click", (event) => {
    const tab = event.target.closest(".sc-tabs [data-sc]");
    const replay = event.target.closest("#showcase .sc-replay");
    if (!tab && !replay) return;
    const root = event.target.closest(".sc");
    auto = false;
    play(root, tab ? tab.dataset.sc : current);
  });

  // Arrow keys move between tabs, as in the ARIA tabs pattern.
  document.addEventListener("keydown", (event) => {
    const tab = event.target.closest && event.target.closest(".sc-tabs [data-sc]");
    if (!tab || !["ArrowLeft", "ArrowRight", "Home", "End"].includes(event.key)) return;
    event.preventDefault();
    const i = ORDER.indexOf(tab.dataset.sc);
    const j = event.key === "Home" ? 0 : event.key === "End" ? ORDER.length - 1
      : (i + (event.key === "ArrowRight" ? 1 : ORDER.length - 1)) % ORDER.length;
    const root = tab.closest(".sc");
    auto = false;
    play(root, ORDER[j]);
    root.querySelector(`[data-sc="${ORDER[j]}"]`).focus();
  });

  // The Distill template re-renders the article after load, so set up once that is done, and start playing the
  // first time the showcase scrolls into view.
  window.addEventListener("load", () => {
    const setup = () => {
      const root = document.querySelector("#showcase .sc");
      if (!root || root.dataset.ready || !window.SHOWCASE || !window.WC391) return;
      root.dataset.ready = "1";
      const io = new IntersectionObserver((entries) => {
        if (entries.some((e) => e.isIntersecting)) {
          io.disconnect();
          if (run === 0) play(root, "understand");  // unless the reader already picked a tab
        }
      }, { threshold: 0.25 });
      io.observe(root);
    };
    setup();
    setTimeout(setup, 300);
    setTimeout(setup, 1200);
  });
})();
