// Jauge de crânes (0..=3) : gain par dégâts des attaques normales + gain passif, effet violet sur le bâton.
use crate::state::*;
use smash::app::lua_bind::*;
use smash::lib::lua_const::*;
use smash::lua2cpp::L2CFighterCommon;
use smash::phx::Hash40;
use smash_script::*;
use smashline::*;

unsafe fn is_normal_attack(status: i32) -> bool {
    [
        *FIGHTER_STATUS_KIND_ATTACK,
        *FIGHTER_STATUS_KIND_ATTACK_100,
        *FIGHTER_STATUS_KIND_ATTACK_DASH,
        *FIGHTER_STATUS_KIND_ATTACK_S3,
        *FIGHTER_STATUS_KIND_ATTACK_HI3,
        *FIGHTER_STATUS_KIND_ATTACK_LW3,
        *FIGHTER_STATUS_KIND_ATTACK_S4,
        *FIGHTER_STATUS_KIND_ATTACK_HI4,
        *FIGHTER_STATUS_KIND_ATTACK_LW4,
        *FIGHTER_STATUS_KIND_ATTACK_AIR,
    ]
    .contains(&status)
}

unsafe extern "C" fn mumbo_frame(fighter: &mut L2CFighterCommon) {
    let boma = fighter.module_accessor;
    let status = StatusModule::status_kind(boma);

    // Réinitialisation à l'entrée, à la mort et au respawn.
    if status == *FIGHTER_STATUS_KIND_ENTRY
        || status == *FIGHTER_STATUS_KIND_DEAD
        || status == *FIGHTER_STATUS_KIND_REBIRTH
    {
        reset(boma);
        return;
    }
    let s = st(boma);
    s.timer += 0; // (le timer des spéciaux est géré dans specials.rs)
    static mut BEAT: u32 = 0;
    BEAT += 1;
    if BEAT % 300 == 1 {
        println!("[mumbo_mod] frame hook actif (statut={}, battement={})", status, BEAT);
    }

    // Trace de diagnostic : chaque changement de statut (hors marche/attente/chute, trop bavards).
    if status != s.last_status {
        s.last_status = status;
        println!("[mumbo_mod] statut -> {} (crânes={})", status, s.skulls);
    }

    // Gain par les coups normaux : on compte une fois par contact (front montant).
    let inflicting = AttackModule::is_infliction(boma, *COLLISION_KIND_MASK_HIT);
    if inflicting && !s.hit_latched && is_normal_attack(status) {
        let power = AttackModule::get_power(boma, 0, false, 1.0, false);
        s.dmg_acc += if power > 0.0 { power } else { 5.0 };
    }
    s.hit_latched = inflicting;
    while s.dmg_acc >= DMG_PER_SKULL {
        s.dmg_acc -= DMG_PER_SKULL;
        gain_skull(s);
    }

    if !smash::app::sv_information::is_ready_go() {
        return;
    }

    // Gain passif (le « timer » de la spec).
    s.passive_timer += 1;
    if s.passive_timer >= PASSIVE_FRAMES {
        s.passive_timer = 0;
        gain_skull(s);
    }

    // Indicateur : étincelle violette sur le bâton, plus grosse avec le nombre de crânes.
    if s.skulls > 0 && s.passive_timer % 20 == 0 {
        let size = 0.15 + 0.12 * s.skulls as f32;
        macros::EFFECT_FOLLOW(fighter, Hash40::new("sys_hit_magic"), Hash40::new("haver"), 0, 0, 0, 0, 0, 0, size, true);
        macros::LAST_EFFECT_SET_COLOR(fighter, 0.6, 0.2, 1.0);
    }
}

unsafe extern "C" fn diag_start(_fighter: &mut L2CFighterCommon) {
    println!("[mumbo_mod] on_start déclenché");
}

pub fn install() {
    Agent::new(HOST).on_start(diag_start).on_line(Main, mumbo_frame).install();
}
