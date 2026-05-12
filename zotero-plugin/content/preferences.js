Zotero.PaperPulse_Preferences = {
  init(event) {
    Zotero.debug("[PaperPulse] preferences pane loaded");
    const doc = event?.target?.ownerDocument;
    const minScore = doc?.getElementById("paperpulse-min-score");
    minScore?.addEventListener("change", () => {
      const parsed = Number.parseInt(minScore.value, 10);
      if (!Number.isFinite(parsed)) {
        minScore.value = "5";
        return;
      }
      minScore.value = String(Math.max(0, Math.min(10, parsed)));
    });
  },
};
