# Lance Ryujinx, navigue jusqu'au combat (Samus par dÃ©faut, hÃ´te indiffÃ©rent) et attend.
. "$PSScriptRoot\gui.ps1"
Get-Process Ryujinx -ErrorAction SilentlyContinue | Stop-Process -Force
Start-Sleep 2
Start-Process 'E:\Emulateurs\Emulateur Switch\Ryujinx\publish\Ryujinx.exe' -ArgumentList '"E:\Emulateurs\Emulateur Switch\Ryujinx\jeux\Super Smash Bros Ultimate V13.0.1 Incl. all Dlcs Eur SuperXCi - CLC.xci"'
Start-Sleep 100
1..3 | % { Key 0x4B 150; Start-Sleep 3 }; Start-Sleep 6
Key 0x4B 150; Start-Sleep 8   # Smash
Key 0x4B 150; Start-Sleep 10  # rÃ¨gle
Key 0x44 100; Start-Sleep 1; Key 0x44 100; Start-Sleep 1
Key 0x4B 150; Start-Sleep 12  # stage
"css"
