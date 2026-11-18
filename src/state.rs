// Ã‰tat propre Ã  chaque joueur (indexÃ© par l'entry id 0..7).
// On Ã©vite les variables de work du jeu : leurs id sont dÃ©jÃ  utilisÃ©s par le moteur.
use smash::app::lua_bind::WorkModule;
use smash::app::BattleObjectModuleAccessor;
use smash::lib::lua_const::*;

/// Combattant hÃ´te du mod. "ness" en production ; "mario" pour tester sur une sauvegarde
/// oÃ¹ Ness n'est pas encore dÃ©bloquÃ©.
pub const HOST: &str = "ness";

pub const MAX_SKULLS: i32 = 3;
/// Un crÃ¢ne tous les X % de dÃ©gÃ¢ts infligÃ©s par les attaques normales.
pub const DMG_PER_SKULL: f32 = 30.0;
/// Gain passif : un crÃ¢ne toutes les 20 s de combat (60 frames/s).
pub const PASSIVE_FRAMES: i32 = 1200;

#[derive(Clone, Copy)]
pub struct MumboState {
    pub skulls: i32,
    pub dmg_acc: f32,
    pub hit_latched: bool,
    pub passive_timer: i32,
    // SpÃ©ciaux
    pub timer: i32,
    pub zap_lvl: i32,
    pub fire_frame: i32,
    pub croco: bool,
    pub pad_effect: i32,
    pub pad_x: f32,
    pub pad_y: f32,
    pub slowed_mask: u32,
    pub last_status: i32,
}

const INIT: MumboState = MumboState {
    skulls: 0,
    dmg_acc: 0.0,
    hit_latched: false,
    passive_timer: 0,
    timer: 0,
    zap_lvl: 0,
    fire_frame: -1,
    croco: false,
    pad_effect: 0,
    pad_x: 0.0,
    pad_y: 0.0,
    slowed_mask: 0,
    last_status: -1,
};

static mut STATES: [MumboState; 8] = [INIT; 8];

pub unsafe fn st(boma: *mut BattleObjectModuleAccessor) -> &'static mut MumboState {
    let id = WorkModule::get_int(boma, *FIGHTER_INSTANCE_WORK_ID_INT_ENTRY_ID).clamp(0, 7) as usize;
    &mut *core::ptr::addr_of_mut!(STATES[id])
}

pub unsafe fn reset(boma: *mut BattleObjectModuleAccessor) {
    *st(boma) = INIT;
}

pub fn gain_skull(s: &mut MumboState) {
    if s.skulls < MAX_SKULLS {
        s.skulls += 1;
        println!("[mumbo_mod] crÃ¢ne gagnÃ© -> {}", s.skulls);
    }
}
