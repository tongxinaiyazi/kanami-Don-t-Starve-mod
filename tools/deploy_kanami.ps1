[CmdletBinding()]
param([switch]$ValidateOnly)
$ErrorActionPreference = 'Stop'
$projectRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
$sourceMod = Join-Path $projectRoot 'mods\klbq_kanami'
$gameMods = [IO.Path]::GetFullPath("E:\steam\steamapps\common\Don't Starve Together\mods")
if (!(Test-Path -LiteralPath (Join-Path $sourceMod 'modinfo.lua'))) { throw 'Source mod missing' }
$deployVersion = [regex]::Match([IO.File]::ReadAllText((Join-Path $sourceMod 'modinfo.lua')), '(?m)^version\s*=\s*"([0-9.]+)"').Groups[1].Value
if (!$deployVersion -or !(Test-Path -LiteralPath (Join-Path $projectRoot "dist\klbq_kanami-$deployVersion-dst.zip"))) { throw 'Package must be verified before deployment' }
$ownedNames = [ordered]@{
    'klbq_kanami' = '.kanami-task-owned'
    'klbq_kanami_startup_old' = '.kanami-startup-owned'
    'klbq_kanami_verify' = '.kanami-task-owned'
    'klbq_kanami_test' = '.kanami-task-owned'
    'klbq_kanami_client_qa' = '.kanami-task-owned'
    'klbq_kanami_void_test' = '.kanami-void-task-owned'
    'klbq_kanami_resource_test' = '.kanami-task-owned'
    'klbq_lilith_kanami_verify' = '.lilith-task-owned'
}
$resolvedTargets = @()
foreach ($name in $ownedNames.Keys) {
    $candidate = Join-Path $gameMods $name
    if (!(Test-Path -LiteralPath $candidate)) { continue }
    $resolved = (Resolve-Path -LiteralPath $candidate).Path
    $expected = [IO.Path]::GetFullPath((Join-Path $gameMods $name))
    if ($resolved -ne $expected -or !( $resolved.StartsWith($gameMods + [IO.Path]::DirectorySeparatorChar, [StringComparison]::OrdinalIgnoreCase))) { throw "Unsafe target: $resolved" }
    if ((Get-Item -LiteralPath $resolved -Force).Attributes -band [IO.FileAttributes]::ReparsePoint) { throw "Refusing linked mod: $resolved" }
    if (!(Test-Path -LiteralPath (Join-Path $resolved $ownedNames[$name]))) { throw "Unowned mod: $resolved" }
    $links = @(Get-ChildItem -LiteralPath $resolved -Directory -Recurse -Force | Where-Object { $_.Attributes -band [IO.FileAttributes]::ReparsePoint })
    if ($links.Count -gt 0) { throw "Linked child in target: $resolved" }
    $resolvedTargets += $resolved
}
if ($ValidateOnly) { $resolvedTargets; return }
# Only exact, resolved game-mod folders with this task's ownership marker are
# replaced. Project code, archived packages, Steam Workshop and saves stay put.
foreach ($resolved in $resolvedTargets) { Remove-Item -LiteralPath $resolved -Recurse -Force }
$installedMod = Join-Path $gameMods 'klbq_kanami'
New-Item -ItemType Directory -Path $installedMod | Out-Null
Get-ChildItem -LiteralPath $sourceMod -Force | Copy-Item -Destination $installedMod -Recurse -Force
Set-Content -LiteralPath (Join-Path $installedMod '.kanami-task-owned') -Value "Created by Kanami development; current install $deployVersion" -Encoding utf8
foreach ($file in (Get-ChildItem -LiteralPath $sourceMod -File -Recurse)) {
    $relative = $file.FullName.Substring($sourceMod.Length).TrimStart([IO.Path]::DirectorySeparatorChar)
    $copy = Join-Path $installedMod $relative
    if ((Get-FileHash -LiteralPath $file.FullName -Algorithm SHA256).Hash -ne (Get-FileHash -LiteralPath $copy -Algorithm SHA256).Hash) { throw "Deploy hash mismatch: $relative" }
}
Write-Output "Installed $deployVersion; source and deployed runtime hashes match. Task-owned older game installs removed."
