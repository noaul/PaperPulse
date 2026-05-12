$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
$dist = Join-Path $root "dist"
$xpi = Join-Path $dist "paperpulse-zotero-analyzer.xpi"
$zip = Join-Path $dist "paperpulse-zotero-analyzer.zip"

if (Test-Path $dist) {
  Remove-Item -LiteralPath $dist -Recurse -Force
}
New-Item -ItemType Directory -Path $dist | Out-Null

$files = @(
  "manifest.json",
  "bootstrap.js",
  "prefs.js",
  "prefs.xhtml",
  "README.md",
  "content\paperpulse.js",
  "content\preferences.js",
  "content\preferences.css"
)

$temp = Join-Path $dist "package"
New-Item -ItemType Directory -Path $temp | Out-Null
New-Item -ItemType Directory -Path (Join-Path $temp "content") | Out-Null

foreach ($file in $files) {
  Copy-Item -LiteralPath (Join-Path $root $file) -Destination (Join-Path $temp $file)
}

Compress-Archive -Path (Join-Path $temp "*") -DestinationPath $zip -Force
Move-Item -LiteralPath $zip -Destination $xpi -Force
Remove-Item -LiteralPath $temp -Recurse -Force

Write-Output "Built $xpi"
