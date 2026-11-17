# Mumbo Jumbo — moveset SSBU (Skyline / smashline 2)

Mod de moveset fan-made pour **Super Smash Bros. Ultimate**, remplaçant **Ness**.
Ce dépôt contient uniquement du code (aucun asset du jeu ni modèle 3D).

> Statut : en développement, pas encore compilé ni testé en jeu.

## Contenu
- `src/fighter_frame.rs` — jauge de crânes (0–3), gain par dégâts infligés
- `src/specials.rs` — Neutral B (Zap, 3 paliers), Down B (Socle : lenteur / étourdissement / transformation)
- `src/normals.rs` — jab, tilts, smashs, aériennes
- `src/final_smash.rs` — Final Smash (zone, rafale d'éclairs, explosion)

## Compilation
Prérequis : Rust nightly, [cargo-skyline](https://github.com/jam1garner/cargo-skyline), git, Visual Studio Build Tools (C++).

```
cargo skyline build --release
```

Le `.nro` produit se place dans `atmosphere/contents/01006A800016E000/romfs/skyline/plugins/`
avec Skyline et le plugin smashline installés.
