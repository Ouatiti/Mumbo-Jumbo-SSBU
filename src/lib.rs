// Mod de moveset : "Mumbo Jumbo" (hôte : Ness), smashline 2.
mod state;
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
