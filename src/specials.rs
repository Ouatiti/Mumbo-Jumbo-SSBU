// Neutral B (Zap Stick, 3 paliers de charge) et Down B (Socle, effet selon les crânes).
use crate::fighter_frame::SKULLS;
use smash::app::lua_bind::*;
use smash::lib::lua_const::*;
use smash::lua2cpp::L2CAgentBase;
use smash_script::*;
use smashline::*;
use smash::app::sv_animcmd::frame;

/// Niveau de charge du Zap (0..=2) — variable de work.
const ZAP_LVL: i32 = 0x1000_0010;

// ───────────── Neutral B : Zap Stick ─────────────
// Le projectile est l'article PK Thunder de l'hôte, réglé par palier (taille / dégâts).
unsafe extern "C" fn game_specialn(agent: &mut L2CAgentBase) {
    let module_accessor = agent.module_accessor;
    if macros::is_excute(agent) {
        WorkModule::set_int(module_accessor, 0, ZAP_LVL);
    }
    // Charge : on avance de palier toutes les 14 frames tant que B est maintenu.
    for lvl in 1..=2 {
        frame(agent.lua_state_agent, 14.0 * lvl as f32);
        if macros::is_excute(agent) {
            if ControlModule::check_button_on(module_accessor, *CONTROL_PAD_BUTTON_SPECIAL) {
                WorkModule::set_int(module_accessor, lvl, ZAP_LVL);
            }
        }
    }
    frame(agent.lua_state_agent, 30.0);
    if macros::is_excute(agent) {
        let lvl = WorkModule::get_int(module_accessor, ZAP_LVL);
        // Dégâts : 5 / 9 / 14 ; hitbox : plus grosse à chaque palier (mise à l'échelle de l'article).
        let _dmg = [5.0_f32, 9.0, 14.0][lvl as usize];
        ArticleModule::generate_article(
            module_accessor,
            *FIGHTER_NESS_GENERATE_ARTICLE_PK_THUNDER,
            false,
            -1,
        );
        // TODO : ArticleModule::set_float / scale via ARTICLE_SCALE pour le palier `lvl`.
    }
}

// ───────────── Down B : Socle de Mumbo ─────────────
// 0 crâne = ralentissement ; 1 = étourdissement (consomme 1) ; 2+ = transformation (consomme 2).
const PAD_EFFECT: i32 = 0x1000_0011;

unsafe extern "C" fn game_speciallw(agent: &mut L2CAgentBase) {
    let module_accessor = agent.module_accessor;
    frame(agent.lua_state_agent, 12.0);
    if macros::is_excute(agent) {
        let skulls = WorkModule::get_int(module_accessor, SKULLS);
        let (effect, cost) = match skulls {
            0 => (0, 0),
            1 => (1, 1),
            _ => (2, 2),
        };
        WorkModule::set_int(module_accessor, effect, PAD_EFFECT);
        WorkModule::set_int(module_accessor, skulls - cost, SKULLS);
        // Pose du piège : article au sol (base : PK Flash de Ness, détecteur de zone).
        ArticleModule::generate_article(
            module_accessor,
            *FIGHTER_NESS_GENERATE_ARTICLE_PK_FLASH,
            false,
            -1,
        );
    }
}

// Effets appliqués à la victime à la détection (à brancher sur l'article-piège) :
//   0 -> mouvement ralenti ~3 s (SlowModule / vitesse de chute et de marche réduites)
//   1 -> FIGHTER_STATUS_KIND_CAPTURE_PULLED/paralysie 1,2 s (état électrique)
//   2 -> état BURY ou vulnérable 2,5 s (transformation : hitbox défenseur sans défense)

pub fn install() {
    Agent::new("ness")
        .acmd("game_specialn", game_specialn, Priority::Low)
        .acmd("game_specialairn", game_specialn, Priority::Low)
        .acmd("game_speciallw", game_speciallw, Priority::Low)
        .acmd("game_specialairlw", game_speciallw, Priority::Low)
        .install();
}
