var PaperPulseZoteroAnalyzer;
var chromeHandle;

function log(message) {
  Zotero.debug(`[PaperPulse] ${message}`);
}

async function install() {}

async function startup({ id, resourceURI, rootURI }) {
  await Zotero.initializationPromise;
  if (!rootURI) {
    rootURI = resourceURI.spec;
  }

  const aomStartup = Components.classes[
    "@mozilla.org/addons/addon-manager-startup;1"
  ].getService(Components.interfaces.amIAddonManagerStartup);
  const manifestURI = Services.io.newURI(`${rootURI}manifest.json`);
  chromeHandle = aomStartup.registerChrome(manifestURI, [
    ["content", "paperpulse", `${rootURI}content/`],
  ]);

  const ctx = { rootURI };
  ctx._globalThis = ctx;
  Services.scriptloader.loadSubScript(`${rootURI}content/paperpulse.js`, ctx);
  PaperPulseZoteroAnalyzer = new ctx.PaperPulse.ZoteroAnalyzer(rootURI);
  await PaperPulseZoteroAnalyzer.startup();
  log("started");
}

async function onMainWindowLoad({ window }) {
  PaperPulseZoteroAnalyzer?.onMainWindowLoad(window);
}

async function onMainWindowUnload({ window }) {
  PaperPulseZoteroAnalyzer?.onMainWindowUnload(window);
}

async function shutdown(data, reason) {
  if (reason === APP_SHUTDOWN) {
    return;
  }
  if (PaperPulseZoteroAnalyzer) {
    await PaperPulseZoteroAnalyzer.shutdown();
    PaperPulseZoteroAnalyzer = null;
  }
  if (chromeHandle) {
    chromeHandle.destruct();
    chromeHandle = null;
  }
  log("stopped");
}

async function uninstall() {}
