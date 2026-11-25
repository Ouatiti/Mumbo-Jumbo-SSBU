param($tag)
Get-Process Ryujinx -EA 0 | Stop-Process -Force; Start-Sleep 2
Copy-Item E:\Emulateurs\mumbo-mod\target\aarch64-skyline-switch\release\libmumbo_mod.nro 'C:\Users\sofia\AppData\Roaming\Ryujinx\sdcard\atmosphere\contents\01006a800016e000\romfs\skyline\plugins\libzmumbo_mod.nro' -Force
cd E:\Emulateurs\mumbo-mod\tools; . .\gui.ps1
Start-Process 'E:\Emulateurs\Emulateur Switch\Ryujinx\publish\Ryujinx.exe' -ArgumentList '"E:\Emulateurs\Emulateur Switch\Ryujinx\jeux\Super Smash Bros Ultimate V13.0.1 Incl. all Dlcs Eur SuperXCi - CLC.xci"'
Start-Sleep 95
1..40 | % { Key 0x4B 100; Start-Sleep 2 }
Key 0x7A 200; Start-Sleep 2
Key 0x57 700; Start-Sleep 1; Key 0x44 1400; Start-Sleep 1; Key 0x41 540; Start-Sleep 1; Key 0x53 200; Start-Sleep 1
Key 0x57 90; Start-Sleep 1; Key 0x44 60; Start-Sleep 1; Key 0x44 200; Start-Sleep 1; Key 0x44 250; Start-Sleep 1; Key 0x57 40; Start-Sleep 1
Key 0x4B 250; Start-Sleep 2; Key 0x4B 250; Start-Sleep 2; Key 0x0D 200; Start-Sleep 4; Key 0x0D 200; Start-Sleep 45
Shot "E:\Emulateurs\mumbo-mod\tools\shots\${tag}1.png" | Out-Null; Start-Sleep 8
Shot "E:\Emulateurs\mumbo-mod\tools\shots\${tag}2.png" | Out-Null
