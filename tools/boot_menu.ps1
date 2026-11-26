# Lance Ryujinx (clavier de test) et s'arrete sur le menu principal de Smash.
. "$PSScriptRoot\gui.ps1"
. "$PSScriptRoot\kbd_config.ps1"
Enable-TestKeyboard
Start-Process 'E:\Emulateurs\Emulateur Switch\Ryujinx\publish\Ryujinx.exe' -ArgumentList '"E:\Emulateurs\Emulateur Switch\Ryujinx\jeux\Super Smash Bros Ultimate V13.0.1 Incl. all Dlcs Eur SuperXCi - CLC.xci"'
Start-Sleep 100
1..3 | % { Key 0x4B 150; Start-Sleep 3 }; Start-Sleep 6
New-Item -ItemType Directory -Force "$PSScriptRoot\shots\train" | Out-Null
GShot "$PSScriptRoot\shots\train\a1.png"
"menu"
