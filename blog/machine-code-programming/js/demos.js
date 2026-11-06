// Figure 1: tabs that switch between before/after pairs of terminal GIFs. Each pair shares one timeline, so both
// images are fetched first and then assigned together, which starts them in step. A pair loads only when its tab
// is opened. Event delegation keeps this working after the Distill template re-renders the article.
(() => {
  const show = (root, which) => {
    root.querySelectorAll(".demo-tabs [data-demo]").forEach((t) => {
      t.setAttribute("aria-selected", String(t.dataset.demo === which));
    });
    root.querySelectorAll(".demo-pair").forEach((pair) => {
      const on = pair.dataset.demo === which;
      pair.hidden = !on;
      const imgs = [...pair.querySelectorAll("img")];
      if (on) {
        Promise.all(imgs.map((img) => new Promise((done) => {
          const pre = new Image();
          pre.onload = pre.onerror = done;
          pre.src = img.dataset.src;
        }))).then(() => {
          // Re-adding the src restarts both GIFs from their first frame, together.
          imgs.forEach((img) => { img.removeAttribute("src"); });
          requestAnimationFrame(() => imgs.forEach((img) => { img.src = img.dataset.src; }));
        });
      } else {
        imgs.forEach((img) => img.removeAttribute("src"));
      }
    });
  };

  document.addEventListener("click", (event) => {
    const tab = event.target.closest(".demo-tabs [data-demo]");
    if (tab) show(tab.closest(".demos"), tab.dataset.demo);
  });

  // The Distill template re-renders the article after load, so start the first pair once that is done.
  window.addEventListener("load", () => {
    const start = () => {
      const root = document.querySelector(".demos");
      if (root && !root.querySelector(".demo-pair img[src]")) show(root, "0");
    };
    start();
    setTimeout(start, 300);
    setTimeout(start, 1200);
  });
})();
