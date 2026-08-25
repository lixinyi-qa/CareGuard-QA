$ErrorActionPreference = "Stop"
$env:RUN_UI_TESTS = "1"
if (-not $env:BASE_URL) { $env:BASE_URL = "http://127.0.0.1:8000" }
if (-not $env:PLAYWRIGHT_EXECUTABLE_PATH) {
    $chromePath = "C:\Program Files\Google\Chrome\Application\chrome.exe"
    $edgePath = "C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
    if (Test-Path -LiteralPath $chromePath) { $env:PLAYWRIGHT_EXECUTABLE_PATH = $chromePath }
    elseif (Test-Path -LiteralPath $edgePath) { $env:PLAYWRIGHT_EXECUTABLE_PATH = $edgePath }
}
python -m pytest tests/ui -m ui -v
