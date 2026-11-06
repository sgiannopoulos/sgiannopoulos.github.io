// Title band: fills the background with the bytes of the 391-byte executable Sol 6.1 wrote (assets/wc391.js), as hex.
// Decorative only, so it is hidden from assistive technology; the visible .hero-note says what it is.
(() => {
  const fill = () => {
    const title = document.querySelector("d-title");
    const data = window.WC391;
    if (!title || !data || title.querySelector(".hero-hex")) return;
    const hex = data.bytes.map((b) => b.toString(16).padStart(2, "0")).join(" ");
    const layer = document.createElement("div");
    layer.className = "hero-hex";
    layer.setAttribute("aria-hidden", "true");
    // Repeat so the field covers wide screens; the first pass is the file from its first byte.
    layer.textContent = `${hex} ${hex} ${hex}`;
    title.prepend(layer);
  };
  window.addEventListener("load", () => {
    fill();
    setTimeout(fill, 300);
    setTimeout(fill, 1200);
  });
})();
