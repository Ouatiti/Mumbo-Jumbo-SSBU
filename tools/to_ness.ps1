. "$PSScriptRoot\gui.ps1"
& "$PSScriptRoot\to_css.ps1" | Out-Null
Start-Sleep 15
Key 0x57 700; Start-Sleep 5; Key 0x44 500; Start-Sleep 4; Key 0x44 300; Start-Sleep 4; Key 0x44 300; Start-Sleep 4
Key 0x44 130; Start-Sleep 4; Key 0x44 120; Start-Sleep 4; Key 0x44 130; Start-Sleep 12
Key 0x4B 400; Start-Sleep 8; Key 0x0D 200
"ness lancé"
