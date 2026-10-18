# Amni Ecosystem Plugin Installer & Updater for Windows PowerShell
# Alhaq Studio (alhaq.uk) - Zero-Emoji Compliant

$ErrorActionPreference = "Stop"

$PluginDir = Join-Path $HOME ".agents\plugins\amni-ecosystem"
$RepoUrl = "https://github.com/alhaq-studio/amni-agent-plugin.git"

Write-Host "[INFO] Installing / Updating Amni Ecosystem Plugin for Alhaq Studio..."

if (Test-Path -Path (Join-Path $PluginDir ".git")) {
    Write-Host "[INFO] Existing git repository found at $PluginDir. Pulling latest updates..."
    git -C $PluginDir pull --ff-only
} elseif (Test-Path -Path $PluginDir) {
    Write-Host "[WARNING] Directory $PluginDir exists but is not a git repository."
    Write-Host "[INFO] Backing up and recloning..."
    $BackupDir = "$PluginDir.bak." + (Get-Date -Format "yyyyMMddHHmmss")
    Move-Item -Path $PluginDir -Destination $BackupDir
    git clone $RepoUrl $PluginDir
} else {
    Write-Host "[INFO] Cloning $RepoUrl to $PluginDir..."
    $ParentDir = Split-Path -Parent $PluginDir
    if (-not (Test-Path -Path $ParentDir)) {
        New-Item -ItemType Directory -Path $ParentDir -Force | Out-Null
    }
    git clone $RepoUrl $PluginDir
}

# Update ~/.gemini/config/plugins.json if it exists
$GeminiConfigDir = Join-Path $HOME ".gemini\config"
$PluginsConfig = Join-Path $GeminiConfigDir "plugins.json"

if (-not (Test-Path -Path $GeminiConfigDir)) {
    New-Item -ItemType Directory -Path $GeminiConfigDir -Force | Out-Null
}

$NormalizedPluginPath = ($PluginDir -replace "\\", "/")

if (Test-Path -Path $PluginsConfig) {
    try {
        $Json = Get-Content -Path $PluginsConfig -Raw | ConvertFrom-Json
        $Exists = $false
        foreach ($entry in $Json.entries) {
            if ($entry.path -eq $NormalizedPluginPath -or $entry.path -eq $PluginDir) {
                $Exists = $true
                break
            }
        }
        if (-not $Exists) {
            $Json.entries += [PSCustomObject]@{ path = $NormalizedPluginPath }
            $Json | ConvertTo-Json -Depth 4 | Set-Content -Path $PluginsConfig -Encoding UTF8
            Write-Host "[INFO] Registered plugin path in $PluginsConfig"
        }
    } catch {
        Write-Host "[WARNING] Could not parse $PluginsConfig. Please verify manually."
    }
} else {
    $InitialConfig = [PSCustomObject]@{
        entries = @(
            [PSCustomObject]@{ path = $NormalizedPluginPath }
        )
    }
    $InitialConfig | ConvertTo-Json -Depth 4 | Set-Content -Path $PluginsConfig -Encoding UTF8
    Write-Host "[INFO] Created $PluginsConfig with plugin registration"
}

Write-Host "[OK] Amni Ecosystem Plugin successfully installed and synchronized."
Write-Host "[INFO] Location: $PluginDir"
