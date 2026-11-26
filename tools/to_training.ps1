# Lance Smash et ouvre un match d'entrainement : Mumbo (P1) contre un CPU immobile.
#   . .\to_training.ps1        -> laisse le jeu en match, clavier de test actif
#   Restore-Config             -> a la fin des tests : ferme Ryujinx et remet la manette
# La fenetre Ryujinx prend le focus : ne pas toucher au clavier pendant ~3 min.
# En cas d'echec du script, la manette est remise automatiquement.
. "$PSScriptRoot\gui.ps1"
. "$PSScriptRoot\kbd_config.ps1"

# Appui + attente. S'arrete si la fenetre a disparu (sinon les touches iraient ailleurs).
function Step([byte]$vk, [int]$ms, [double]$wait) {
  if (-not (Get-Ryu)) { throw "fenetre Ryujinx introuvable" }
  Key $vk $ms
  Start-Sleep -Milliseconds ([int]($wait * 1000))
}

try {
  New-Item -ItemType Directory -Force "$PSScriptRoot\shots\train" | Out-Null
  Enable-TestKeyboard
  Start-Process 'E:\Emulateurs\Emulateur Switch\Ryujinx\publish\Ryujinx.exe' -ArgumentList '"E:\Emulateurs\Emulateur Switch\Ryujinx\jeux\Super Smash Bros Ultimate V13.0.1 Incl. all Dlcs Eur SuperXCi - CLC.xci"'
  Start-Sleep 100
  Step 0x4B 150 3; Step 0x4B 150 9      # ecran titre -> menu principal (curseur sur Smash)
  Step 0x44 100 2; Step 0x57 100 2      # Vault puis Games & More
  Step 0x4B 150 5
  Step 0x53 100 2; Step 0x41 100 2      # curseur sur Training
  GShot "$PSScriptRoot\shots\train\menu.png"
  Step 0x4B 150 12                      # choix du stage (Training preselectionne)
  GShot "$PSScriptRoot\shots\train\stage.png"
  Step 0x4B 150 12                      # choix du personnage
  Step 0x57 700 2; Step 0x44 1400 2     # curseur jusqu'a Mumbo (case de Ness)
  Step 0x41 220 2; Step 0x41 240 4
  Step 0x41 70 2; Step 0x53 80 2        # recentrer le curseur dans la case
  Step 0x4B 250 5                       # choisir Mumbo
  GShot "$PSScriptRoot\shots\train\css.png"
  Step 0x0D 200 40                      # lancer le match
  GShot "$PSScriptRoot\shots\train\match.png"
}
catch {
  Restore-Config
  throw
}
