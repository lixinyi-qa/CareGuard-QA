param(
    [int]$Port = 3307,
    [int]$Connections = 24
)

$ErrorActionPreference = "Stop"
$mysqlVersion = "8.4.11"
$mysqlArchiveName = "mysql-$mysqlVersion-winx64.zip"
$mysqlUrl = "https://cdn.mysql.com/Downloads/MySQL-8.4/$mysqlArchiveName"
$mysqlContentLength = 281191914
$mysqlExpectedMd5 = "2e833921898a9a030ea6bfe81bd811bc"
$mysqlExpectedSha256 = "a492371d687d2bab088b0062581144a0044b8964baefdf4faa579292b423d25c"

$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$runtimeRoot = Join-Path $projectRoot "work/mysql-runtime"
$archivePath = Join-Path $runtimeRoot $mysqlArchiveName
$serverRoot = Join-Path $runtimeRoot "mysql-$mysqlVersion-winx64"
$dataRoot = Join-Path $runtimeRoot "data"
$secureRoot = Join-Path $runtimeRoot "secure"
$partsRoot = Join-Path $runtimeRoot "parts"
$configPath = Join-Path $runtimeRoot "my.ini"

New-Item -ItemType Directory -Force -Path $runtimeRoot, $secureRoot | Out-Null

function Test-Archive {
    if (-not (Test-Path -LiteralPath $archivePath)) { return $false }
    if ((Get-Item -LiteralPath $archivePath).Length -ne $mysqlContentLength) { return $false }
    $actualMd5 = (Get-FileHash -Algorithm MD5 -LiteralPath $archivePath).Hash.ToLowerInvariant()
    $actualSha256 = (Get-FileHash -Algorithm SHA256 -LiteralPath $archivePath).Hash.ToLowerInvariant()
    return $actualMd5 -eq $mysqlExpectedMd5 -and $actualSha256 -eq $mysqlExpectedSha256
}

if (-not (Test-Archive)) {
    Write-Output "Downloading official MySQL $mysqlVersion in $Connections verified parts..."
    New-Item -ItemType Directory -Force -Path $partsRoot | Out-Null
    $chunkSize = [long][Math]::Ceiling($mysqlContentLength / $Connections)
    $downloads = @()

    for ($index = 0; $index -lt $Connections; $index++) {
        $start = [long]$index * $chunkSize
        $end = [Math]::Min($mysqlContentLength - 1, $start + $chunkSize - 1)
        if ($start -gt $end) { break }
        $partPath = Join-Path $partsRoot ("part-{0:D3}.bin" -f $index)
        $expectedLength = $end - $start + 1
        if ((Test-Path -LiteralPath $partPath) -and ((Get-Item $partPath).Length -eq $expectedLength)) {
            continue
        }
        $curlArguments = @(
            "-L", "--fail", "--silent", "--show-error", "--retry", "5",
            "--range", "$start-$end", "--output", $partPath, $mysqlUrl
        )
        $process = Start-Process -FilePath "curl.exe" -ArgumentList $curlArguments -WindowStyle Hidden -PassThru
        $downloads += [PSCustomObject]@{
            Index = $index
            Process = $process
            Path = $partPath
            ExpectedLength = $expectedLength
        }
    }

    do {
        $running = @($downloads | Where-Object { -not $_.Process.HasExited })
        Write-Output "Download progress: $($Connections - $running.Count)/$Connections parts finished"
        if ($running.Count -gt 0) { Start-Sleep -Seconds 5 }
    } while ($running.Count -gt 0)

    foreach ($download in $downloads) {
        if ($download.Process.ExitCode -ne 0) {
            throw "curl failed for part $($download.Index)"
        }
    }

    $outputStream = [System.IO.File]::Open(
        $archivePath,
        [System.IO.FileMode]::Create,
        [System.IO.FileAccess]::Write
    )
    try {
        for ($index = 0; $index -lt $Connections; $index++) {
            $partPath = Join-Path $partsRoot ("part-{0:D3}.bin" -f $index)
            $start = [long]$index * $chunkSize
            $end = [Math]::Min($mysqlContentLength - 1, $start + $chunkSize - 1)
            $expectedLength = $end - $start + 1
            if (-not (Test-Path -LiteralPath $partPath)) { throw "Missing part $index" }
            if ((Get-Item $partPath).Length -ne $expectedLength) {
                throw "Unexpected size for part $index"
            }
            $inputStream = [System.IO.File]::OpenRead($partPath)
            try { $inputStream.CopyTo($outputStream) } finally { $inputStream.Dispose() }
        }
    }
    finally {
        $outputStream.Dispose()
    }
}

if (-not (Test-Archive)) {
    throw "MySQL archive hash verification failed"
}
Write-Output "Archive verified (MD5 and SHA-256)."

if (-not (Test-Path -LiteralPath (Join-Path $serverRoot "bin/mysqld.exe"))) {
    & tar.exe -xf $archivePath -C $runtimeRoot
    if ($LASTEXITCODE -ne 0) { throw "Failed to extract MySQL archive" }
}

$normalizedServerRoot = $serverRoot.Replace("\", "/")
$normalizedDataRoot = $dataRoot.Replace("\", "/")
$normalizedSecureRoot = $secureRoot.Replace("\", "/")
$normalizedRuntimeRoot = $runtimeRoot.Replace("\", "/")
$configLines = @(
    "[mysqld]",
    "basedir=$normalizedServerRoot",
    "datadir=$normalizedDataRoot",
    "port=$Port",
    "bind-address=127.0.0.1",
    "mysqlx=0",
    "character-set-server=utf8mb4",
    "collation-server=utf8mb4_0900_ai_ci",
    "default-time-zone=+08:00",
    "log-error=$normalizedRuntimeRoot/mysql-error.log",
    "pid-file=$normalizedRuntimeRoot/mysql.pid",
    "secure-file-priv=$normalizedSecureRoot"
)
[System.IO.File]::WriteAllLines(
    $configPath,
    $configLines,
    [System.Text.UTF8Encoding]::new($false)
)

New-Item -ItemType Directory -Force -Path $dataRoot | Out-Null
if (-not (Test-Path -LiteralPath (Join-Path $dataRoot "mysql.ibd"))) {
    $mysqldPath = Join-Path $serverRoot "bin/mysqld.exe"
    & $mysqldPath "--defaults-file=$configPath" --initialize-insecure --console
    if ($LASTEXITCODE -ne 0) { throw "MySQL data directory initialization failed" }
}

$serverVersion = & (Join-Path $serverRoot "bin/mysqld.exe") --version
Write-Output $serverVersion
Write-Output "Portable MySQL is ready. Start it with: .\scripts\start_mysql84_portable.ps1"
