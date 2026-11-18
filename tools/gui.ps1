# Outils de test GUI : capture d'écran et envoi de touches vers la fenêtre Ryujinx.
Add-Type -AssemblyName System.Drawing, System.Windows.Forms
Add-Type @'
using System; using System.Runtime.InteropServices;
public class W {
  [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr h);
  [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr h, out RECT r);
  [DllImport("user32.dll")] public static extern void keybd_event(byte vk, byte sc, uint fl, UIntPtr ex);
  [DllImport("user32.dll")] public static extern bool SetProcessDPIAware();
  public struct RECT { public int L, T, R, B; }
}
'@
[W]::SetProcessDPIAware() | Out-Null

Add-Type @'
using System; using System.Runtime.InteropServices;
public class W2 { [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr h, int c); }
'@
function Focus-Ryu($p) {
  # Astuce Alt : Windows refuse sinon de donner le focus à un autre processus.
  # (F15 et non Alt : Alt activerait la barre de menu de Ryujinx, qui avalerait les touches suivantes.)
  [W]::keybd_event(0x7E, 0, 0, [UIntPtr]::Zero)
  [W2]::ShowWindow($p.MainWindowHandle, 9) | Out-Null
  [W]::SetForegroundWindow($p.MainWindowHandle) | Out-Null
  [W]::keybd_event(0x7E, 0, 2, [UIntPtr]::Zero)
}
function Get-Ryu { Get-Process Ryujinx -ErrorAction SilentlyContinue | Where-Object { $_.MainWindowHandle -ne 0 } | Select-Object -First 1 }

function Shot([string]$path) {
  $p = Get-Ryu
  if (-not $p) { "pas de fenetre Ryujinx"; return }
  Focus-Ryu $p
  Start-Sleep -Milliseconds 700
  $r = New-Object W+RECT
  [W]::GetWindowRect($p.MainWindowHandle, [ref]$r) | Out-Null
  $w = $r.R - $r.L; $h = $r.B - $r.T
  $bmp = New-Object System.Drawing.Bitmap $w, $h
  $g = [System.Drawing.Graphics]::FromImage($bmp)
  $g.CopyFromScreen($r.L, $r.T, 0, 0, (New-Object System.Drawing.Size $w, $h))
  $small = New-Object System.Drawing.Bitmap $bmp, ([int]($w/2)), ([int]($h/2))
  $small.Save($path, [System.Drawing.Imaging.ImageFormat]::Png)
  $g.Dispose(); $bmp.Dispose(); $small.Dispose()
  "ok $w x $h -> $path"
}

# Appui d'une touche (code virtuel) pendant $ms millisecondes.
function Key([byte]$vk, [int]$ms = 120) {
  $p = Get-Ryu
  if ($p) { Focus-Ryu $p }
  [W]::keybd_event($vk, 0, 0, [UIntPtr]::Zero)
  Start-Sleep -Milliseconds $ms
  [W]::keybd_event($vk, 0, 2, [UIntPtr]::Zero)
  Start-Sleep -Milliseconds 120
}

Add-Type @"
using System; using System.Runtime.InteropServices;
public class M { [DllImport("user32.dll")] public static extern bool SetCursorPos(int x,int y); [DllImport("user32.dll")] public static extern void mouse_event(uint f,uint x,uint y,uint d,UIntPtr e); }
"@
# Clique sur le bouton OK du dialogue d'erreur (coordonnees relatives a la fenetre Ryujinx).
function Click-Ok {
  $p = Get-Ryu; $r = New-Object W+RECT; [W]::GetWindowRect($p.MainWindowHandle,[ref]$r) | Out-Null
  Focus-Ryu $p; Start-Sleep 1
  [M]::SetCursorPos($r.L+848,$r.T+416) | Out-Null; Start-Sleep -Milliseconds 300
  [M]::mouse_event(2,0,0,0,[UIntPtr]::Zero); [M]::mouse_event(4,0,0,0,[UIntPtr]::Zero)
}

# Combo : maintient $dir puis appuie $btn pendant $ms, puis relâche.
function Combo([byte]$dir, [byte]$btn, [int]$ms = 200) {
  $p = Get-Ryu; if ($p) { Focus-Ryu $p }
  [W]::keybd_event($dir, 0, 0, [UIntPtr]::Zero); Start-Sleep -Milliseconds 80
  [W]::keybd_event($btn, 0, 0, [UIntPtr]::Zero); Start-Sleep -Milliseconds $ms
  [W]::keybd_event($btn, 0, 2, [UIntPtr]::Zero); [W]::keybd_event($dir, 0, 2, [UIntPtr]::Zero)
  Start-Sleep -Milliseconds 120
}
