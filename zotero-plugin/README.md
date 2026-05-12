# PaperPulse Zotero Analyzer

Zotero 9 plugin prototype for sending selected Zotero items to a PaperPulse backend, then writing the AI score, tags, and an analysis note back to Zotero.

## What It Does

- Adds `Tools -> PaperPulse: Analyze Selected Items`.
- Adds `Tools -> PaperPulse: Settings` for backend URL, auth token, minimum tag score, and write-back options.
- Reads selected regular Zotero items, including feed-saved items.
- Sends title, abstract, URL, DOI, authors, tags, and Zotero key to `POST /api/zotero/analyze`.
- Adds `PaperPulse:*` tags when the returned score is high enough.
- Adds a child note containing the PaperPulse AI analysis.

## Configuration

Defaults are in `prefs.js`:

- `extensions.paperpulse.backendURL`: `http://127.0.0.1:18095`
- `extensions.paperpulse.authToken`: empty by default. Set this to the PaperPulse auth token if your instance has an admin user.
- `extensions.paperpulse.minScoreToTag`: `5`
- `extensions.paperpulse.addNote`: `true`
- `extensions.paperpulse.addTags`: `true`

You can edit these values from Zotero via `Tools -> PaperPulse: Settings`.

## Build an XPI

From this folder:

```bash
powershell -ExecutionPolicy Bypass -File .\scripts\build-xpi.ps1
```

The output file is `dist/paperpulse-zotero-analyzer.xpi`.

## Install for Testing

In Zotero 9:

1. Open `Tools -> Add-ons`.
2. Use the gear menu and choose `Install Add-on From File...`.
3. Select `dist/paperpulse-zotero-analyzer.xpi`.
4. Restart Zotero if requested.

## Notes

This plugin delegates AI analysis to PaperPulse. It does not store AI API keys in Zotero and does not call OpenAI-compatible providers directly.
