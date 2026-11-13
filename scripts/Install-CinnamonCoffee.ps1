#requires -Version 5.1
<#
.SYNOPSIS
Install one CinnamonCoffee script, preserving old copies outside the scripts tree.
.EXAMPLE
  .\Install-CinnamonCoffee.ps1 -GameFolder 'D:\Games\Grand Theft Auto V'
.EXAMPLE
  .\Install-CinnamonCoffee.ps1 -GameFolder 'D:\Games\Grand Theft Auto V' -WhatIf
#>
[CmdletBinding(SupportsShouldProcess = $true, ConfirmImpact = 'Medium')]
param(
    [Parameter(Mandatory = $true)]
    [ValidateNotNullOrEmpty()]
    [string] $GameFolder
)

Set-StrictMode -Version 2.0
$ErrorActionPreference = 'Stop'

function Assert-PlainDirectory([string] $Path) {
    $item = Get-Item -LiteralPath $Path -Force
    if (-not $item.PSIsContainer) { throw "Not a directory: $Path" }
    if (($item.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) {
        throw "A linked directory cannot be scanned safely: $Path"
    }
}

function Get-ScriptFiles([string] $Root) {
    # Traverse explicitly; refuse junctions/symlinks instead of following them
    # outside the selected scripts folder or silently ignoring unknown scripts.
    $pending = New-Object 'System.Collections.Generic.Queue[string]'
    $pending.Enqueue($Root)
    while ($pending.Count -gt 0) {
        $directory = $pending.Dequeue()
        Assert-PlainDirectory $directory
        foreach ($item in @(Get-ChildItem -LiteralPath $directory -Force)) {
            if (($item.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) {
                throw "A linked entry cannot be scanned safely: $($item.FullName)"
            }
            if ($item.PSIsContainer) {
                $pending.Enqueue($item.FullName)
            }
            elseif ($item.Name -match '^CinnamonCoffee.*\.(cs|vb|dll)$') {
                $item
            }
        }
    }
}

$gameRoot = [IO.Path]::GetFullPath((Resolve-Path -LiteralPath $GameFolder).ProviderPath)
if (-not (Test-Path -LiteralPath (Join-Path $gameRoot 'GTA5.exe') -PathType Leaf) -and
    -not (Test-Path -LiteralPath (Join-Path $gameRoot 'GTA5_Enhanced.exe') -PathType Leaf)) {
    throw 'GameFolder must contain GTA5.exe or GTA5_Enhanced.exe. No files were changed.'
}
if (@(Get-Process -Name 'GTA5', 'GTA5_Enhanced' -ErrorAction SilentlyContinue).Count -gt 0) {
    throw 'Close GTA V before installing CinnamonCoffee. No files were changed.'
}

$sourceCandidates = @(
    (Join-Path $PSScriptRoot 'scripts'),
    (Join-Path $PSScriptRoot 'Mod/scripts'),
    (Join-Path (Split-Path -Parent $PSScriptRoot) 'Mod/scripts')
)
$sourceRoot = $null
foreach ($candidate in $sourceCandidates) {
    if (Test-Path -LiteralPath (Join-Path $candidate 'CinnamonCoffee.3.cs') -PathType Leaf) {
        $sourceRoot = [IO.Path]::GetFullPath($candidate)
        break
    }
}
if ($null -eq $sourceRoot) {
    throw 'Package source not found. Keep the installer beside the package scripts folder.'
}
$sourceFile = Join-Path $sourceRoot 'CinnamonCoffee.3.cs'
$sourceBytes = [IO.File]::ReadAllBytes($sourceFile)
$sourceText = [Text.Encoding]::UTF8.GetString($sourceBytes)
if (-not $sourceText.Contains('class CinnamonCoffee')) {
    throw 'The package does not contain a valid CinnamonCoffee source script.'
}
$sourceHash = (Get-FileHash -LiteralPath $sourceFile -Algorithm SHA256).Hash
$version = 'API v3'
if ($sourceText -match '\b(?:MOD_VERSION|BUILD_VERSION|SCRIPT_VERSION|RELEASE_VERSION|CINNAMON_COFFEE_VERSION)\s*=\s*"([^"]+)"') {
    $version = $Matches[1]
}

# Read the complete payload before moving anything. This also supports a package
# extracted directly into the game folder, where source and destination coincide.
$payload = New-Object 'System.Collections.Generic.List[object]'
$payload.Add([pscustomobject]@{ Relative = 'CinnamonCoffee.3.cs'; Bytes = $sourceBytes; Preserve = $false })
$cfg = Join-Path $sourceRoot 'CinnamonCoffee.cfg'
if (Test-Path -LiteralPath $cfg -PathType Leaf) {
    $payload.Add([pscustomobject]@{ Relative = 'CinnamonCoffee.cfg'; Bytes = [IO.File]::ReadAllBytes($cfg); Preserve = $true })
}
$sounds = Join-Path $sourceRoot 'CinnamonCoffeeSounds'
if (Test-Path -LiteralPath $sounds -PathType Container) {
    Assert-PlainDirectory $sounds
    foreach ($wav in @(Get-ChildItem -LiteralPath $sounds -File -Filter '*.wav')) {
        if (($wav.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) {
            throw "A linked package sound cannot be copied safely: $($wav.FullName)"
        }
        $payload.Add([pscustomobject]@{
            Relative = (Join-Path 'CinnamonCoffeeSounds' $wav.Name)
            Bytes = [IO.File]::ReadAllBytes($wav.FullName)
            Preserve = $true
        })
    }
}

$scriptsRoot = Join-Path $gameRoot 'scripts'
$oldScripts = @()
if (Test-Path -LiteralPath $scriptsRoot) {
    Assert-PlainDirectory $scriptsRoot
    $oldScripts = @(Get-ScriptFiles $scriptsRoot)
}
Write-Host "Package: CinnamonCoffee $version"
Write-Host "Source SHA256: $sourceHash"
Write-Host "Existing CinnamonCoffee script copies: $($oldScripts.Count)"
if (-not $PSCmdlet.ShouldProcess($gameRoot, 'Back up previous CinnamonCoffee scripts and install one API-v3 copy')) {
    return
}

$backupRoot = $null
$moved = New-Object 'System.Collections.Generic.List[object]'
$created = New-Object 'System.Collections.Generic.List[string]'
$preserved = 0
try {
    if ($oldScripts.Count -gt 0) {
        $stamp = [DateTime]::UtcNow.ToString('yyyyMMdd-HHmmss-fff') + '-' + [Guid]::NewGuid().ToString('N').Substring(0, 8)
        $backupRoot = Join-Path (Join-Path $gameRoot 'CinnamonCoffee-backups') $stamp
        foreach ($old in $oldScripts) {
            $relative = $old.FullName.Substring($scriptsRoot.Length).TrimStart([char[]]'\/')
            $destination = Join-Path $backupRoot $relative
            [void][IO.Directory]::CreateDirectory((Split-Path -Parent $destination))
            Move-Item -LiteralPath $old.FullName -Destination $destination
            $moved.Add([pscustomobject]@{ Original = $old.FullName; Backup = $destination })
        }
    }
    foreach ($entry in $payload) {
        $destination = Join-Path $scriptsRoot $entry.Relative
        if (Test-Path -LiteralPath $destination) {
            if ($entry.Preserve -and (Test-Path -LiteralPath $destination -PathType Leaf)) {
                $preserved++
                continue
            }
            throw "An unexpected destination already exists: $destination"
        }
        [void][IO.Directory]::CreateDirectory((Split-Path -Parent $destination))
        $created.Add($destination)
        [IO.File]::WriteAllBytes($destination, $entry.Bytes)
    }
    $active = @(Get-ScriptFiles $scriptsRoot)
    if ($active.Count -ne 1 -or $active[0].Name -cne 'CinnamonCoffee.3.cs') {
        throw 'Installation verification failed: expected exactly one active CinnamonCoffee.3.cs.'
    }
    if ((Get-FileHash -LiteralPath $active[0].FullName -Algorithm SHA256).Hash -ne $sourceHash) {
        throw 'Installed script checksum did not match the package.'
    }
}
catch {
    $failure = $_
    $rollbackFailures = New-Object 'System.Collections.Generic.List[string]'
    foreach ($path in $created) {
        try {
            if (Test-Path -LiteralPath $path -PathType Leaf) { Remove-Item -LiteralPath $path }
        }
        catch { $rollbackFailures.Add($_.Exception.Message) }
    }
    foreach ($entry in $moved) {
        try {
            if (Test-Path -LiteralPath $entry.Backup -PathType Leaf) {
                Move-Item -LiteralPath $entry.Backup -Destination $entry.Original
            }
        }
        catch { $rollbackFailures.Add($_.Exception.Message) }
    }
    if ($rollbackFailures.Count -gt 0) {
        throw "Installation failed: $($failure.Exception.Message). Some files could not be restored automatically. Backups remain at: $backupRoot. Recovery details: $($rollbackFailures -join '; ')"
    }
    throw $failure
}
Write-Host 'Installed exactly one CinnamonCoffee.3.cs. Existing cfg, A-Life data and sounds were preserved.'
Write-Host "Existing configuration/sound files kept: $preserved"
if ($null -ne $backupRoot) { Write-Host "Old script backup (outside scripts): $backupRoot" }
Write-Host 'Start GTA V again so ScriptHookVDotNet loads only the newly installed copy.'
