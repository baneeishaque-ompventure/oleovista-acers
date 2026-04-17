#!pwsh
#Requires -Version 5.1

<#
.SYNOPSIS
    Industrial Local-Remote Database Synchronization Tool (Single-Session).
    Compatible with PowerShell Core (Mac/Linux/Windows).

.DESCRIPTION
    Orchestrates a remote PostgreSQL backup via a single SSH streaming session.
    1. Connects to the remote server once.
    2. Validates dependencies and extracts DATABASE_URL remotely.
    3. Streams the binary dump directly to the local 'db_dumps' directory.
    4. Automatically commits the dump to the local repository.

.PARAMETER User
    Remote SSH username.

.PARAMETER Host
    Remote SSH host / IP address.

.PARAMETER Password
    Remote SSH password (requires 'sshpass' locally).

.PARAMETER RemoteEnvPath
    Absolute path to the .env file on the remote server.
    Defaults to '/home/ext_web_root/Projects/acers-backend/acers/.env'.

.PARAMETER EnvDbKey
    The exact key in the remote .env file mapped to the connection string.
    Defaults to 'DATABASE_URL'.

.PARAMETER DatabasePrefix
    Core naming prefix for the output dump files.
    Defaults to 'acers-production'.

.PARAMETER PendingSuffix
    Suffix applied to the temporary file during the streaming process.
    Defaults to 'pending'.

.PARAMETER OutputDirName
    Local directory name for database storage.
    Defaults to 'db_dumps'.

.PARAMETER TimeZones
    Array of TimeZone conversion strings formatted as "SystemZoneId:Label".
    Defaults to @("India Standard Time:IST", "Arabian Standard Time:GST").

.PARAMETER Format
    Format of the dump file: 'Custom' (binary) or 'Plain' (text).
    Defaults to 'Custom'.

.PARAMETER PostDumpAction
    Controls the Git pipeline executed after the dump is created.
    None   — Dump only, no Git operations.
    Commit — Dump, then git add + git commit.
    Push   — Dump, git add + git commit + git push (default).
#>

Param (
    [Parameter(Mandatory=$true)][string]$User,
    [Parameter(Mandatory=$true)][string]$ServerHost,
    [Parameter(Mandatory=$true)][string]$Password,
    [string]$RemoteEnvPath = "/home/ext_web_root/Projects/acers-backend/acers/.env",
    [string]$EnvDbKey = "DATABASE_URL",
    [string]$DatabasePrefix = "acers-production",
    [string]$PendingSuffix = "pending",
    [string]$OutputDirName = "db_dumps",
    [string[]]$TimeZones = @("India Standard Time:IST", "Arabian Standard Time:GST"),
    [ValidateSet("Custom","Plain")]
    [string]$Format = "Custom",
    [ValidateSet("None","Commit","Push")]
    [string]$PostDumpAction = "Push"
)

$ErrorActionPreference = "Stop"

# Script-scoped constants
Set-Variable -Name BASH_SCRIPT_NAME -Value "parse_dotenv_and_stream_pg_dump.bash" -Option Constant
Set-Variable -Name PG_RESTORE -Value "pg_restore" -Option Constant

function Write-Message ($Text, $Color = "White") {
    Write-Host "[$(Get-Date -Format 'HH:mm:ss')] $Text" -ForegroundColor $Color
}

Write-Message "### Starting Single-Session Industrial Backup Sync" "Cyan"

# 1. Local Preflight
if (!(Get-Command "sshpass" -ErrorAction SilentlyContinue)) {
    Write-Message "Error: 'sshpass' utility not found." "Red"
    Write-Message "This script requires 'sshpass' for secure, non-interactive password handling." "Gray"
    Write-Message "Please install 'sshpass' using your system's package manager:" "Yellow"
    Write-Message "  - macOS:            brew install sshpass | sudo port install sshpass" "Gray"
    Write-Message "  - Debian/Ubuntu:    sudo apt-get install sshpass" "Gray"
    Write-Message "  - Fedora/RHEL:      sudo dnf install sshpass (or yum)" "Gray"
    Write-Message "  - Arch Linux:       sudo pacman -S sshpass" "Gray"
    Write-Message "  - Windows Git Bash: curl -L https://raw.githubusercontent.com/wushuaibo/sshpass-for-windows-git-bash/master/sshpass.exe -o /usr/bin/sshpass" "Gray"
    Write-Message "  - Windows MSYS2:    pacman -S sshpass" "Gray"
    Write-Message "  - Windows Cygwin:   Select sshpass in setup-x86_64.exe" "Gray"
    Write-Message "  - Windows WSL:      sudo apt-get install sshpass (or match distro)" "Gray"
    Write-Message "  - Source Compile:   https://sourceforge.net/projects/sshpass/ (macOS/Linux/Cygwin/MSYS2 only; impossible on native Windows)" "Gray"
    exit 1
}

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot = Split-Path -Parent (Split-Path -Parent $ScriptDir)
$OutputDir = Join-Path $RepoRoot $OutputDirName

if ($PostDumpAction -ne "None") {
    Push-Location $RepoRoot
    if (!(Get-Command "git" -ErrorAction SilentlyContinue)) {
        Write-Message "Error: 'git' not found. This script requires Git to commit the dump to the local repository." "Red"
        Write-Message "Please install 'git' using your system's package manager:" "Yellow"
        Write-Message "  - macOS:            brew install git | sudo port install git | xcode-select --install" "Gray"
        Write-Message "  - Debian/Ubuntu:    sudo apt-get install git" "Gray"
        Write-Message "  - Fedora/RHEL:      sudo dnf install git" "Gray"
        Write-Message "  - Arch Linux:       sudo pacman -S git" "Gray"
        Write-Message "  - Windows Winget:   winget install Git.Git" "Gray"
        Write-Message "  - Windows Scoop:    scoop install git" "Gray"
        Write-Message "  - Windows MSYS2:    pacman -S git" "Gray"
        Write-Message "  - Windows Cygwin:   Select git in setup-x86_64.exe" "Gray"
        Write-Message "  - Source Compile:   https://git-scm.com/downloads/source" "Gray"
        exit 1
    }

    $GitBranch = $null
    $GitRemote = $null

    try {
        $IsGitRepo = (git rev-parse --is-inside-work-tree 2>$null) -eq "true"
        if (!$IsGitRepo) {
            Write-Message "Error: The target directory is not a Git repository." "Red"
            Write-Message "PostDumpAction requires the output folder ('$OutputDir') to be tracked by Git." "Gray"
            exit 1
        }

        $GitBranch = git branch --show-current 2>$null

        if ($PostDumpAction -eq "Push") {
            $GitRemote = git remote get-url origin 2>$null
            if ([string]::IsNullOrWhiteSpace($GitRemote)) {
                Write-Message "Error: No remote 'origin' found in the Git repository." "Red"
                Write-Message "PostDumpAction 'Push' requires a valid remote origin to synchronize the dump." "Gray"
                exit 1
            }
        }
    } finally {
        Pop-Location
    }
}

# 2. Format Standardization
switch ($Format) {
    "Custom" {
        $FileExt = "dump"
        $DumpFormatFlag = "--format=custom"
        $IsBinaryDump = $true
    }
    "Plain" {
        $FileExt = "sql"
        $DumpFormatFlag = "--format=plain"
        $IsBinaryDump = $false
    }
}

if ($IsBinaryDump -and !(Get-Command $PG_RESTORE -ErrorAction SilentlyContinue)) {
    Write-Message "Error: '$PG_RESTORE' utility not found." "Red"
    Write-Message "This script requires PostgreSQL client tools locally to extract the absolute transaction time from Custom dumps." "Gray"
    Write-Message "Please install PostgreSQL client tools using your system's package manager:" "Yellow"
    Write-Message "  - macOS:            brew install libpq (client, needs PATH) | sudo port install postgresql16 (client-only)" "Gray"
    Write-Message "  - Debian/Ubuntu:    sudo apt-get install postgresql-client" "Gray"
    Write-Message "  - Fedora/RHEL:      sudo dnf install postgresql (this is the client-only package)" "Gray"
    Write-Message "  - Arch Linux:       sudo pacman -S postgresql (provides client binaries)" "Gray"
    Write-Message "  - Windows Winget:   winget install PostgreSQL.PostgreSQL (server+client)" "Gray"
    Write-Message "  - Windows Scoop:    scoop install postgresql" "Gray"
    Write-Message "  - Windows MSYS2:    pacman -S mingw-w64-x86_64-postgresql" "Gray"
    Write-Message "  - Windows Cygwin:   Select postgresql in setup-x86_64.exe" "Gray"
    Write-Message "  - Source Compile:   https://www.postgresql.org/ftp/source/ (requires core C buildchain)" "Gray"
    exit 1
}

# 3. Local Preparation
$FileName = "$DatabasePrefix-$PendingSuffix.$FileExt"
$SnapshotUTC = [DateTime]::UtcNow

if (!(Test-Path $OutputDir)) {
    New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null
}
$LocalPath = Join-Path $OutputDir $FileName

# 4. Single-Session Remote Execution
# We use bash -s to combine preflight, extraction, and dumping into one stream.
# Errors are sent to stderr (>&2) to avoid corrupting the stdout binary stream.

$BashScriptPath = Join-Path $ScriptDir $BASH_SCRIPT_NAME

if (-not (Test-Path $BashScriptPath)) {
    Write-Message "Error: Support shell script '$BASH_SCRIPT_NAME' not found in $ScriptDir." "Red"
    exit 1
}

Write-Message "Initiating secure tunnel and streaming dump..." "Yellow"

    # PowerShell explicitly blocks the '<' operator and corrupts binary blobs internally via '>'.
    # We defer to the OS-native shell to execute pure, binary-safe I/O redirection.
    # Passwords natively suffer from severe CLI parsing corruption across OS boundaries via 'sh -c'.
    # We explicitly inject it into the environment tree and use SSHPASS (-e) to bypass all syntax parsers permanently and securely.
    $env:SSHPASS = $Password
    $IsWin = (Get-Variable "IsWindows" -ErrorAction SilentlyContinue) -and $IsWindows -or ($PSVersionTable.Platform -eq $null)
    if ($IsWin) {
        cmd.exe /c "sshpass -e ssh -o StrictHostKeyChecking=no `"$User@$ServerHost`" `"bash -s`" -- `"$RemoteEnvPath`" `"$DumpFormatFlag`" `"$EnvDbKey`" < `"$BashScriptPath`" > `"$LocalPath`""
    } else {
        sh -c "sshpass -e ssh -o StrictHostKeyChecking=no '$User@$ServerHost' 'bash -s' -- '$RemoteEnvPath' '$DumpFormatFlag' '$EnvDbKey' < '$BashScriptPath' > '$LocalPath'"
    }
    Remove-Item Env:\SSHPASS -ErrorAction SilentlyContinue

# 5. Success Verification
if ($LASTEXITCODE -ne 0 -or !(Test-Path $LocalPath) -or (Get-Item $LocalPath).Length -eq 0) {
    # If the output file is small enough to be an error string rather than a real dump, inspect it first
    if ((Test-Path $LocalPath) -and ((Get-Item $LocalPath).Length -lt 1024)) {
        $PotentialError = Get-Content $LocalPath -Raw
        if ($PotentialError -match "ERR:") {
            Write-Message "Remote Error: $($PotentialError.Trim())" "Red"
            exit 1
        }
    }
    Write-Message "Error: Sync failed. Check remote dependencies or .env configuration." "Red"
    exit 1
}

# 6. Metadata Extraction (Server Transaction Time)
Write-Message "Extracting absolute transaction time from dump header..." "Yellow"
$SnapshotUTC = $SnapshotUTC

if ($IsBinaryDump) {
    $TOC = & $PG_RESTORE --list "$LocalPath" 2>$null
    $TimeLine = $TOC | Where-Object { $_ -match ";\s*Archive created at\s*(.+ UTC)" } | Select-Object -First 1
    if ($TimeLine -and $matches[1]) {
        try {
            $SnapshotUTC = [DateTime]::ParseExact($matches[1], "yyyy-MM-dd HH:mm:ss 'UTC'", [cultureinfo]::InvariantCulture, [System.Globalization.DateTimeStyles]::AssumeUniversal).ToUniversalTime()
            Write-Message "Successfully extracted transaction time: $($SnapshotUTC.ToString('yyyy-MM-dd HH:mm:ss')) UTC" "Green"
        } catch {
            Write-Message "Warning: Failed to parse custom transaction time. Falling back." "Yellow"
        }
    }
} else {
    $Header = Get-Content -Path $LocalPath -TotalCount 50 2>$null
    $TimeLine = $Header | Where-Object { $_ -match "--\s*Started on\s*(.+ UTC)" } | Select-Object -First 1
    if ($TimeLine -and $matches[1]) {
        try {
            $SnapshotUTC = [DateTime]::ParseExact($matches[1], "yyyy-MM-dd HH:mm:ss 'UTC'", [cultureinfo]::InvariantCulture, [System.Globalization.DateTimeStyles]::AssumeUniversal).ToUniversalTime()
            Write-Message "Successfully extracted sql transaction time: $($SnapshotUTC.ToString('yyyy-MM-dd HH:mm:ss')) UTC" "Green"
        } catch {}
    }
}

# Timezone conversions
$TimestampUTC = $SnapshotUTC.ToString("MMM dd yyyy HH:mm")
$CommitMsgParams = @("DB Dump: $TimestampUTC UTC")

foreach ($TzDef in $TimeZones) {
    if ($TzDef -match "^(.+?):(.+)$") {
        $TzId = $matches[1].Trim()
        $TzLabel = $matches[2].Trim()
    } else {
        $TzId = $TzDef.Trim()
        $TzLabel = $TzId
    }

    try {
        $ZoneTime = [TimeZoneInfo]::ConvertTimeBySystemTimeZoneId($SnapshotUTC, $TzId).ToString("MMM dd yyyy HH:mm")
        $CommitMsgParams += "$ZoneTime $TzLabel"
    } catch {
        Write-Message "Warning: Failed to convert time for zone '$TzId'." "Yellow"
    }
}
$CommitMsg = $CommitMsgParams -join ", "

# Format final filepath
$FileNameTimestamp = $SnapshotUTC.ToString("dd-MM-yyyy-HH-mm")
$FinalFileName = "$DatabasePrefix-$FileNameTimestamp-UTC.$FileExt"
$FinalPath = Join-Path (Split-Path $LocalPath) $FinalFileName

Rename-Item -Path $LocalPath -NewName $FinalFileName
$LocalPath = $FinalPath

$FileBytes = (Get-Item $LocalPath).Length
$FileSize = if ($FileBytes -ge 1MB) { "{0:N2} MB" -f ($FileBytes / 1MB) } `
            elseif ($FileBytes -ge 1KB) { "{0:N2} KB" -f ($FileBytes / 1KB) } `
            else { "$FileBytes B" }
Write-Message "Transfer and processing complete. File: $FinalFileName ($FileSize)" "Green"

# 6. Git Pipeline
$GitHash = $null

if ($PostDumpAction -ne "None") {
    Write-Message "Committing to local repository..." "Gray"
    git add "$LocalPath"
    git commit -m "$CommitMsg"

    $GitHash = git rev-parse --short HEAD

    if ($PostDumpAction -eq "Push") {
        Write-Message "Pushing to remote repository..." "Gray"
        git push
        if ($LASTEXITCODE -ne 0) {
            Write-Message "Warning: Git push failed. Dump is committed locally." "Yellow"
        } else {
            Write-Message "Push successful." "Green"
        }
    }
}

Write-Message "### Sync Operation Successful" "Cyan"
Write-Message "  File     : $FinalFileName ($FileSize)" "Green"
Write-Message "  Snapshot : $($SnapshotUTC.ToString('yyyy-MM-dd HH:mm:ss')) UTC" "Green"
if ($PostDumpAction -eq "None") {
    Write-Message "  Git      : Skipped (PostDumpAction = None)" "Gray"
} else {
    $ActionStr = if ($PostDumpAction -eq "Push") { "Committed and pushed" } else { "Committed locally" }
    Write-Message "  Git      : $ActionStr" "Green"
    Write-Message "  Branch   : $GitBranch" "Green"
    Write-Message "  Hash     : $GitHash" "Green"
    if ($PostDumpAction -eq "Push") {
        Write-Message "  Remote   : $GitRemote" "Green"
    }
    Write-Message "  Message  : $CommitMsg" "Green"
}
