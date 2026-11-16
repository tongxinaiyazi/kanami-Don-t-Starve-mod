[CmdletBinding()]
param([switch]$ValidateOnly)
$ErrorActionPreference = 'Stop'
$projectRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
$sourceMod = Join-Path $projectRoot 'mods\klbq_kanami'
$gameMods = [IO.Path]::GetFullPath("E:\steam\steamapps\common\Don't Starve Together\mods")
if (!(Test-Path -LiteralPath (Join-Path $sourceMod 'modinfo.lua'))) { throw 'Source mod missing' }
$deployVersion = [regex]::Match([IO.File]::ReadAllText((Join-Path $sourceMod 'modinfo.lua')), '(?m)^version\s*=\s*"([^"]+)"').Groups[1].Value
if (!$deployVersion) { throw 'Source version missing' }
$installedMod = Join-Path $gameMods 'klbq_kanami'
$workshopMod = 'E:\steam\steamapps\workshop\content\322330\3827702076'
$targets = @([pscustomobject]@{ Name = 'local'; Path = $installedMod; Workshop = $false })
if (Test-Path -LiteralPath $workshopMod) {
    $targets += [pscustomobject]@{ Name = 'workshop-3827702076'; Path = $workshopMod; Workshop = $true }
}
foreach ($target in $targets) {
    if (!(Test-Path -LiteralPath $target.Path)) { continue }
    if ((Resolve-Path -LiteralPath $target.Path).Path -ne [IO.Path]::GetFullPath($target.Path)) { throw "Redirected target: $($target.Path)" }
    if ((Get-Item -LiteralPath $target.Path -Force).Attributes -band [IO.FileAttributes]::ReparsePoint) { throw "Linked mod: $($target.Path)" }
    if (!$target.Workshop -and !(Test-Path -LiteralPath (Join-Path $target.Path '.kanami-task-owned'))) { throw "Unowned local mod: $($target.Path)" }
    if ($target.Workshop -and !(Test-Path -LiteralPath (Join-Path $target.Path 'scripts\prefabs\klbq_kanami.lua'))) { throw 'Workshop target is not Kanami' }
    $links = @(Get-ChildItem -LiteralPath $target.Path -Recurse -Force | Where-Object { $_.Attributes -band [IO.FileAttributes]::ReparsePoint })
    if ($links.Count -gt 0) { throw "Linked child in target: $($target.Path)" }
}
if ($ValidateOnly) { $targets | Select-Object Name, Path; return }
$files = @(Get-ChildItem -LiteralPath $sourceMod -File -Recurse | Sort-Object FullName)
$runningGame = @(Get-Process dontstarve* -ErrorAction SilentlyContinue).Count -gt 0
if ($runningGame) {
    $sourcePaths = @($files | ForEach-Object { $_.FullName.Substring($sourceMod.Length).TrimStart([IO.Path]::DirectorySeparatorChar) })
    foreach ($target in $targets) {
        foreach ($installed in (Get-ChildItem -LiteralPath $target.Path -File -Recurse)) {
            $relative = $installed.FullName.Substring($target.Path.Length).TrimStart([IO.Path]::DirectorySeparatorChar)
            if ($sourcePaths -notcontains $relative -and $relative -notin @('mod.manifest', '.kanami-task-owned')) {
                throw 'Save and fully exit DST before retiring old runtime paths.'
            }
        }
        foreach ($file in $files) {
            $relative = $file.FullName.Substring($sourceMod.Length).TrimStart([IO.Path]::DirectorySeparatorChar)
            $copy = Join-Path $target.Path $relative
            if (!(Test-Path -LiteralPath $copy)) { throw 'Save and fully exit DST before installing new runtime paths.' }
            if ((Get-FileHash -LiteralPath $file.FullName -Algorithm SHA256).Hash -eq (Get-FileHash -LiteralPath $copy -Algorithm SHA256).Hash) { continue }
            if ($relative -eq 'README.md') { continue }
            if ($relative -eq 'modinfo.lua') {
                $pattern = '(?m)^version\s*=\s*"[^"]+"'
            } elseif ($relative -eq 'modmain.lua') {
                $pattern = '\[KLBQ_KANAMI\] [0-9.]+ registered'
            } else { throw 'Save and fully exit DST before replacing runtime code or assets.' }
            $sourceText = [IO.File]::ReadAllText($file.FullName)
            $installedText = [IO.File]::ReadAllText($copy)
            if (($sourceText -replace $pattern, 'VERSION') -cne ($installedText -replace $pattern, 'VERSION')) {
                throw 'Save and fully exit DST before replacing runtime code or configuration.'
            }
        }
    }
}
$backupRoot = Join-Path 'D:\SOFTWARE\CodexData\temp\kanami-local-deploy' (Get-Date -Format 'yyyyMMdd-HHmmss-fff')
$report = [ordered]@{ version = $deployVersion; source = $sourceMod; backup = $backupRoot; restart_required = $runningGame; targets = @() }
foreach ($target in $targets) {
    New-Item -ItemType Directory -Path $target.Path -Force | Out-Null
    $changed = @()
    foreach ($file in $files) {
        $relative = $file.FullName.Substring($sourceMod.Length).TrimStart([IO.Path]::DirectorySeparatorChar)
        $copy = Join-Path $target.Path $relative
        if ((Test-Path -LiteralPath $copy) -and (Get-FileHash -LiteralPath $file.FullName -Algorithm SHA256).Hash -eq (Get-FileHash -LiteralPath $copy -Algorithm SHA256).Hash) { continue }
        if (Test-Path -LiteralPath $copy) {
            $backup = Join-Path (Join-Path $backupRoot $target.Name) $relative
            New-Item -ItemType Directory -Path (Split-Path $backup -Parent) -Force | Out-Null
            Copy-Item -LiteralPath $copy -Destination $backup
        }
        New-Item -ItemType Directory -Path (Split-Path $copy -Parent) -Force | Out-Null
        Copy-Item -LiteralPath $file.FullName -Destination $copy -Force
        $changed += $relative
    }
    if ($target.Workshop) {
        $manifestPath = Join-Path $target.Path 'mod.manifest'
        if (Test-Path -LiteralPath $manifestPath) {
            $backup = Join-Path (Join-Path $backupRoot $target.Name) 'mod.manifest'
            New-Item -ItemType Directory -Path (Split-Path $backup -Parent) -Force | Out-Null
            Copy-Item -LiteralPath $manifestPath -Destination $backup
        }
        $stream = [IO.MemoryStream]::new()
        $writer = [IO.BinaryWriter]::new($stream)
        try {
            $writer.Write([Text.Encoding]::ASCII.GetBytes('MNFS'))
            $writer.Write([uint32]1)
            $writer.Write([uint32]$files.Count)
            foreach ($file in $files) {
                $relative = $file.FullName.Substring($sourceMod.Length).TrimStart([IO.Path]::DirectorySeparatorChar).Replace('\', '/').ToLowerInvariant()
                [uint64]$pathHash = 0
                foreach ($value in [Text.Encoding]::UTF8.GetBytes($relative)) { $pathHash = ($pathHash * 65599 + $value) -band 4294967295L }
                $writer.Write([uint32]$pathHash)
            }
            $writer.Flush()
            [IO.File]::WriteAllBytes($manifestPath, $stream.ToArray())
        } finally { $writer.Dispose(); $stream.Dispose() }
    } else {
        Set-Content -LiteralPath (Join-Path $target.Path '.kanami-task-owned') -Value "Created by Kanami development; current install $deployVersion" -Encoding utf8
    }
    foreach ($file in $files) {
        $relative = $file.FullName.Substring($sourceMod.Length).TrimStart([IO.Path]::DirectorySeparatorChar)
        if ((Get-FileHash -LiteralPath $file.FullName -Algorithm SHA256).Hash -ne (Get-FileHash -LiteralPath (Join-Path $target.Path $relative) -Algorithm SHA256).Hash) { throw "Deploy hash mismatch: $relative" }
    }
    $report.targets += [ordered]@{ name = $target.Name; path = $target.Path; verified_files = $files.Count; changed_files = $changed }
}
$reportPath = Join-Path $projectRoot 'docs\reports\local-deploy-latest.json'
[IO.File]::WriteAllText($reportPath, ($report | ConvertTo-Json -Depth 6) + [Environment]::NewLine, [Text.UTF8Encoding]::new($false))
Write-Output "Installed $deployVersion into $($targets.Count) mod directories. Every runtime file matches source."
if ($runningGame) { Write-Output 'Fully restart DST to load the updated version metadata.' }
Write-Output $reportPath
