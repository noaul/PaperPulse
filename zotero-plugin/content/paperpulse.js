var PaperPulse = PaperPulse || {};

PaperPulse.ZoteroAnalyzer = class {
  constructor(rootURI) {
    this.rootURI = rootURI;
    this.pluginID = "paperpulse-zotero-analyzer@uovme.github.io";
    this.preferencePaneID = "paperpulse-zotero-analyzer-preferences";
    this.preferencePaneRegistered = false;
    this.menuItemsByWindow = new Map();
  }

  async startup() {
    this.registerPrefs();
    for (const window of Zotero.getMainWindows()) {
      await this.safeRun("register window menu", () => this.onMainWindowLoad(window));
    }
    await this.safeRun("register preference pane", () => this.registerPreferencePane());
  }

  async shutdown() {
    for (const items of this.menuItemsByWindow.values()) {
      for (const item of items) {
        item.remove();
      }
    }
    this.menuItemsByWindow.clear();
    if (this.preferencePaneRegistered && Zotero.PreferencePanes?.unregister) {
      Zotero.PreferencePanes.unregister(this.preferencePaneID);
      this.preferencePaneRegistered = false;
    }
  }

  async safeRun(label, fn) {
    try {
      return await fn();
    } catch (error) {
      Zotero.logError(error);
      Zotero.debug(`[PaperPulse] failed to ${label}: ${error}`);
      return null;
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

  onMainWindowLoad(window) {
    this.registerLegacyMenu(window);
  }

  onMainWindowUnload(window) {
    const items = this.menuItemsByWindow.get(window);
    if (!items) {
      return;
    }
    for (const item of items) {
      item.remove();
    }
    this.menuItemsByWindow.delete(window);
  }

  registerLegacyMenu(window) {
    const document = window.document;
    const menu = document.getElementById("menu_ToolsPopup");
    if (!menu || document.getElementById("paperpulse-tools-menu")) {
      return;
    }

    const submenu = document.createXULElement("menu");
    submenu.id = "paperpulse-tools-menu";
    submenu.setAttribute("label", "PaperPulse");

    const popup = document.createXULElement("menupopup");
    const analyzeItem = this.createMenuItem(document, "paperpulse-analyze-selected", "Analyze Selected Items");
    analyzeItem.addEventListener("command", () => this.analyzeSelectedItems());
    const settingsItem = this.createMenuItem(document, "paperpulse-settings", "Settings");
    settingsItem.addEventListener("command", () => this.openSettings());

    popup.appendChild(analyzeItem);
    popup.appendChild(settingsItem);
    submenu.appendChild(popup);
    menu.appendChild(submenu);
    this.menuItemsByWindow.set(window, [submenu]);
  }

  createMenuItem(document, id, label) {
    const item = document.createXULElement("menuitem");
    item.id = id;
    item.setAttribute("label", label);
    return item;
  }

  async registerPreferencePane() {
    if (!Zotero.PreferencePanes?.register) {
      Zotero.debug("[PaperPulse] Zotero.PreferencePanes.register is unavailable");
      return;
    }

    this.preferencePaneID = await Zotero.PreferencePanes.register({
      pluginID: this.pluginID,
      id: this.preferencePaneID,
      label: "PaperPulse",
      src: `${this.rootURI}prefs.xhtml`,
      scripts: [`${this.rootURI}content/preferences.js`],
      stylesheets: [`${this.rootURI}content/preferences.css`],
      helpURL: "https://github.com/uovme/PaperPulse/tree/main/zotero-plugin",
    });
    this.preferencePaneRegistered = true;
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

  setBackendURL(value) {
    this.getPrefBranch().setStringPref("backendURL", String(value || "").trim() || "http://127.0.0.1:18095");
  }

  setAuthToken(value) {
    this.getPrefBranch().setStringPref("authToken", String(value || "").trim());
  }

  setMinScoreToTag(value) {
    const parsed = Number.parseInt(value, 10);
    const normalized = Number.isFinite(parsed) ? Math.max(0, Math.min(10, parsed)) : 5;
    this.getPrefBranch().setIntPref("minScoreToTag", normalized);
  }

  setAddNote(value) {
    this.getPrefBranch().setBoolPref("addNote", !!value);
  }

  setAddTags(value) {
    this.getPrefBranch().setBoolPref("addTags", !!value);
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

  openSettings() {
    if (this.preferencePaneRegistered && Zotero.Utilities?.Internal?.openPreferences) {
      try {
        Zotero.Utilities.Internal.openPreferences(this.preferencePaneID);
        return;
      } catch (error) {
        Zotero.logError(error);
        Zotero.debug(`[PaperPulse] failed to open preferences pane: ${error}`);
      }
    }
    this.openSettingsDialog();
  }

  openSettingsDialog() {
    const prompts = Services.prompt;
    const backend = { value: this.getBackendURL() };
    if (!prompts.prompt(null, "PaperPulse Settings", "Backend URL", backend, null, {})) {
      return;
    }
    const token = { value: this.getAuthToken() };
    if (!prompts.promptPassword(null, "PaperPulse Settings", "Auth token (leave empty if not required)", token, null, {})) {
      return;
    }
    const minScore = { value: String(this.getMinScoreToTag()) };
    if (!prompts.prompt(null, "PaperPulse Settings", "Minimum tag score (0-10)", minScore, null, {})) {
      return;
    }
    const addTags = { value: this.shouldAddTags() };
    prompts.confirmCheck(
      null,
      "PaperPulse Settings",
      "Write PaperPulse tags to analyzed items.",
      "Enable tag write-back",
      addTags
    );
    const addNote = { value: this.shouldAddNote() };
    prompts.confirmCheck(
      null,
      "PaperPulse Settings",
      "Add a PaperPulse analysis child note.",
      "Enable note write-back",
      addNote
    );

    this.setBackendURL(backend.value);
    this.setAuthToken(token.value);
    this.setMinScoreToTag(minScore.value);
    this.setAddTags(addTags.value);
    this.setAddNote(addNote.value);
    this.alert("PaperPulse", "Settings saved.");
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
