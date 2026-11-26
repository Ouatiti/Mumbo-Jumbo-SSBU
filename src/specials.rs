// Spéciaux de Mumbo : statuts personnalisés qui remplacent entièrement ceux de Ness
// (PK Flash, PK Fire, PK Thunder, Psy-aimant). Chaque statut finit sur un compteur de frames,
// donc il ne peut pas rester bloqué même si une animation est absente.
//   B neutre : Zap, 3 paliers de charge (maintenir B), rayon de plus en plus long et fort.
//   B côté   : 0 crâne = Termite (charge multi-coups) ; 1+ = Croco (morsure, consomme 1 crâne).
//   B haut   : lévitation multi-coups, puis chute spéciale.
//   B bas    : socle ; 0 crâne = ralentit, 1 = paralyse (consomme 1), 2+ = enterre (consomme 2).
use crate::state::*;
use smash::app::lua_bind::*;
use smash::app::{sv_battle_object, GroundCliffCheckKind, GroundCorrectKind, SituationKind};
use smash::lib::lua_const::*;
use smash::lib::{L2CValue, L2CValueType};
use smash::lua2cpp::{L2CAgentBase, L2CFighterCommon};
use smash::phx::Hash40;
use smash_script::*;
use smashline::*;

// ───────────── Outils communs ─────────────

unsafe fn pre_special(fighter: &mut L2CFighterCommon, air_only: bool, power_bit: i32, log_bit: i32) -> L2CValue {
    let (situation, kinetic, correct) = if air_only {
        (*SITUATION_KIND_AIR, *FIGHTER_KINETIC_TYPE_FALL, *GROUND_CORRECT_KIND_AIR)
    } else {
        (*SITUATION_KIND_NONE, *FIGHTER_KINETIC_TYPE_UNIQ, *GROUND_CORRECT_KIND_KEEP)
    };
    StatusModule::init_settings(
        fighter.module_accessor,
        SituationKind(situation),
        kinetic,
        correct as u32,
        GroundCliffCheckKind(*GROUND_CLIFF_CHECK_KIND_NONE),
        true,
        *FIGHTER_STATUS_WORK_KEEP_FLAG_NONE_FLAG,
        *FIGHTER_STATUS_WORK_KEEP_FLAG_NONE_INT,
        *FIGHTER_STATUS_WORK_KEEP_FLAG_NONE_FLOAT,
        0,
    );
    FighterStatusModuleImpl::set_fighter_status_data(
        fighter.module_accessor,
        false,
        *FIGHTER_TREADED_KIND_NO_REAC,
        false,
        false,
        false,
        (log_bit | *FIGHTER_LOG_MASK_FLAG_ACTION_CATEGORY_ATTACK | *FIGHTER_LOG_MASK_FLAG_ACTION_TRIGGER_ON) as u64,
        *FIGHTER_STATUS_ATTR_START_TURN as u32,
        power_bit as u32,
        0,
    );
    0.into()
}

unsafe fn grounded(fighter: &mut L2CFighterCommon) -> bool {
    StatusModule::situation_kind(fighter.module_accessor) == *SITUATION_KIND_GROUND
}

/// Physique « arrêt » au sol / en l'air ; réappliquée quand Mumbo atterrit ou quitte le sol.
unsafe fn apply_situation(fighter: &mut L2CFighterCommon, first: bool) {
    let boma = fighter.module_accessor;
    if !first && !StatusModule::is_situation_changed(boma) {
        return;
    }
    if grounded(fighter) {
        GroundModule::correct(boma, GroundCorrectKind(*GROUND_CORRECT_KIND_GROUND_CLIFF_STOP));
        KineticModule::change_kinetic(boma, *FIGHTER_KINETIC_TYPE_GROUND_STOP);
    } else {
        GroundModule::correct(boma, GroundCorrectKind(*GROUND_CORRECT_KIND_AIR));
        KineticModule::change_kinetic(boma, *FIGHTER_KINETIC_TYPE_AIR_STOP);
    }
}

/// Change d'animation ; si celle de Ness n'existe pas, repli sur attente/chute (et trace dans le log).
unsafe fn set_motion(fighter: &mut L2CFighterCommon, ground: &str, air: &str) {
    let boma = fighter.module_accessor;
    let on_ground = grounded(fighter);
    let name = if on_ground { ground } else { air };
    MotionModule::change_motion(boma, Hash40::new(name), 0.0, 1.0, false, 0.0, false, false);
    if MotionModule::motion_kind(boma) != Hash40::new(name).hash {
        println!("[mumbo_mod] animation '{}' introuvable, repli", name);
        let fallback = if on_ground { "wait_1" } else { "fall" };
        MotionModule::change_motion(boma, Hash40::new(fallback), 0.0, 1.0, false, 0.0, false, false);
    }
}

unsafe fn finish(fighter: &mut L2CFighterCommon, special_fall: bool) -> L2CValue {
    let next = if grounded(fighter) {
        *FIGHTER_STATUS_KIND_WAIT
    } else if special_fall {
        *FIGHTER_STATUS_KIND_FALL_SPECIAL
    } else {
        *FIGHTER_STATUS_KIND_FALL
    };
    fighter.change_status(next.into(), false.into());
    1.into()
}

unsafe fn shift_main(fighter: &mut L2CFighterCommon, func: unsafe extern "C" fn(&mut L2CFighterCommon) -> L2CValue) -> L2CValue {
    let mut v = L2CValue::new_void();
    v.val_type = L2CValueType::Pointer;
    v.inner.raw = func as *const () as u64;
    fighter.sub_shift_status_main(v)
}

/// Vitesse horizontale vers l'avant (énergie « stop »), en unités par frame.
unsafe fn push_forward(fighter: &mut L2CFighterCommon, speed: f32) {
    let lr = PostureModule::lr(fighter.module_accessor);
    sv_kinetic_energy!(set_speed, fighter, *FIGHTER_KINETIC_ENERGY_ID_STOP, speed * lr, 0.0);
}

/// Hitbox générique ; `z2` donne une capsule (rayon du Zap), `rehit` > 0 rend le coup multi-hit.
#[allow(clippy::too_many_arguments)]
unsafe fn hit(
    agent: &mut L2CAgentBase, id: u64, dmg: f32, angle: u64, kbg: i32, fkb: i32, bkb: i32,
    size: f32, y: f32, z: f32, z2: Option<f32>, rehit: i32, attr: &str,
) {
    macros::ATTACK(
        agent, id, 0, Hash40::new("top"), dmg, angle, kbg, fkb, bkb, size, 0.0, y, z,
        None, if z2.is_some() { Some(y) } else { None }, z2, 1.0, 1.0,
        *ATTACK_SETOFF_KIND_ON, *ATTACK_LR_CHECK_F, false, 0, 0.0, rehit,
        false, false, false, false, true,
        *COLLISION_SITUATION_MASK_GA, *COLLISION_CATEGORY_MASK_ALL, *COLLISION_PART_MASK_ALL, false,
        Hash40::new(attr), *ATTACK_SOUND_LEVEL_M, *COLLISION_SOUND_ATTR_ELEC, *ATTACK_REGION_OBJECT,
    );
}

unsafe fn purple_flash(fighter: &mut L2CFighterCommon, effect: &str, size: f32) {
    macros::EFFECT_FOLLOW(fighter, Hash40::new(effect), Hash40::new("haver"), 0, 0, 0, 0, 0, 0, size, true);
    macros::LAST_EFFECT_SET_COLOR(fighter, 0.6, 0.2, 1.0);
}

unsafe extern "C" fn status_noop(_fighter: &mut L2CFighterCommon) -> L2CValue {
    0.into()
}

// ───────────── B neutre : Zap ─────────────

unsafe extern "C" fn special_n_pre(fighter: &mut L2CFighterCommon) -> L2CValue {
    pre_special(fighter, false, *FIGHTER_POWER_UP_ATTACK_BIT_SPECIAL_N, *FIGHTER_LOG_MASK_FLAG_ATTACK_KIND_SPECIAL_N)
}

unsafe extern "C" fn special_n_main(fighter: &mut L2CFighterCommon) -> L2CValue {
    let s = st(fighter.module_accessor);
    s.timer = 0;
    s.zap_lvl = 0;
    s.fire_frame = -1;
    println!("[mumbo_mod] B neutre : Zap commence (crânes={})", s.skulls);
    apply_situation(fighter, true);
    set_motion(fighter, "special_n_start", "special_air_n_start");
    shift_main(fighter, special_n_loop)
}

const ZAP_DMG: [f32; 3] = [5.0, 9.0, 14.0];
const ZAP_SIZE: [f32; 3] = [2.5, 3.5, 5.0];
const ZAP_LEN: [f32; 3] = [25.0, 35.0, 45.0];
const ZAP_BKB: [i32; 3] = [30, 40, 55];
const ZAP_KBG: [i32; 3] = [60, 70, 85];

unsafe extern "C" fn special_n_loop(fighter: &mut L2CFighterCommon) -> L2CValue {
    let boma = fighter.module_accessor;
    let s = st(boma);
    s.timer += 1;
    apply_situation(fighter, false);

    if s.fire_frame < 0 {
        let held = ControlModule::check_button_on(boma, *CONTROL_PAD_BUTTON_SPECIAL);
        if held && s.timer % 14 == 0 && s.zap_lvl < 2 {
            s.zap_lvl += 1;
            purple_flash(fighter, "sys_hit_magic", 0.2 + 0.12 * s.zap_lvl as f32);
        }
        if (!held && s.timer >= 6) || s.timer >= 42 {
            s.fire_frame = s.timer;
            let l = s.zap_lvl as usize;
            println!("[mumbo_mod] Zap tiré : palier {} à la frame {}", l, s.timer);
            set_motion(fighter, "special_n_fire", "special_air_n_fire");
            hit(fighter, 0, ZAP_DMG[l], 361, ZAP_KBG[l], 0, ZAP_BKB[l], ZAP_SIZE[l], 8.0, 8.0,
                Some(8.0 + ZAP_LEN[l]), 0, "collision_attr_elec");
            purple_flash(fighter, "sys_hit_elec", 0.6 + 0.4 * s.zap_lvl as f32);
        }
    } else {
        let t = s.timer - s.fire_frame;
        if t == 4 {
            AttackModule::clear_all(boma);
        }
        if t >= 22 {
            return finish(fighter, false);
        }
    }
    0.into()
}

// ───────────── B côté : Termite / Croco ─────────────

unsafe extern "C" fn special_s_pre(fighter: &mut L2CFighterCommon) -> L2CValue {
    pre_special(fighter, false, *FIGHTER_POWER_UP_ATTACK_BIT_SPECIAL_S, *FIGHTER_LOG_MASK_FLAG_ATTACK_KIND_SPECIAL_S)
}

unsafe extern "C" fn special_s_main(fighter: &mut L2CFighterCommon) -> L2CValue {
    let s = st(fighter.module_accessor);
    s.timer = 0;
    s.croco = s.skulls >= 1;
    if s.croco {
        s.skulls -= 1;
    }
    println!("[mumbo_mod] B côté : {} (crânes restants={})", if s.croco { "Croco" } else { "Termite" }, s.skulls);
    apply_situation(fighter, true);
    set_motion(fighter, "special_s", "special_air_s");
    shift_main(fighter, special_s_loop)
}

unsafe extern "C" fn special_s_loop(fighter: &mut L2CFighterCommon) -> L2CValue {
    let boma = fighter.module_accessor;
    let s = st(boma);
    s.timer += 1;
    apply_situation(fighter, false);
    let t = s.timer;

    if !s.croco {
        // Termite : petite charge rapide, coups répétés toutes les 6 frames.
        if (6..30).contains(&t) {
            push_forward(fighter, 1.8);
        }
        if t == 6 {
            hit(fighter, 0, 1.5, 45, 40, 0, 20, 5.0, 5.0, 4.0, None, 6, "collision_attr_normal");
        }
        if t == 30 {
            AttackModule::clear_all(boma);
            hit(fighter, 0, 4.0, 40, 90, 0, 45, 6.0, 5.0, 5.0, None, 0, "collision_attr_normal");
        }
        if t == 33 {
            AttackModule::clear_all(boma);
        }
        if t >= 42 {
            return finish(fighter, false);
        }
    } else {
        // Croco : courte avancée puis grosse morsure.
        if (8..14).contains(&t) {
            push_forward(fighter, 1.2);
        }
        if t == 12 {
            hit(fighter, 0, 16.0, 40, 95, 0, 45, 7.0, 7.0, 10.0, None, 0, "collision_attr_cutup");
            purple_flash(fighter, "sys_hit_magic", 0.35);
        }
        if t == 16 {
            AttackModule::clear_all(boma);
        }
        if t >= 40 {
            return finish(fighter, false);
        }
    }
    0.into()
}

// ───────────── B haut : lévitation ─────────────

unsafe extern "C" fn special_hi_pre(fighter: &mut L2CFighterCommon) -> L2CValue {
    pre_special(fighter, true, *FIGHTER_POWER_UP_ATTACK_BIT_SPECIAL_HI, *FIGHTER_LOG_MASK_FLAG_ATTACK_KIND_SPECIAL_HI)
}

unsafe extern "C" fn special_hi_main(fighter: &mut L2CFighterCommon) -> L2CValue {
    let boma = fighter.module_accessor;
    st(boma).timer = 0;
    println!("[mumbo_mod] B haut : lévitation commence");
    GroundModule::correct(boma, GroundCorrectKind(*GROUND_CORRECT_KIND_AIR));
    set_motion(fighter, "special_air_hi_hold", "special_air_hi_hold");
    shift_main(fighter, special_hi_loop)
}

unsafe extern "C" fn special_hi_loop(fighter: &mut L2CFighterCommon) -> L2CValue {
    let boma = fighter.module_accessor;
    let s = st(boma);
    s.timer += 1;
    let t = s.timer;

    if t <= 36 {
        // Montée : la gravité est remplacée par une vitesse ascendante ; la dérive reste contrôlable.
        sv_kinetic_energy!(set_speed, fighter, *FIGHTER_KINETIC_ENERGY_ID_GRAVITY, 1.4);
    }
    if t == 4 {
        hit(fighter, 0, 1.3, 90, 100, 45, 0, 7.0, 8.0, 0.0, None, 5, "collision_attr_elec");
        purple_flash(fighter, "sys_hit_elec", 0.8);
    }
    if t == 36 {
        AttackModule::clear_all(boma);
        hit(fighter, 0, 5.0, 80, 120, 0, 50, 9.0, 8.0, 0.0, None, 0, "collision_attr_elec");
    }
    if t == 40 {
        AttackModule::clear_all(boma);
    }
    if t >= 44 {
        return finish(fighter, true);
    }
    0.into()
}

// ───────────── B bas : socle ─────────────

unsafe extern "C" fn special_lw_pre(fighter: &mut L2CFighterCommon) -> L2CValue {
    pre_special(fighter, false, *FIGHTER_POWER_UP_ATTACK_BIT_SPECIAL_LW, *FIGHTER_LOG_MASK_FLAG_ATTACK_KIND_SPECIAL_LW)
}

unsafe extern "C" fn special_lw_main(fighter: &mut L2CFighterCommon) -> L2CValue {
    st(fighter.module_accessor).timer = 0;
    apply_situation(fighter, true);
    set_motion(fighter, "special_lw_start", "special_air_lw_start");
    shift_main(fighter, special_lw_loop)
}

/// Ralentit les adversaires présents sur le socle (effet 0). Chacun n'est touché qu'une fois.
unsafe fn slow_victims(fighter: &mut L2CFighterCommon) {
    let boma = fighter.module_accessor;
    let own_id = (*boma).battle_object_id;
    let s = st(boma);
    for id in 0u32..8 {
        if id == own_id || s.slowed_mask & (1 << id) != 0 {
            continue;
        }
        if !sv_battle_object::is_active(id) || sv_battle_object::category(id) != *BATTLE_OBJECT_CATEGORY_FIGHTER {
            continue;
        }
        let victim = sv_battle_object::module_accessor(id);
        let dx = (PostureModule::pos_x(victim) - s.pad_x).abs();
        let dy = (PostureModule::pos_y(victim) - s.pad_y).abs();
        if dx < 12.0 && dy < 14.0 {
            SlowModule::set(victim, 0, 3, 180, false, 0x5000_0000);
            s.slowed_mask |= 1 << id;
        }
    }
}

unsafe extern "C" fn special_lw_loop(fighter: &mut L2CFighterCommon) -> L2CValue {
    let boma = fighter.module_accessor;
    let s = st(boma);
    s.timer += 1;
    apply_situation(fighter, false);
    let t = s.timer;

    if t == 10 {
        let (effect, cost) = match s.skulls {
            0 => (0, 0),
            1 => (1, 1),
            _ => (2, 2),
        };
        s.pad_effect = effect;
        s.skulls -= cost;
        println!("[mumbo_mod] B bas : socle effet {} (crânes restants={})", effect, s.skulls);
        s.slowed_mask = 0;
        s.pad_x = PostureModule::pos_x(boma) + 12.0 * PostureModule::lr(boma);
        s.pad_y = PostureModule::pos_y(boma);
        match effect {
            1 => hit(fighter, 0, 4.0, 361, 30, 0, 20, 9.0, 3.0, 12.0, None, 0, "collision_attr_paralyze"),
            2 => hit(fighter, 0, 6.0, 361, 50, 0, 30, 10.0, 3.0, 12.0, None, 0, "collision_attr_bury"),
            _ => {}
        }
        purple_flash(fighter, "sys_hit_magic", 0.25 + 0.12 * effect as f32);
    }
    if (10..40).contains(&t) && s.pad_effect == 0 {
        slow_victims(fighter);
    }
    if t == 40 {
        AttackModule::clear_all(boma);
    }
    if t >= 50 {
        return finish(fighter, false);
    }
    0.into()
}

// ───────────── Neutralisation des scripts d'origine (PK Fire, PK Flash...) ─────────────

unsafe extern "C" fn acmd_empty(_agent: &mut L2CAgentBase) {}

const SILENCED: [&str; 7] = [
    "specialnstart", "specialairnstart", "specials", "specialairs",
    "specialairhihold", "speciallwstart", "specialairlwstart",
];

pub fn install() {
    let mut ag = Agent::new(HOST);
    for name in SILENCED {
        for prefix in ["game_", "effect_", "sound_", "expression_"] {
            // Les noms doivent vivre toute la durée du jeu : on les « fuit » volontairement.
            let full: &'static str = Box::leak(format!("{prefix}{name}").into_boxed_str());
            ag.acmd(full, acmd_empty, Priority::Low);
        }
    }
    let kinds = [
        (*FIGHTER_STATUS_KIND_SPECIAL_N, special_n_pre as unsafe extern "C" fn(&mut L2CFighterCommon) -> L2CValue, special_n_main as unsafe extern "C" fn(&mut L2CFighterCommon) -> L2CValue),
        (*FIGHTER_STATUS_KIND_SPECIAL_S, special_s_pre, special_s_main),
        (*FIGHTER_STATUS_KIND_SPECIAL_HI, special_hi_pre, special_hi_main),
        (*FIGHTER_STATUS_KIND_SPECIAL_LW, special_lw_pre, special_lw_main),
    ];
    for (kind, pre, main) in kinds {
        ag.status(Pre, kind, pre);
        ag.status(Main, kind, main);
        ag.status(Init, kind, status_noop);
        ag.status(Exec, kind, status_noop);
        ag.status(End, kind, status_noop);
    }
    ag.install();
}
