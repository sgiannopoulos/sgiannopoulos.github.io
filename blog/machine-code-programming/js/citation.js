// Copy buttons in the Citation section: each one copies the text of the <pre> right after it.
(() => {
  const LABEL = "Copy";
  const RESET_MS = 2000;

  const addCopyBehavior = (button) => {
    let resetTimer;
    button.addEventListener("click", async () => {
      try {
        await navigator.clipboard.writeText(button.nextElementSibling.textContent);
        button.textContent = "Copied";
      } catch {
        button.textContent = "Copy failed";
      }
      clearTimeout(resetTimer);
      resetTimer = setTimeout(() => {
        button.textContent = LABEL;
      }, RESET_MS);
    });
  };

  document.addEventListener("DOMContentLoaded", () => {
    document.querySelectorAll(".citation-copy").forEach(addCopyBehavior);
  });
})();
