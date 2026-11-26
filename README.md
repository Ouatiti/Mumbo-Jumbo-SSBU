# Mumbo Jumbo (SSBU, Skyline + smashline 2)

Moveset de Mumbo Jumbo qui remplace **Ness**.

## Mécaniques
- **Jauge de crânes 0-3** : +1 crâne tous les 30 % infligés avec les attaques normales, +1 toutes les 20 s. Étincelle violette sur le bâton.
- **B neutre – Zap** : 3 paliers de charge (maintenir B).
- **B côté** : Termite (0 crâne) / Croco (1+ crâne, consomme 1).
- **B haut** : lévitation multi-coups puis chute spéciale.
- **B bas – socle** : 0 crâne = ralentit, 1 = paralyse (−1), 2+ = enterre (−2).
- Normales, smashs, aériennes, Final Smash « Eekum Bokum » (squelette).

## Compiler
```
cargo skyline build --release
```
Sortie : `target/aarch64-skyline-switch/release/libmumbo_mod.nro`

## Installer (Ryujinx)
Copier `libmumbo_mod.nro` et `libsmashline_plugin.nro` dans
`%APPDATA%\Ryujinx\sdcard\atmosphere\contents\01006a800016e000\romfs\skyline\plugins\`.
Skyline doit être installé dans `mods\contents\01006a800016e000\skyline\exefs\`.

## Modèle et animations
Dans l'ordre, avec Blender (`blender -b --factory-startup -P <script>` sauf indication) :
1. `tools/anim/moves.py` puis `tools/anim/lift_head.py` → `tools/anim/out`.
2. `blender -b mumbo_build/step2.blend -P tools/model/add_tokens.py` → `mumbo_build/out_tok`.
3. `tools/model/add_staff_bone.py` (à relancer après chaque `add_tokens.py`) : le bâton passe sur
   l'os `MumboStaff`, car le rendu du jeu n'affiche pas l'animation de `HaveR`.
4. `tools/model/add_token_tracks.py` → `mumbo_build/out_motion`.

Copier `model.nusktb` et `model.numshb` de `out_tok` et les `.nuanmb` de `out_motion` dans le mod
(`fighter/ness/{model,motion}/body/c00`), puis vider le cache d'Arcropolis (sauf `offsets.toml`).
Le modèle et les animations vont ensemble : installer les deux.

## Tester
Jouer un match avec Ness, puis chercher `[mumbo_mod]` dans le dossier `Logs` de Ryujinx :
une ligne « animation '…' introuvable » signale un nom d'animation à corriger dans `src/specials.rs`.
