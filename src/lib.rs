// Mod de moveset : "Mumbo" (hôte : Ness). Squelette smashline 2.
// ATTENTION : non compilé ni testé en jeu. Les noms de macros/APIs sont à valider
// contre ta version exacte de smashline / smash-script.
mod fighter_frame;
mod specials;
mod normals;
mod final_smash;

#[skyline::main(name = "mumbo_mod")]
pub fn main() {
    fighter_frame::install();
    specials::install();
    normals::install();
    final_smash::install();
}
