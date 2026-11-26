# Test en jeu de l'animation rituelle (taunt haut de Ness/Mumbo). Clavier de test, puis restauration.
. "$PSScriptRoot\gui.ps1"
. "$PSScriptRoot\kbd_config.ps1"
$out = "$PSScriptRoot\shots\ritual"
try {
  Enable-TestKeyboard
  "clavier de test actif"
  & "$PSScriptRoot\to_ness.ps1" | Out-Null
  Start-Sleep 45           # chargement du combat + intro
  Shot "$out\00_match.png" | Out-Null
  Key 0x54 150             # T = taunt haut
  for ($i = 1; $i -le 14; $i++) { Start-Sleep -Milliseconds 700; Shot "$out\t$('{0:00}' -f $i).png" | Out-Null }
  Start-Sleep 3
  Shot "$out\99_apres.png" | Out-Null
  "fini"
} finally {
  Restore-Config
  "config manette restauree"
}
