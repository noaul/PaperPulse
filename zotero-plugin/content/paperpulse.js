var PaperPulse = PaperPulse || {};

PaperPulse.ZoteroAnalyzer = class {
  constructor(rootURI) {
    this.rootURI = rootURI;
    this.menuItem = null;
  }

  async startup() {
    this.registerPrefs();
    this.registerMenu();
  }

  async shutdown() {
    if (this.menuItem) {
      this.menuItem.remove();
      this.menuItem = null;
    }
  }

  registerPrefs() {
    const branch = Services.prefs.getBranch("extensions.paperpulse.");
    if (branch.getPrefType("backendURL") === branch.PREF_INVALID) {
      branch.setStringPref("backendURL", "http://127.0.0.1:18095");
    }
    if (branch.getPrefType("authToken") === branch.PREF_INVALID) {
      branch.setStringPref("authToken", "");
    }
    if (branch.getPrefType("minScoreToTag") === branch.PREF_INVALID) {
      branch.setIntPref("minScoreToTag", 5);
    }
    if (branch.getPrefType("addNote") === branch.PREF_INVALID) {
      branch.setBoolPref("addNote", true);
    }
    if (branch.getPrefType("addTags") === branch.PREF_INVALID) {
      branch.setBoolPref("addTags", true);
    }
  }

  registerMenu() {
    const document = Zotero.getMainWindow().document;
    const menu = document.getElementById("menu_ToolsPopup");
    if (!menu || document.getElementById("paperpulse-analyze-selected")) {
      return;
    }

    this.menuItem = document.createXULElement("menuitem");
    this.menuItem.id = "paperpulse-analyze-selected";
    this.menuItem.setAttribute("label", "PaperPulse: Analyze Selected Items");
    this.menuItem.addEventListener("command", () => this.analyzeSelectedItems());
    menu.appendChild(this.menuItem);
  }

  getPrefBranch() {
    return Services.prefs.getBranch("extensions.paperpulse.");
  }

  getBackendURL() {
    return this.getPrefBranch().getStringPref("backendURL", "http://127.0.0.1:18095").replace(/\/+$/, "");
  }

  getAuthToken() {
    return this.getPrefBranch().getStringPref("authToken", "");
  }

  shouldAddNote() {
    return this.getPrefBranch().getBoolPref("addNote", true);
  }

  shouldAddTags() {
    return this.getPrefBranch().getBoolPref("addTags", true);
  }

  getMinScoreToTag() {
    return this.getPrefBranch().getIntPref("minScoreToTag", 5);
  }

  getSelectedItems() {
    const pane = Zotero.getActiveZoteroPane();
    if (!pane) {
      return [];
    }
    return pane.getSelectedItems().filter((item) => item && item.isRegularItem());
  }

  async analyzeSelectedItems() {
    const items = this.getSelectedItems();
    if (!items.length) {
      this.alert("PaperPulse", "No regular Zotero items selected.");
      return;
    }

    let analyzed = 0;
    let failed = 0;
    for (const item of items) {
      try {
        await this.analyzeItem(item);
        analyzed += 1;
      } catch (error) {
        failed += 1;
        Zotero.debug(`[PaperPulse] failed to analyze ${item.key}: ${error}`);
      }
    }

    this.alert("PaperPulse", `Analyzed ${analyzed} item(s). Failed: ${failed}.`);
  }

  async analyzeItem(item) {
    const response = await this.callPaperPulse(item);
    await this.writeBack(item, response);
    return response;
  }

  async callPaperPulse(item) {
    const url = `${this.getBackendURL()}/api/zotero/analyze`;
    const headers = {
      "Content-Type": "application/json",
    };
    const token = this.getAuthToken();
    if (token) {
      headers.Authorization = `Bearer ${token}`;
    }

    const response = await fetch(url, {
      method: "POST",
      headers,
      body: JSON.stringify(this.serializeItem(item)),
    });

    if (!response.ok) {
      const text = await response.text();
      throw new Error(`PaperPulse ${response.status}: ${text}`);
    }
    return response.json();
  }

  serializeItem(item) {
    return {
      zotero_key: item.key,
      title: item.getField("title") || "Untitled",
      abstract: item.getField("abstractNote") || "",
      url: item.getField("url") || "",
      doi: item.getField("DOI") || "",
      authors: this.creatorsToText(item),
      tags: item.getTags().map((tag) => tag.tag),
    };
  }

  creatorsToText(item) {
    return item.getCreators()
      .map((creator) => {
        if (creator.name) return creator.name;
        return [creator.firstName, creator.lastName].filter(Boolean).join(" ");
      })
      .filter(Boolean)
      .join(", ");
  }

  async writeBack(item, analysis) {
    if (this.shouldAddTags() && analysis.relevance_score >= this.getMinScoreToTag()) {
      for (const tag of analysis.zotero_tags || []) {
        item.addTag(tag);
      }
    }
    await item.saveTx();

    if (this.shouldAddNote() && analysis.note_html) {
      const note = new Zotero.Item("note");
      note.libraryID = item.libraryID;
      note.parentID = item.id;
      note.setNote(analysis.note_html);
      await note.saveTx();
    }
  }

  alert(title, text) {
    const promptService = Services.prompt;
    promptService.alert(null, title, text);
  }
};
