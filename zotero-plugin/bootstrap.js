var PaperPulseZoteroAnalyzer;

function log(message) {
  Zotero.debug(`[PaperPulse] ${message}`);
}

async function install() {}

async function startup({ rootURI }) {
  Services.scriptloader.loadSubScript(`${rootURI}content/paperpulse.js`);
  PaperPulseZoteroAnalyzer = new PaperPulse.ZoteroAnalyzer(rootURI);
  await PaperPulseZoteroAnalyzer.startup();
  log("started");
}

async function shutdown() {
  if (PaperPulseZoteroAnalyzer) {
    await PaperPulseZoteroAnalyzer.shutdown();
    PaperPulseZoteroAnalyzer = null;
  }
  log("stopped");
}

async function uninstall() {}
