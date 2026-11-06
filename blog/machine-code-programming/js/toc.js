// Contents list in the left margin: one link for each h2 with an id, marking the section being read.
// css/style.css shows it only on screens with a margin wide enough to hold it.
(() => {
  // A heading counts as the current section once its top is this close to the top of the window.
  // Keep it below the shortest section's height, so that following a link marks that link's section.
  const READING_LINE_PX = 200;
  const REALIGN_LIMIT_MS = 10000;

  // The run viewers fill in after load and push later headings down, and not every browser keeps the view in place
  // when that happens. So a link that opens the post at a section stays on that heading until the article stops
  // growing or the reader takes over. A reload or back/forward keeps the position the browser restored.
  const holdLinkedSection = (article) => {
    const target = document.getElementById(location.hash.slice(1));
    const [entry] = performance.getEntriesByType("navigation");
    if (!target || entry?.type !== "navigate") return;

    const observer = new ResizeObserver(() => target.scrollIntoView());
    const inputs = ["wheel", "touchstart", "pointerdown", "keydown"];
    const stop = () => {
      observer.disconnect();
      inputs.forEach((type) => window.removeEventListener(type, stop));
    };
    inputs.forEach((type) => window.addEventListener(type, stop, { passive: true }));
    setTimeout(stop, REALIGN_LIMIT_MS);
    observer.observe(article);
  };

  const build = () => {
    const article = document.querySelector("d-article");
    const headings = [...article.querySelectorAll("h2[id]")];

    const nav = document.createElement("nav");
    nav.className = "toc";
    nav.setAttribute("aria-labelledby", "toc-title");

    const inner = document.createElement("div");
    inner.className = "toc-inner";

    const title = document.createElement("div");
    title.className = "toc-title";
    title.id = "toc-title";
    title.textContent = "Contents";

    const list = document.createElement("ol");
    const links = headings.map((heading) => {
      const link = document.createElement("a");
      link.href = `#${heading.id}`;
      link.textContent = heading.textContent;
      const item = document.createElement("li");
      item.append(link);
      list.append(item);
      return link;
    });

    inner.append(title, list);
    nav.append(inner);
    article.prepend(nav);

    const mark = () => {
      let current = -1;
      headings.forEach((heading, i) => {
        if (heading.getBoundingClientRect().top <= READING_LINE_PX) current = i;
      });
      links.forEach((link, i) => {
        if (i === current) link.setAttribute("aria-current", "true");
        else link.removeAttribute("aria-current");
      });
    };

    window.addEventListener("scroll", mark, { passive: true });
    window.addEventListener("resize", mark);
    // Figures and citations change the page's height as they load.
    window.addEventListener("load", mark);
    mark();

    holdLinkedSection(article);
  };

  document.addEventListener("DOMContentLoaded", build);
})();
