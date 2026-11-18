// Déplacements de Mumbo : effets/sons des cycles de base + chute ralentie avec aura magique.
// Les animations elles-mêmes (dos voûté, démarche sautillante...) viennent des .nuanmb
// (fighter/ness/motion/body/c00) : ici on ne pilote que les scripts effect_/sound_ et la physique.
// Les numéros de frame sont des repères à recaler une fois les animations de Mumbo faites.
use crate::state::*;
use smash::app::lua_bind::*;
use smash::app::sv_animcmd::frame;
use smash::lib::lua_const::*;
use smash::lua2cpp::{L2CAgentBase, L2CFighterCommon};
use smash::phx::Hash40;
use smash_script::*;
use smashline::*;

/// Vitesse de chute max de Mumbo (Ness : ~1.55). Le fast-fall n'est pas bridé.
const FALL_CAP: f32 = 1.20;
/// Couleur violette de la magie de Mumbo (RVB 0..1).
const MAGIC: (f32, f32, f32) = (0.6, 0.2, 1.0);

/// Petite étincelle violette qui suit un os.
unsafe fn sparkle(a: &mut L2CAgentBase, bone: &str, size: f32) {
    macros::EFFECT_FOLLOW(a, Hash40::new("sys_hit_magic"), Hash40::new(bone), 0, 0, 0, 0, 0, 0, size, true);
    macros::LAST_EFFECT_SET_COLOR(a, MAGIC.0, MAGIC.1, MAGIC.2);
}

/// Poussière au pied (pas pieds nus : petite et sèche).
unsafe fn dust(a: &mut L2CAgentBase, size: f32) {
    macros::FOOT_EFFECT(a, Hash40::new("sys_run_smoke"), Hash40::new("top"), -2, 0, 0, 0, 0, 0, size, 0, 0, 0, 0, 0, 0, false);
}

// ───────────── Attente : le bâton crépite de temps en temps ─────────────
unsafe extern "C" fn effect_wait(a: &mut L2CAgentBase) {
    frame(a.lua_state_agent, 30.0);
    if macros::is_excute(a) { sparkle(a, "haver", 0.08); }
    frame(a.lua_state_agent, 60.0);
    if macros::is_excute(a) { sparkle(a, "haver", 0.06); }
}

// ───────────── Marche / course : pas raides, poussière à chaque appui ─────────────
const STEP_WALK: [f32; 2] = [8.0, 24.0];
const STEP_RUN: [f32; 2] = [4.0, 14.0];

unsafe extern "C" fn sound_walk(a: &mut L2CAgentBase) {
    frame(a.lua_state_agent, STEP_WALK[0]);
    if macros::is_excute(a) { macros::PLAY_STEP(a, Hash40::new("se_ness_step_left_s")); }
    frame(a.lua_state_agent, STEP_WALK[1]);
    if macros::is_excute(a) { macros::PLAY_STEP(a, Hash40::new("se_ness_step_right_s")); }
}
unsafe extern "C" fn effect_walk(a: &mut L2CAgentBase) {
    frame(a.lua_state_agent, STEP_WALK[0]);
    if macros::is_excute(a) { dust(a, 0.4); }
    frame(a.lua_state_agent, STEP_WALK[1]);
    if macros::is_excute(a) { dust(a, 0.4); }
}
unsafe extern "C" fn sound_run(a: &mut L2CAgentBase) {
    frame(a.lua_state_agent, STEP_RUN[0]);
    if macros::is_excute(a) { macros::PLAY_STEP(a, Hash40::new("se_ness_step_left_m")); }
    frame(a.lua_state_agent, STEP_RUN[1]);
    if macros::is_excute(a) { macros::PLAY_STEP(a, Hash40::new("se_ness_step_right_m")); }
}
unsafe extern "C" fn effect_run(a: &mut L2CAgentBase) {
    frame(a.lua_state_agent, STEP_RUN[0]);
    if macros::is_excute(a) { dust(a, 0.6); sparkle(a, "haver", 0.05); }
    frame(a.lua_state_agent, STEP_RUN[1]);
    if macros::is_excute(a) { dust(a, 0.6); }
}
unsafe extern "C" fn effect_dash(a: &mut L2CAgentBase) {
    frame(a.lua_state_agent, 1.0);
    if macros::is_excute(a) {
        macros::FOOT_EFFECT(a, Hash40::new("sys_dash_smoke"), Hash40::new("top"), -3, 0, 0, 0, 0, 0, 0.8, 0, 0, 0, 0, 0, 0, false);
    }
}

// ───────────── Sauts / atterrissages ─────────────
unsafe extern "C" fn effect_jump(a: &mut L2CAgentBase) {
    frame(a.lua_state_agent, 1.0);
    if macros::is_excute(a) {
        macros::LANDING_EFFECT(a, Hash40::new("sys_jump_smoke"), Hash40::new("top"), 0, 0, 0, 0, 0, 0, 0.8, 0, 0, 0, 0, 0, 0, false);
    }
}
unsafe extern "C" fn effect_jumpaerial(a: &mut L2CAgentBase) {
    frame(a.lua_state_agent, 1.0);
    if macros::is_excute(a) {
        macros::EFFECT_FOLLOW(a, Hash40::new("sys_jump_aerial"), Hash40::new("top"), 0, 6, 0, 0, 0, 0, 0.9, true);
        macros::LAST_EFFECT_SET_COLOR(a, MAGIC.0, MAGIC.1, MAGIC.2);
        sparkle(a, "haver", 0.1);
    }
}
unsafe extern "C" fn effect_landing(a: &mut L2CAgentBase) {
    frame(a.lua_state_agent, 1.0);
    if macros::is_excute(a) {
        macros::LANDING_EFFECT(a, Hash40::new("sys_landing_smoke"), Hash40::new("top"), 0, 0, 0, 0, 0, 0, 0.7, 0, 0, 0, 0, 0, 0, false);
    }
}

// ───────────── Chute ralentie + aura (frame hook) ─────────────
unsafe extern "C" fn fall_frame(fighter: &mut L2CFighterCommon) {
    let boma = fighter.module_accessor;
    let status = StatusModule::status_kind(boma);
    let airborne = [
        *FIGHTER_STATUS_KIND_FALL, *FIGHTER_STATUS_KIND_FALL_AERIAL,
        *FIGHTER_STATUS_KIND_JUMP, *FIGHTER_STATUS_KIND_JUMP_AERIAL,
    ].contains(&status);
    if !airborne || StatusModule::situation_kind(boma) != *SITUATION_KIND_AIR {
        return;
    }
    let vy = KineticModule::get_sum_speed_y(boma, *KINETIC_ENERGY_RESERVE_ATTRIBUTE_MAIN);
    let diving = WorkModule::is_flag(boma, *FIGHTER_STATUS_WORK_ID_FLAG_RESERVE_DIVE);
    if vy < 0.0 && !diving {
        if vy < -FALL_CAP {
            sv_kinetic_energy!(set_speed, fighter, FIGHTER_KINETIC_ENERGY_ID_GRAVITY, -FALL_CAP);
        }
        // Aura magique discrète tant qu'il plane.
        let s = st(boma);
        if s.passive_timer % 16 == 0 {
            macros::EFFECT_FOLLOW(fighter, Hash40::new("sys_aura_light"), Hash40::new("hip"), 0, 0, 0, 0, 0, 0, 0.25, true);
            macros::LAST_EFFECT_SET_COLOR(fighter, MAGIC.0, MAGIC.1, MAGIC.2);
            macros::LAST_EFFECT_SET_ALPHA(fighter, 0.5);
        }
    }
}

type Acmd = unsafe extern "C" fn(&mut L2CAgentBase);

pub fn install() {
    let mut ag = Agent::new(HOST);
    let table: &[(&str, Acmd)] = &[
        ("effect_wait1", effect_wait), ("effect_wait2", effect_wait), ("effect_wait3", effect_wait),
        ("sound_walkslow", sound_walk), ("sound_walkmiddle", sound_walk), ("sound_walkfast", sound_run),
        ("effect_walkslow", effect_walk), ("effect_walkmiddle", effect_walk), ("effect_walkfast", effect_run),
        ("sound_run", sound_run), ("effect_run", effect_run), ("effect_dash", effect_dash),
        ("effect_jumpf", effect_jump), ("effect_jumpb", effect_jump),
        ("effect_jumpaerialf", effect_jumpaerial), ("effect_jumpaerialb", effect_jumpaerial),
        ("effect_landingheavy", effect_landing), ("effect_landinglight", effect_landing),
    ];
    for (name, f) in table { ag.acmd(name, *f, Priority::Low); }
    ag.on_line(Main, fall_frame);
    ag.install();
}
