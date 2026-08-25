param([int]$Port = 3307)

$ErrorActionPreference = "Stop"
$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$runtimeRoot = Join-Path $projectRoot "work/mysql-runtime"
$serverRoot = Join-Path $runtimeRoot "mysql-8.4.11-winx64"
$configPath = Join-Path $runtimeRoot "my.ini"
$mysqldPath = Join-Path $serverRoot "bin/mysqld.exe"
$mysqlPath = Join-Path $serverRoot "bin/mysql.exe"
$mysqlAdminPath = Join-Path $serverRoot "bin/mysqladmin.exe"

if (-not (Test-Path -LiteralPath $mysqldPath)) {
    throw "MySQL runtime is missing. Run .\scripts\setup_mysql84_portable.ps1 first."
}

function Test-MySqlReady {
    $savedPreference = $ErrorActionPreference
    $ErrorActionPreference = "SilentlyContinue"
    try {
        & $mysqlAdminPath '--protocol=TCP' '--host=127.0.0.1' "--port=$Port" '--user=root' '--connect-timeout=2' ping 2>$null | Out-Null
        return $LASTEXITCODE -eq 0
    }
    finally {
        $ErrorActionPreference = $savedPreference
    }
}

if (-not (Test-MySqlReady)) {
    $mysqlProcess = Start-Process -FilePath $mysqldPath -ArgumentList "--defaults-file=$configPath" -WindowStyle Hidden -PassThru
    $isReady = $false
    for ($attempt = 1; $attempt -le 30; $attempt++) {
        Start-Sleep -Seconds 1
        $isReady = Test-MySqlReady
        if ($isReady) { break }
        if ($mysqlProcess.HasExited) { throw "mysqld exited during startup" }
    }
    if (-not $isReady) { throw "MySQL did not become ready within 30 seconds" }
}

$bootstrapSql = @"
CREATE DATABASE IF NOT EXISTS careguard_test CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;
CREATE USER IF NOT EXISTS 'careguard'@'localhost' IDENTIFIED BY 'careguard_test';
ALTER USER 'careguard'@'localhost' IDENTIFIED BY 'careguard_test';
CREATE USER IF NOT EXISTS 'careguard'@'127.0.0.1' IDENTIFIED BY 'careguard_test';
ALTER USER 'careguard'@'127.0.0.1' IDENTIFIED BY 'careguard_test';
GRANT SELECT, INSERT, UPDATE, DELETE, CREATE, DROP, ALTER, INDEX, REFERENCES ON careguard_test.* TO 'careguard'@'localhost';
GRANT SELECT, INSERT, UPDATE, DELETE, CREATE, DROP, ALTER, INDEX, REFERENCES ON careguard_test.* TO 'careguard'@'127.0.0.1';
FLUSH PRIVILEGES;
"@
& $mysqlPath '--protocol=TCP' '--host=127.0.0.1' "--port=$Port" '--user=root' "--execute=$bootstrapSql"
if ($LASTEXITCODE -ne 0) { throw "Failed to create the isolated CareGuard test database" }

& $mysqlPath '--protocol=TCP' '--host=127.0.0.1' "--port=$Port" '--user=careguard' '--password=careguard_test' '--database=careguard_test' '--skip-column-names' '--execute=SELECT VERSION(), @@port, DATABASE(), @@character_set_database, @@collation_database;'
Write-Output "DATABASE_URL=mysql+pymysql://careguard:careguard_test@127.0.0.1:$Port/careguard_test?charset=utf8mb4"
