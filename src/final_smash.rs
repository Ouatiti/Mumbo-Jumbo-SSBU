// Final Smash « Eekum Bokum » : zone devant le lanceur, série d'éclairs violets, explosion finale.
// Squelette : la cinématique (caméra) et la capture des cibles sont à brancher sur ton modèle.
use smash::app::lua_bind::*;
use smash::lib::lua_const::*;
use smash::lua2cpp::L2CAgentBase;
use smash_script::*;
use smashline::*;
use smash::app::sv_animcmd::{frame, wait};
use smash::phx::Hash40;

unsafe extern "C" fn game_finalstart(a: &mut L2CAgentBase) {
    frame(a.lua_state_agent, 20.0);
    if macros::is_excute(a) {
        // Zone d'activation devant Mumbo : détecte et capture les adversaires.
        macros::ATTACK(a, 0, 0, Hash40::new("top"), 0.0, 361, 100, 0, 0, 14.0, 0.0, 10.0, 22.0,
            None, None, None, 1.0, 1.0, *ATTACK_SETOFF_KIND_OFF, *ATTACK_LR_CHECK_F, false, 0, 0.0, 0,
            false, false, false, false, true, *COLLISION_SITUATION_MASK_GA_d, *COLLISION_CATEGORY_MASK_ALL,
            *COLLISION_PART_MASK_ALL, false, Hash40::new("collision_attr_elec"), *ATTACK_SOUND_LEVEL_S,
            *COLLISION_SOUND_ATTR_ELEC, *ATTACK_REGION_OBJECT);
    }
}

unsafe extern "C" fn game_finalattack(a: &mut L2CAgentBase) {
    // Éclairs à haute fréquence : une petite hitbox toutes les 3 frames pendant 60 frames.
    for i in 0..20 {
        frame(a.lua_state_agent, 3.0 * i as f32);
        if macros::is_excute(a) {
            macros::ATTACK(a, 0, 0, Hash40::new("top"), 1.2, 361, 0, 0, 0, 9.0, 0.0, 10.0, 20.0,
                None, None, None, 1.0, 1.0, *ATTACK_SETOFF_KIND_OFF, *ATTACK_LR_CHECK_F, false, 0, 0.0, 0,
                false, false, false, false, true, *COLLISION_SITUATION_MASK_GA_d, *COLLISION_CATEGORY_MASK_ALL,
                *COLLISION_PART_MASK_ALL, false, Hash40::new("collision_attr_elec"), *ATTACK_SOUND_LEVEL_S,
                *COLLISION_SOUND_ATTR_ELEC, *ATTACK_REGION_OBJECT);
        }
    }
    // Explosion finale éjectrice.
    frame(a.lua_state_agent, 64.0);
    if macros::is_excute(a) {
        AttackModule::clear_all(a.module_accessor);
        macros::ATTACK(a, 0, 0, Hash40::new("top"), 25.0, 45, 90, 0, 70, 22.0, 0.0, 10.0, 22.0,
            None, None, None, 1.0, 1.0, *ATTACK_SETOFF_KIND_OFF, *ATTACK_LR_CHECK_F, false, 0, 0.0, 0,
            false, false, false, false, true, *COLLISION_SITUATION_MASK_GA_d, *COLLISION_CATEGORY_MASK_ALL,
            *COLLISION_PART_MASK_ALL, false, Hash40::new("collision_attr_elec"), *ATTACK_SOUND_LEVEL_L,
            *COLLISION_SOUND_ATTR_ELEC, *ATTACK_REGION_OBJECT);
    }
    wait(a.lua_state_agent, 3.0);
    if macros::is_excute(a) { AttackModule::clear_all(a.module_accessor); }
}

pub fn install() {
    Agent::new(crate::state::HOST)
        .acmd("game_finalstart", game_finalstart, Priority::Low)
        .acmd("game_finalairstart", game_finalstart, Priority::Low)
        .acmd("game_finalattack", game_finalattack, Priority::Low)
        .install();
}
