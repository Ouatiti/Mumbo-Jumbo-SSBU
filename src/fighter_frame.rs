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
        println!("[mumbo_mod] statut -> {} (crânes={}) smash={} s3={}", status, s.skulls,
            status == *FIGHTER_STATUS_KIND_ATTACK_S4 || status == *FIGHTER_STATUS_KIND_ATTACK_HI4 || status == *FIGHTER_STATUS_KIND_ATTACK_LW4,
            status == *FIGHTER_STATUS_KIND_ATTACK_S3);
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

    #[cfg(feature = "fs_test")]
    if status == *FIGHTER_STATUS_KIND_APPEAL
        && [smash::hash40("appeal_s_r"), smash::hash40("appeal_s_l")].contains(&MotionModule::motion_kind(boma))
    {
        WorkModule::on_flag(boma, *FIGHTER_INSTANCE_WORK_ID_FLAG_FINAL);
        StatusModule::change_status_request_from_script(boma, *FIGHTER_STATUS_KIND_FINAL, true);
    }

    // Final Smash « Golden Goliath » (statue géante dorée) : piloté frame par frame.
    let in_fs = crate::final_smash::is_fs_status(status);
    crate::final_smash::goliath_frame(fighter, s, in_fs);

    // Gain passif (le « timer » de la spec).
    s.passive_timer += 1;
    if s.passive_timer >= PASSIVE_FRAMES {
        s.passive_timer = 0;
        gain_skull(s);
    }

    orbit_skulls(fighter, s, !in_fs);
}

// ───────────── Crânes en orbite (jauge visuelle, façon orbes de Rosalina) ─────────────
// Un petit globe os/ivoire par crâne, en cercle horizontal autour du torse ; espacement
// régulier (2π/n), rotation continue + léger flottement vertical. Les effets sont recréés
// toutes les 2 frames à la nouvelle position (l'ancien est tué : pas d'accumulation).
const ORBIT_R: f32 = 7.0;
const ORBIT_Y: f32 = 9.0;
const ORBIT_SPEED: f32 = 2.6; // rad/s

unsafe fn orbit_skulls(fighter: &mut L2CFighterCommon, s: &mut MumboState, visible: bool) {
    if s.passive_timer % 2 != 0 { return; }
    let boma = fighter.module_accessor;
    for h in s.orbit.iter_mut() {
        if *h != 0 {
            EffectModule::kill(boma, *h as u32, false, false);
            *h = 0;
        }
    }
    let n = s.skulls.clamp(0, MAX_SKULLS) as usize;
    if !visible || n == 0 { return; }
    let t = s.passive_timer as f32 / 60.0;
    for k in 0..n {
        let th = t * ORBIT_SPEED + k as f32 * core::f32::consts::TAU / n as f32;
        let x = ORBIT_R * th.sin();
        let z = ORBIT_R * th.cos();
        let y = ORBIT_Y + 0.8 * (t * 3.0 + k as f32 * 2.0).sin();
        macros::EFFECT_FOLLOW(fighter, Hash40::new("sys_aura_light"), Hash40::new("top"), x, y, z, 0, 0, 0, 0.13, true);
        macros::LAST_EFFECT_SET_COLOR(fighter, 1.0, 0.93, 0.78);
        s.orbit[k] = EffectModule::get_last_handle(boma);
        // étincelle violette (rendu non additif : reste visible même sur fond clair)
        if s.passive_timer % 6 == 0 {
            macros::EFFECT_FOLLOW(fighter, Hash40::new("sys_hit_magic"), Hash40::new("top"), x, y, z, 0, 0, 0, 0.05, true);
            macros::LAST_EFFECT_SET_COLOR(fighter, 0.6, 0.2, 1.0);
        }
    }
}

unsafe extern "C" fn diag_start(_fighter: &mut L2CFighterCommon) {
    println!("[mumbo_mod] on_start déclenché");
}

pub fn install() {
    Agent::new(HOST).on_start(diag_start).on_line(Main, mumbo_frame).install();
}
