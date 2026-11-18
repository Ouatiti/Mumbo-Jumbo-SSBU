# Lance Ryujinx + SSBU, navigue jusqu'à un match (Mario hôte de test vs CPU) puis joue une séquence d'entrées.
# Usage : .\run_test.ps1 -Sequence "N,S,HI,LW"
param([string]$Sequence = "N")
. "$PSScriptRoot\gui.ps1"
$sc = $env:MUMBO_SHOTS; if (-not $sc) { $sc = "$PSScriptRoot\shots" }
New-Item -ItemType Directory -Force $sc | Out-Null
Get-Process Ryujinx -ErrorAction SilentlyContinue | Stop-Process -Force
Start-Sleep 2
Start-Process -FilePath 'E:\Emulateurs\Emulateur Switch\Ryujinx\publish\Ryujinx.exe' -ArgumentList '"E:\Emulateurs\Emulateur Switch\Ryujinx\jeux\Super Smash Bros Ultimate V13.0.1 Incl. all Dlcs Eur SuperXCi - CLC.xci"'
Start-Sleep 100
# Menus jusqu'à la sélection de personnage
1..8 | ForEach-Object { Key 0x0D 400; Start-Sleep 3; Key 0x4B 400; Start-Sleep 3 }
# Curseur -> Mario
Key 0x41 1500; Key 0x57 900; Key 0x57 1200; Key 0x44 450; Key 0x53 450; Key 0x57 300
Key 0x4B 400; Start-Sleep 2; Key 0x4B 400; Start-Sleep 5
Key 0x0D 300; Start-Sleep 30   # lancement + chargement
Shot "$sc\match.png"
# Séquence d'entrées. Touches : B=L, direction D/S/W.
function Down($vk) { [W]::keybd_event($vk, 0, 0, [UIntPtr]::Zero) }
function Up($vk)   { [W]::keybd_event($vk, 0, 2, [UIntPtr]::Zero) }
foreach ($m in $Sequence.Split(',')) {
  switch ($m) {
    'N'  { Down 0x4C; Start-Sleep -Milliseconds 700; Up 0x4C }          # Zap chargé
    'N0' { Key 0x4C 80 }                                                  # Zap tap
    'S'  { Down 0x44; Key 0x4C 100; Up 0x44 }                             # B côté
    'HI' { Down 0x57; Key 0x4C 100; Up 0x57 }                             # B haut
    'LW' { Down 0x53; Key 0x4C 100; Up 0x53 }                             # B bas
    'A'  { Key 0x4B 100 }                                                 # attaque normale
    'JAB' { 1..6 | ForEach-Object { Key 0x4B 60; Start-Sleep -Milliseconds 80 } }
  }
  Start-Sleep 3
}
Shot "$sc\end.png"
