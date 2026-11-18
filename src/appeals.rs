// Emotes (appeal) de Mumbo.
//  - haut  (appealhil/r) : plante le bâton et danse autour en chantant « Eekum Bokum » — étincelles.
//  - côté  (appealsl/r)  : sort un Glowbo, le regarde se trémousser, le fait disparaître (Alakazam).
//  - bas   (appeallwl/r) : méditation en tailleur en lévitation, bâton flottant, lueur mystique.
//  (Les poses — tour autour du bâton, tailleur, bâton flottant — sont dans les .nuanmb,
//   générés par tools/anim/retarget.py : SPIN / CROSS / FLOAT_STAFF.)
// Timeline de l'emote haut (60 f env., à recaler sur l'animation finale) :
//   f1-6   lève le bâton           → éclair violet sur le bâton
//   f7     plante le bâton         → poussière au sol + son d'impact
//   f10    début du chant          → voix (vc_ness_appeal01 = voix Mumbo remplacée)
//   f10-46 danse autour du bâton   → étincelles violettes/dorées toutes les 6 f
//   f48    final du chant          → flash doré
use smash::app::sv_animcmd::{frame, wait};
use smash::lua2cpp::L2CAgentBase;
use smash::phx::Hash40;
use smash_script::*;
use smashline::*;

unsafe extern "C" fn effect_appealhi(a: &mut L2CAgentBase) {
    frame(a.lua_state_agent, 1.0);
    if macros::is_excute(a) {
        macros::EFFECT_FOLLOW(a, Hash40::new("sys_hit_magic"), Hash40::new("haver"), 0, 0, 0, 0, 0, 0, 0.12, true);
        macros::LAST_EFFECT_SET_COLOR(a, 0.6, 0.2, 1.0);
    }
    frame(a.lua_state_agent, 7.0);
    if macros::is_excute(a) {
        macros::LANDING_EFFECT(a, Hash40::new("sys_landing_smoke"), Hash40::new("top"), 6, 0, 0, 0, 0, 0, 0.5, 0, 0, 0, 0, 0, 0, false);
    }
    frame(a.lua_state_agent, 10.0);
    for i in 0..7 {
        if macros::is_excute(a) {
            // alternance violet (magie) / doré (notes du chant)
            let (r, g, b) = if i % 2 == 0 { (0.6, 0.2, 1.0) } else { (1.0, 0.85, 0.2) };
            let x = if i % 2 == 0 { 5.0 } else { -5.0 };
            macros::EFFECT(a, Hash40::new("sys_hit_magic"), Hash40::new("top"), 0, 14.0 + i as f32, x, 0, 0, 0, 0.1, 2, 2, 2, 0, 0, 0, true);
            macros::LAST_EFFECT_SET_COLOR(a, r, g, b);
        }
        wait(a.lua_state_agent, 6.0);
    }
    frame(a.lua_state_agent, 48.0);
    if macros::is_excute(a) {
        macros::EFFECT_FOLLOW(a, Hash40::new("sys_sp_flash"), Hash40::new("haver"), 0, 0, 0, 0, 0, 0, 0.3, true);
        macros::LAST_EFFECT_SET_COLOR(a, 1.0, 0.85, 0.2);
    }
}

unsafe extern "C" fn sound_appealhi(a: &mut L2CAgentBase) {
    frame(a.lua_state_agent, 7.0);
    if macros::is_excute(a) { macros::PLAY_SE(a, Hash40::new("se_common_landing_soil")); }
    frame(a.lua_state_agent, 10.0);
    if macros::is_excute(a) { macros::PLAY_SE(a, Hash40::new("vc_ness_appeal01")); }
}

// ───────────── Emote côté : le Glowbo ─────────────
// f4 sort le Glowbo (lueur dans la main gauche) → f8-44 il se trémousse (couleurs qui
// changent, petits sauts autour de la main) → f48 « Alakazam » : flash + fumée, il disparaît.
const GLOWBO: [(f32, f32, f32); 4] = [(1.0, 0.4, 0.9), (0.3, 0.9, 1.0), (1.0, 0.9, 0.3), (0.5, 1.0, 0.4)];

unsafe extern "C" fn effect_appeals(a: &mut L2CAgentBase) {
    frame(a.lua_state_agent, 4.0);
    if macros::is_excute(a) {
        macros::EFFECT_FOLLOW(a, Hash40::new("sys_sp_flash"), Hash40::new("handl"), 0, 0, 0, 0, 0, 0, 0.15, true);
        macros::LAST_EFFECT_SET_COLOR(a, 1.0, 0.6, 1.0);
    }
    frame(a.lua_state_agent, 8.0);
    for i in 0..10 {
        if macros::is_excute(a) {
            let (r, g, b) = GLOWBO[i % 4];
            let (dy, dz) = [(0.0, 0.0), (1.0, 0.6), (0.3, -0.6), (1.2, 0.0)][i % 4];
            macros::EFFECT_FOLLOW(a, Hash40::new("sys_aura_light"), Hash40::new("handl"), 0, dy, dz, 0, 0, 0, 0.18, true);
            macros::LAST_EFFECT_SET_COLOR(a, r, g, b);
            macros::LAST_EFFECT_SET_ALPHA(a, 0.8);
        }
        wait(a.lua_state_agent, 4.0);
    }
    frame(a.lua_state_agent, 48.0);
    if macros::is_excute(a) {
        macros::EFFECT_FOLLOW(a, Hash40::new("sys_sp_flash"), Hash40::new("handl"), 0, 0, 0, 0, 0, 0, 0.35, true);
        macros::LAST_EFFECT_SET_COLOR(a, 0.6, 0.2, 1.0);
        macros::EFFECT(a, Hash40::new("sys_erace_smoke"), Hash40::new("handl"), 0, 0, 0, 0, 0, 0, 0.6, 0, 0, 0, 0, 0, 0, false);
    }
}
unsafe extern "C" fn sound_appeals(a: &mut L2CAgentBase) {
    frame(a.lua_state_agent, 4.0);
    if macros::is_excute(a) { macros::PLAY_SE(a, Hash40::new("vc_ness_appeal02")); }
    frame(a.lua_state_agent, 48.0);
    if macros::is_excute(a) { macros::PLAY_SE(a, Hash40::new("se_common_swing_05")); }
}

// ───────────── Emote bas : méditation en lévitation ─────────────
// Lueur mystique pulsée autour du corps (violet/doré), éclat sur le bâton flottant.
unsafe extern "C" fn effect_appeallw(a: &mut L2CAgentBase) {
    frame(a.lua_state_agent, 6.0);
    if macros::is_excute(a) {
        macros::EFFECT_FOLLOW(a, Hash40::new("sys_sp_flash"), Hash40::new("haver"), 0, 0, 0, 0, 0, 0, 0.25, true);
        macros::LAST_EFFECT_SET_COLOR(a, 1.0, 0.85, 0.2);
    }
    for i in 0..6 {
        if macros::is_excute(a) {
            let (r, g, b) = if i % 2 == 0 { (0.6, 0.2, 1.0) } else { (1.0, 0.85, 0.2) };
            macros::EFFECT_FOLLOW(a, Hash40::new("sys_aura_light"), Hash40::new("hip"), 0, 0, 0, 0, 0, 0, 0.45, true);
            macros::LAST_EFFECT_SET_COLOR(a, r, g, b);
            macros::LAST_EFFECT_SET_ALPHA(a, 0.45);
        }
        wait(a.lua_state_agent, 9.0);
    }
}
unsafe extern "C" fn sound_appeallw(a: &mut L2CAgentBase) {
    frame(a.lua_state_agent, 6.0);
    if macros::is_excute(a) { macros::PLAY_SE(a, Hash40::new("vc_ness_appeal03")); }
}

type Acmd = unsafe extern "C" fn(&mut L2CAgentBase);

pub fn install() {
    let mut ag = Agent::new(crate::state::HOST);
    let scripts: [(&str, Acmd); 6] = [
        ("effect_appealhi", effect_appealhi), ("sound_appealhi", sound_appealhi),
        ("effect_appeals", effect_appeals), ("sound_appeals", sound_appeals),
        ("effect_appeallw", effect_appeallw), ("sound_appeallw", sound_appeallw),
    ];
    for (base, f) in scripts {
        for side in ["l", "r"] {
            let name: &'static str = Box::leak(format!("{base}{side}").into_boxed_str());
            ag.acmd(name, f, Priority::Low);
        }
    }
    ag.install();
}
