// Jab, tilts, smashs, aériennes. Chaque coup connecté alimente la jauge de crânes.
// Les valeurs (frames, dégâts, angles) sont un point de départ à équilibrer en jeu.
use smash::app::lua_bind::*;
use smash::lib::lua_const::*;
use smash::lua2cpp::L2CAgentBase;
use smash_script::*;
use smashline::*;
use smash::app::sv_animcmd::{frame, wait};
use smash::phx::Hash40;

/// Hitbox de bâton : id, os, dégâts, angle, kbg, bkb, taille, décalage Z.
macro_rules! stick_hit {
    ($a:expr, $id:expr, $dmg:expr, $ang:expr, $kbg:expr, $bkb:expr, $size:expr, $z:expr) => {
        macros::ATTACK(
            $a, $id, 0, Hash40::new("haver"), $dmg, $ang, $kbg, 0, $bkb, $size, 0.0, 0.0, $z,
            None, None, None, 1.0, 1.0,
            *ATTACK_SETOFF_KIND_ON, *ATTACK_LR_CHECK_F, false, 0, 0.0, 0,
            false, false, false, false, true,
            *COLLISION_SITUATION_MASK_GA_d, *COLLISION_CATEGORY_MASK_ALL, *COLLISION_PART_MASK_ALL, false,
            Hash40::new("collision_attr_elec"), *ATTACK_SOUND_LEVEL_M, *COLLISION_SOUND_ATTR_ELEC, *ATTACK_REGION_OBJECT,
        );
    };
}

unsafe extern "C" fn game_attack11(a: &mut L2CAgentBase) {
    frame(a.lua_state_agent, 4.0);
    if macros::is_excute(a) { stick_hit!(a, 0, 2.5, 361, 20, 0, 3.5, 9.0); }
    wait(a.lua_state_agent, 2.0);
    if macros::is_excute(a) { AttackModule::clear_all(a.module_accessor); }
}

unsafe extern "C" fn game_attack12(a: &mut L2CAgentBase) {
    frame(a.lua_state_agent, 4.0);
    if macros::is_excute(a) { stick_hit!(a, 0, 2.2, 361, 20, 0, 3.5, 10.0); }
    wait(a.lua_state_agent, 2.0);
    if macros::is_excute(a) { AttackModule::clear_all(a.module_accessor); }
}

unsafe extern "C" fn game_attack13(a: &mut L2CAgentBase) {
    frame(a.lua_state_agent, 6.0);
    if macros::is_excute(a) { stick_hit!(a, 0, 4.0, 40, 100, 40, 4.5, 11.0); }
    wait(a.lua_state_agent, 3.0);
    if macros::is_excute(a) { AttackModule::clear_all(a.module_accessor); }
}

// Tilts
unsafe extern "C" fn game_attacks3(a: &mut L2CAgentBase) {
    frame(a.lua_state_agent, 8.0);
    if macros::is_excute(a) { stick_hit!(a, 0, 7.0, 361, 90, 0, 4.0, 12.0); }
    wait(a.lua_state_agent, 3.0);
    if macros::is_excute(a) { AttackModule::clear_all(a.module_accessor); }
}
unsafe extern "C" fn game_attackhi3(a: &mut L2CAgentBase) {
    frame(a.lua_state_agent, 7.0);
    if macros::is_excute(a) { stick_hit!(a, 0, 6.0, 90, 100, 0, 4.5, 3.0); }
    wait(a.lua_state_agent, 4.0);
    if macros::is_excute(a) { AttackModule::clear_all(a.module_accessor); }
}
unsafe extern "C" fn game_attacklw3(a: &mut L2CAgentBase) {
    frame(a.lua_state_agent, 7.0);
    if macros::is_excute(a) { stick_hit!(a, 0, 5.0, 80, 80, 0, 3.5, 11.0); }
    wait(a.lua_state_agent, 3.0);
    if macros::is_excute(a) { AttackModule::clear_all(a.module_accessor); }
}

// Smashs
/// Sans cet indicateur (pose de charge), le smash reste bloqué dans son statut de départ.
unsafe fn start_smash_hold(a: &mut L2CAgentBase) {
    WorkModule::on_flag(a.module_accessor, *FIGHTER_STATUS_ATTACK_FLAG_START_SMASH_HOLD);
}
unsafe extern "C" fn game_attacks4(a: &mut L2CAgentBase) {
    frame(a.lua_state_agent, 11.0);
    if macros::is_excute(a) { start_smash_hold(a); }
    frame(a.lua_state_agent, 18.0);
    if macros::is_excute(a) { // onde de choc au sol devant lui
        stick_hit!(a, 0, 15.0, 42, 95, 0, 6.0, 14.0);
        stick_hit!(a, 1, 12.0, 45, 95, 0, 5.0, 24.0);
    }
    wait(a.lua_state_agent, 4.0);
    if macros::is_excute(a) { AttackModule::clear_all(a.module_accessor); }
}
unsafe extern "C" fn game_attackhi4(a: &mut L2CAgentBase) {
    frame(a.lua_state_agent, 11.0);
    if macros::is_excute(a) { start_smash_hold(a); }
    frame(a.lua_state_agent, 14.0);
    if macros::is_excute(a) { stick_hit!(a, 0, 14.0, 88, 100, 0, 7.0, 4.0); } // explosion au-dessus du bâton
    wait(a.lua_state_agent, 4.0);
    if macros::is_excute(a) { AttackModule::clear_all(a.module_accessor); }
}
unsafe extern "C" fn game_attacklw4(a: &mut L2CAgentBase) {
    frame(a.lua_state_agent, 6.0);
    if macros::is_excute(a) { start_smash_hold(a); }
    frame(a.lua_state_agent, 13.0);
    if macros::is_excute(a) { // deux geysers de part et d'autre
        stick_hit!(a, 0, 13.0, 75, 100, 0, 5.5, 14.0);
        stick_hit!(a, 1, 13.0, 75, 100, 0, 5.5, -14.0);
    }
    wait(a.lua_state_agent, 4.0);
    if macros::is_excute(a) { AttackModule::clear_all(a.module_accessor); }
}

// Aériennes
unsafe extern "C" fn game_attackairn(a: &mut L2CAgentBase) {
    frame(a.lua_state_agent, 5.0);
    if macros::is_excute(a) { stick_hit!(a, 0, 8.0, 361, 80, 0, 5.0, 10.0); }
    wait(a.lua_state_agent, 14.0); // rotation du bâton
    if macros::is_excute(a) { AttackModule::clear_all(a.module_accessor); }
}
unsafe extern "C" fn game_attackairf(a: &mut L2CAgentBase) {
    frame(a.lua_state_agent, 14.0);
    if macros::is_excute(a) { // coup de tête : sweetspot puis hitbox tardive
        macros::ATTACK(a, 0, 0, Hash40::new("head"), 13.0, 361, 100, 0, 50, 4.5, 0.0, 1.0, 2.0,
            None, None, None, 1.0, 1.0, *ATTACK_SETOFF_KIND_ON, *ATTACK_LR_CHECK_F, false, 0, 0.0, 0,
            false, false, false, false, true, *COLLISION_SITUATION_MASK_GA_d, *COLLISION_CATEGORY_MASK_ALL,
            *COLLISION_PART_MASK_ALL, false, Hash40::new("collision_attr_normal"), *ATTACK_SOUND_LEVEL_L,
            *COLLISION_SOUND_ATTR_KICK, *ATTACK_REGION_HEAD);
    }
    wait(a.lua_state_agent, 2.0);
    if macros::is_excute(a) { AttackModule::clear_all(a.module_accessor); }
    frame(a.lua_state_agent, 18.0);
    if macros::is_excute(a) { stick_hit!(a, 0, 7.0, 361, 90, 0, 4.0, 10.0); }
    wait(a.lua_state_agent, 4.0);
    if macros::is_excute(a) { AttackModule::clear_all(a.module_accessor); }
}
unsafe extern "C" fn game_attackairb(a: &mut L2CAgentBase) {
    frame(a.lua_state_agent, 10.0);
    if macros::is_excute(a) { // tir d'énergie vers l'arrière
        macros::ATTACK(a, 0, 0, Hash40::new("top"), 11.0, 150, 100, 0, 50, 5.0, 0.0, 12.0, -14.0,
            None, None, None, 1.0, 1.0, *ATTACK_SETOFF_KIND_ON, *ATTACK_LR_CHECK_B, false, 0, 0.0, 0,
            false, false, false, false, true, *COLLISION_SITUATION_MASK_GA_d, *COLLISION_CATEGORY_MASK_ALL,
            *COLLISION_PART_MASK_ALL, false, Hash40::new("collision_attr_elec"), *ATTACK_SOUND_LEVEL_M,
            *COLLISION_SOUND_ATTR_ELEC, *ATTACK_REGION_OBJECT);
    }
    wait(a.lua_state_agent, 3.0);
    if macros::is_excute(a) { AttackModule::clear_all(a.module_accessor); }
}
unsafe extern "C" fn game_attackairlw(a: &mut L2CAgentBase) {
    frame(a.lua_state_agent, 15.0);
    if macros::is_excute(a) { // piqué électrique : angle 270 = météore
        macros::ATTACK(a, 0, 0, Hash40::new("top"), 12.0, 270, 100, 0, 30, 5.5, 0.0, 2.0, 5.0,
            None, None, None, 1.0, 1.0, *ATTACK_SETOFF_KIND_ON, *ATTACK_LR_CHECK_F, false, 0, 0.0, 0,
            false, false, false, false, true, *COLLISION_SITUATION_MASK_GA_d, *COLLISION_CATEGORY_MASK_ALL,
            *COLLISION_PART_MASK_ALL, false, Hash40::new("collision_attr_elec"), *ATTACK_SOUND_LEVEL_L,
            *COLLISION_SOUND_ATTR_ELEC, *ATTACK_REGION_OBJECT);
    }
    wait(a.lua_state_agent, 6.0);
    if macros::is_excute(a) { AttackModule::clear_all(a.module_accessor); }
}

pub fn install() {
    let mut ag = Agent::new(crate::state::HOST);
    let table: [(&str, unsafe extern "C" fn(&mut L2CAgentBase)); 13] = [
        ("game_attack11", game_attack11), ("game_attack12", game_attack12), ("game_attack13", game_attack13),
        ("game_attacks3", game_attacks3), ("game_attackhi3", game_attackhi3), ("game_attacklw3", game_attacklw3),
        ("game_attacks4", game_attacks4), ("game_attackhi4", game_attackhi4), ("game_attacklw4", game_attacklw4),
        ("game_attackairn", game_attackairn), ("game_attackairf", game_attackairf),
        ("game_attackairb", game_attackairb), ("game_attackairlw", game_attackairlw),
    ];
    for (name, f) in table { ag.acmd(name, f, Priority::Low); }
    ag.install();
}
