. "$PSScriptRoot\kbd_config.ps1"
Enable-TestKeyboard
& "$PSScriptRoot\to_css.ps1" | Out-Null
"css pret"
