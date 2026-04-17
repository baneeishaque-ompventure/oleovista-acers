#!pwsh
#Requires -Version 5.1

<#
.SYNOPSIS
    Industrial Local Database Restoration Tool.
    Compatible with PowerShell Core (Mac/Linux/Windows).

.DESCRIPTION
    Automates restoring a raw PostgreSQL custom (.dump) file directly into the local environment.
    1. Reads the local 'acers/.env' to safely extract the DATABASE_URL.
    2. Auto-discovers the latest .dump file from 'db_dumps' if not explicitly provided.
    3. Flushes the local database schemas securely and streams the restoration payload.
#>

Param (
    [string]$DumpFile = "",
    [string]$LocalEnvPath = "$PSScriptRoot/../../acers/.env",
    [string]$EnvDbKey = "DATABASE_URL"
)

$ErrorActionPreference = "Stop"

# Constants
Set-Variable -Name PG_RESTORE -Value "pg_restore" -Option Constant

function Write-Message {
    param([string]$Message, [string]$Color = "White")
    $Timestamp = Get-Date -Format "HH:mm:ss"
    Write-Host "[$Timestamp] $Message" -ForegroundColor $Color
}

Write-Message "### Starting Industrial Local Database Restoration" "Cyan"

# 1. Dependency Preflight
if (-not (Get-Command $PG_RESTORE -ErrorAction SilentlyContinue)) {
    Write-Message "Error: '$PG_RESTORE' is not installed or missing from system PATH." "Red"
    Write-Message "  - macOS: brew install postgresql" "Gray"
    Write-Message "  - Linux: sudo apt install postgresql-client" "Gray"
    Write-Message "  - Win:   winget install PostgreSQL.PostgreSQL" "Gray"
    exit 1
}

# 2. Dump Discovery
$ResolvedDumpPath = $DumpFile
if ([string]::IsNullOrWhiteSpace($ResolvedDumpPath)) {
    Write-Message "No explicit payload provided. Hunting for latest local dump..." "Gray"
    
    $DumpDir = Resolve-Path "$PSScriptRoot/../../db_dumps" -ErrorAction SilentlyContinue
    if (-not $DumpDir) {
        Write-Message "Error: Primary backup directory 'db_dumps' not found." "Red"
        exit 1
    }
    
    $LatestDump = Get-ChildItem -Path $DumpDir.Path -Filter "*.dump" | Sort-Object LastWriteTime -Descending | Select-Object -First 1
    if (-not $LatestDump) {
        Write-Message "Error: No custom .dump payloads discovered in '$($DumpDir.Path)'." "Red"
        exit 1
    }
    
    $ResolvedDumpPath = $LatestDump.FullName
    Write-Message "Auto-selected latest payload: $($LatestDump.Name)" "Yellow"
} elseif (-not (Test-Path $ResolvedDumpPath)) {
    Write-Message "Error: Provided dump payload missing -> '$ResolvedDumpPath'" "Red"
    exit 1
}

# 3. Environment Credential Extraction
$ResolvedEnvPath = (Resolve-Path $LocalEnvPath -ErrorAction SilentlyContinue)?.Path
if (-not $ResolvedEnvPath -or -not (Test-Path $ResolvedEnvPath)) {
    Write-Message "Error: Local ecosystem envelope missing -> '$LocalEnvPath'" "Red"
    exit 1
}

Write-Message "Parsing local ecosystem envelope ($EnvDbKey)..." "Gray"
$DbUrlLine = Get-Content $ResolvedEnvPath | Where-Object { $_ -match "^$EnvDbKey=(.+)$" } | Select-Object -First 1

if (-not $DbUrlLine) {
    Write-Message "Error: '$EnvDbKey' string missing from local environment." "Red"
    exit 1
}

$LocalDbUrl = ($DbUrlLine -split '=', 2)[1].Trim().Trim('"', "'")

# 4. Database Presence Check & Creation
# Extract the target database name and a maintenance connection URL
if ($LocalDbUrl -match "^(postgres(?:ql)?://[^/]+/)([^?]+)(.*)?$") {
    $BaseUrl = $Matches[1]
    $TargetDb = $Matches[2]
    $Params = $Matches[3]
    $MaintenanceUrl = "${BaseUrl}postgres${Params}"
} else {
    Write-Message "Error: Could not parse database name from URL format." "Red"
    exit 1
}

Write-Message "Checking if target database '$TargetDb' exists..." "Gray"
# Attempt to check existence using psql on the maintenance database
$DbExists = & psql -d "$MaintenanceUrl" -tAc "SELECT 1 FROM pg_database WHERE datname='$TargetDb'" 2>$null

if ($DbExists -ne "1") {
    Write-Message "Target database '$TargetDb' not found. Creating..." "Yellow"
    & psql -d "$MaintenanceUrl" -c "CREATE DATABASE $TargetDb" | Out-Null
    if ($LASTEXITCODE -ne 0) {
        Write-Message "Error: Failed to create database '$TargetDb'." "Red"
        exit 1
    }
}

# 5. Payload Injection
Write-Message "Flushing local ecosystem & injecting metadata payload into '$TargetDb'..." "Yellow"
Write-Message "  (Note: Expected non-fatal dropping warnings may appear in stderr)" "DarkGray"

# We use standard industrial restoration directives:
# --clean : Drop existing objects prior to recreation
# --if-exists : Prevent error cascades when dropping missing objects
# --no-owner : Local parity (dev user maps to prod schema automatically)
# --no-acl : Strip absolute prod permissions (granting full dev access locally)

& $PG_RESTORE --clean --if-exists --no-owner --no-acl --dbname="$LocalDbUrl" "$ResolvedDumpPath"

$ExitCode = $LASTEXITCODE

if ($ExitCode -eq 0 -or $ExitCode -eq 1) {
    # Exit Code 1 implies warnings (common with clean drops), but not absolute aborts.
    Write-Message "### Restoration Pipeline Validated (Payload Deployed)" "Green"
} else {
    Write-Message "Error: Critical injection failure. Native PgExitCode: $ExitCode" "Red"
    exit 1
}
