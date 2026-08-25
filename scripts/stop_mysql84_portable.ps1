param([int]$Port = 3307)

$ErrorActionPreference = "Stop"
$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$mysqlAdminPath = Join-Path $projectRoot "work/mysql-runtime/mysql-8.4.11-winx64/bin/mysqladmin.exe"

if (-not (Test-Path -LiteralPath $mysqlAdminPath)) {
    throw "Portable MySQL runtime was not found."
}

& $mysqlAdminPath '--protocol=TCP' '--host=127.0.0.1' "--port=$Port" '--user=root' shutdown
if ($LASTEXITCODE -ne 0) { throw "MySQL shutdown failed" }
Write-Output "Portable MySQL on port $Port stopped cleanly."
