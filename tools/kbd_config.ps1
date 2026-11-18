# Bascule la config Ryujinx du joueur 1 sur un profil clavier de test (et retour).
#   . tools\kbd_config.ps1; Enable-TestKeyboard   -> sauvegarde Config.json.bak_anim puis clavier
#   . tools\kbd_config.ps1; Restore-Config        -> remet la manette d'origine
# Touches : stick WASD, A=K, B=L, X(saut)=I, Y=J, R=U, ZR=O, L=E, ZL=Q,
#           emotes haut/côté/bas = T/V/H (croix), Plus=Entrée.
$script:RyuCfg = "$env:APPDATA\Ryujinx\Config.json"

function Enable-TestKeyboard {
  Get-Process Ryujinx -ErrorAction SilentlyContinue | Stop-Process -Force; Start-Sleep 2
  $c = Get-Content $script:RyuCfg -Raw | ConvertFrom-Json
  if ($c.input_config[0].backend -ne 'WindowKeyboard') { Copy-Item $script:RyuCfg "$script:RyuCfg.bak_anim" -Force }
  $g = $c.input_config[0]
  $kb = [ordered]@{
    left_joycon_stick  = [ordered]@{stick_up='W';stick_down='S';stick_left='A';stick_right='D';stick_button='F'}
    right_joycon_stick = [ordered]@{stick_up='Up';stick_down='Down';stick_left='Left';stick_right='Right';stick_button='G'}
    deadzone_left=0.1; deadzone_right=0.1; range_left=1; range_right=1; trigger_threshold=0.5
    motion=$g.motion; rumble=$g.rumble; led=$g.led
    left_joycon  = [ordered]@{button_minus='Minus';button_l='E';button_zl='Q';button_sl='Unbound';button_sr='Unbound';dpad_up='T';dpad_down='H';dpad_left='V';dpad_right='B'}
    right_joycon = [ordered]@{button_plus='Enter';button_r='U';button_zr='O';button_sl='Unbound';button_sr='Unbound';button_x='I';button_b='L';button_y='J';button_a='K'}
    version=1; backend='WindowKeyboard'; id='0'; name='Mumbo test keyboard'; controller_type='ProController'; player_index='Player1'
  }
  $c.input_config = @([pscustomobject]$kb)
  [IO.File]::WriteAllText($script:RyuCfg, ($c | ConvertTo-Json -Depth 12), (New-Object Text.UTF8Encoding $false))
}

function Restore-Config {
  Get-Process Ryujinx -ErrorAction SilentlyContinue | Stop-Process -Force; Start-Sleep 2
  Copy-Item "$script:RyuCfg.bak_anim" $script:RyuCfg -Force
}
