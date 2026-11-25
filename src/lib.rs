// Mod de moveset : "Mumbo Jumbo" (hôte : Ness), smashline 2.
// Le println! de std n'atteint pas le log sur Switch : on redirige vers skyline.
macro_rules! println {
    ($($arg:tt)*) => { ::skyline::println!($($arg)*) };
}
mod state;
mod fighter_frame;
mod token_anim;
mod specials;
mod normals;
mod final_smash;
mod movement;
mod appeals;

#[skyline::main(name = "mumbo_mod")]
pub fn main() {
    println!("[mumbo_mod] main : installation des hooks (hôte = {})", state::HOST);
    fighter_frame::install();
    specials::install();
    normals::install();
    final_smash::install();
    movement::install();
    appeals::install();
}
