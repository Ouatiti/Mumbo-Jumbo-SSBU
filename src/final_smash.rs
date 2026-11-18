// Final Smash « Golden Goliath » : Mumbo se change en statue géante dorée (lourde, façon
// Ganon/Métal), écrase le sol, avance en balayant tout, puis explose en décharge magique.
//
// Le déroulé est piloté frame par frame depuis le hook du combattant (goliath_frame) plutôt
// que par les scripts ACMD : il ne dépend donc pas de la durée des animations de Ness.
//   f1        transformation : flash doré, échelle x GIANT, séisme
//   f1..      teinte dorée maintenue (FLASH) + aura dorée
//   f20..140  avance de WALK_SPEED/frame ; hitbox de balayage (multi-coups, re-armée toutes les 8 f)
//             piétinement toutes les 20 f : hitbox au sol + séisme + fumée
//   f150      décharge magique : grosse explosion éjectrice
//   f156      retour à la normale (échelle, couleur)
// Si le statut FS se termine avant, on remet tout à zéro proprement.
use crate::state::MumboState;
use smash::app::lua_bind::*;
use smash::app::sv_animcmd::frame;
use smash::lib::lua_const::*;
use smash::app::GroundCorrectKind;
use smash::lib::{L2CValue, L2CValueType};
use smash::lua2cpp::{L2CAgentBase, L2CFighterCommon};
use smash::phx::{Hash40, Vector3f, Vector4f};
use smash_script::*;
use smashline::*;

const GIANT: f32 = 2.6;
const WALK_START: i32 = 20;
const WALK_END: i32 = 140;
const WALK_SPEED: f32 = 0.6;
const STOMP_EVERY: i32 = 20;
const EXPLODE: i32 = 150;
const END: i32 = 156;
const GOLD: (f32, f32, f32) = (1.0, 0.8, 0.15);

pub unsafe fn is_fs_status(status: i32) -> bool {
    status == *FIGHTER_STATUS_KIND_FINAL || status == *FIGHTER_NESS_STATUS_KIND_FINAL_ATTACK
}

unsafe fn hitbox(a: &mut L2CAgentBase, id: u64, dmg: f32, angle: u64, kbg: i32, bkb: i32, size: f32,
                 y: f32, z: f32, lvl: i32) {
    macros::ATTACK(a, id, 0, Hash40::new("top"), dmg, angle, kbg, 0, bkb, size, 0.0, y, z,
        None, None, None, 1.0, 1.0, *ATTACK_SETOFF_KIND_OFF, *ATTACK_LR_CHECK_F, false, 0, 0.0, 0,
        false, false, false, false, true, *COLLISION_SITUATION_MASK_GA_d, *COLLISION_CATEGORY_MASK_ALL,
        *COLLISION_PART_MASK_ALL, false, Hash40::new("collision_attr_magic"), lvl,
        *COLLISION_SOUND_ATTR_HEAVY, *ATTACK_REGION_OBJECT);
}

unsafe fn finish(fighter: &mut L2CFighterCommon, s: &mut MumboState) {
    let boma = fighter.module_accessor;
    AttackModule::clear_all(boma);
    ModelModule::set_scale(boma, 1.0);
    ColorBlendModule::cancel_main_color(boma, 0);
    macros::COL_NORMAL(fighter);
    s.fs_frame = 0;
}

pub unsafe fn goliath_frame(fighter: &mut L2CFighterCommon, s: &mut MumboState, in_fs: bool) {
    let boma = fighter.module_accessor;
    if !in_fs {
        if s.fs_frame != 0 { finish(fighter, s); }
        return;
    }
    if s.fs_frame >= END { return; } // terminé : on attend la fin du statut
    s.fs_frame += 1;
    let f = s.fs_frame;
    let lr = PostureModule::lr(boma);

    if f == 1 {
        s.fs_x = PostureModule::pos_x(boma);
        ModelModule::set_scale(boma, GIANT);
        macros::EFFECT_FOLLOW(fighter, Hash40::new("sys_sp_flash"), Hash40::new("top"), 0, 12, 0, 0, 0, 0, 1.2, true);
        macros::LAST_EFFECT_SET_COLOR(fighter, GOLD.0, GOLD.1, GOLD.2);
        macros::QUAKE(fighter, *CAMERA_QUAKE_KIND_M);
        macros::PLAY_SE(fighter, Hash40::new("se_common_final_hit"));
        println!("[mumbo_mod] Golden Goliath !");
    }
    if f < END {
        ModelModule::set_scale(boma, GIANT); // le moteur peut la réinitialiser : on la maintient
    }
    if f < EXPLODE {
        // statue d'or : teinte dorée maintenue + aura dorée pulsée
        // (FLASH depuis le hook n'est pas appliqué : on passe par ColorBlendModule)
        let c = Vector4f { x: GOLD.0, y: GOLD.1, z: GOLD.2, w: 0.75 };
        let add = Vector4f { x: 0.35, y: 0.25, z: 0.0, w: 0.75 };
        ColorBlendModule::set_main_color(boma, &c, &add, 1.0, 1.0, 0, true);
        if f % 10 == 1 {
            macros::EFFECT_FOLLOW(fighter, Hash40::new("sys_aura_light"), Hash40::new("hip"), 0, 0, 0, 0, 0, 0, 1.4, true);
            macros::LAST_EFFECT_SET_COLOR(fighter, GOLD.0, GOLD.1, GOLD.2);
            macros::LAST_EFFECT_SET_ALPHA(fighter, 0.5);
        }
    }

    if (WALK_START..=WALK_END).contains(&f) {
        // avance lourde
        s.fs_x += WALK_SPEED * lr;
        let pos = Vector3f { x: s.fs_x, y: PostureModule::pos_y(boma), z: 0.0 };
        PostureModule::set_pos(boma, &pos);
        // balayage : multi-coups qui pousse vers l'avant (re-armé toutes les 8 f)
        if (f - WALK_START) % 8 == 0 {
            AttackModule::clear(boma, 0, false);
            hitbox(fighter, 0, 3.0, 40, 30, 40, 16.0, 14.0, 12.0, *ATTACK_SOUND_LEVEL_M);
        }
        // piétinement
        if (f - WALK_START) % STOMP_EVERY == 0 {
            AttackModule::clear(boma, 1, false);
            hitbox(fighter, 1, 6.0, 80, 40, 50, 14.0, 2.0, 6.0, *ATTACK_SOUND_LEVEL_L);
            macros::QUAKE(fighter, *CAMERA_QUAKE_KIND_M);
            macros::LANDING_EFFECT(fighter, Hash40::new("sys_landing_smoke"), Hash40::new("top"), 0, 0, 0, 0, 0, 0, 2.2, 0, 0, 0, 0, 0, 0, false);
            macros::PLAY_SE(fighter, Hash40::new("se_common_landing_metal"));
        } else if (f - WALK_START) % STOMP_EVERY == 3 {
            AttackModule::clear(boma, 1, false);
        }
    }
    if f == WALK_END + 1 {
        AttackModule::clear_all(boma);
    }

    if f == EXPLODE {
        AttackModule::clear_all(boma);
        hitbox(fighter, 0, 30.0, 50, 90, 80, 32.0, 14.0, 0.0, *ATTACK_SOUND_LEVEL_L);
        ColorBlendModule::cancel_main_color(boma, 0);
        macros::COL_NORMAL(fighter);
        macros::EFFECT(fighter, Hash40::new("sys_bomb_b"), Hash40::new("top"), 0, 14, 0, 0, 0, 0, 2.5, 0, 0, 0, 0, 0, 0, false);
        macros::LAST_EFFECT_SET_COLOR(fighter, 0.6, 0.2, 1.0);
        macros::EFFECT_FOLLOW(fighter, Hash40::new("sys_sp_flash"), Hash40::new("top"), 0, 14, 0, 0, 0, 0, 2.0, true);
        macros::LAST_EFFECT_SET_COLOR(fighter, GOLD.0, GOLD.1, GOLD.2);
        macros::QUAKE(fighter, *CAMERA_QUAKE_KIND_L);
        macros::PLAY_SE(fighter, Hash40::new("se_common_bomb_l"));
    }
    if f == EXPLODE + 4 {
        AttackModule::clear_all(boma);
    }
    if f == END {
        AttackModule::clear_all(boma);
        ModelModule::set_scale(boma, 1.0);
        macros::CAM_ZOOM_OUT(fighter);
    }
}

// Les scripts ACMD de Ness sont neutralisés (pas d'éclairs PK) : seule la caméra reste.
unsafe extern "C" fn game_finalstart(a: &mut L2CAgentBase) {
    frame(a.lua_state_agent, 1.0);
    if macros::is_excute(a) {
        macros::CAM_ZOOM_IN_arg5(a, 3.0, 0.0, 1.4, 0.0, 0.0);
    }
}
unsafe extern "C" fn game_finalattack(_a: &mut L2CAgentBase) {}

// ───────────── Statut FINAL remplacé ─────────────
// Le statut vanilla de Ness lance la PK Starstorm (articles Paula/Poo + étoiles) : on garde
// son Pre/End (mise en place / nettoyage du FS par le moteur) mais Init/Exec/Main sont les
// nôtres. Main joue une marche lente (pas lourds de la statue) ; le déroulé (échelle, or,
// hitbox, explosion) est piloté par goliath_frame ; on quitte le statut une fois END atteint.
unsafe extern "C" fn final_noop(_f: &mut L2CFighterCommon) -> L2CValue { 0.into() }

unsafe extern "C" fn final_main(fighter: &mut L2CFighterCommon) -> L2CValue {
    let boma = fighter.module_accessor;
    let ground = StatusModule::situation_kind(boma) == *SITUATION_KIND_GROUND;
    if ground {
        GroundModule::correct(boma, GroundCorrectKind(*GROUND_CORRECT_KIND_GROUND_CLIFF_STOP));
        KineticModule::change_kinetic(boma, *FIGHTER_KINETIC_TYPE_GROUND_STOP);
        MotionModule::change_motion(boma, Hash40::new("walk_slow"), 0.0, 0.7, false, 0.0, false, false);
    } else {
        GroundModule::correct(boma, GroundCorrectKind(*GROUND_CORRECT_KIND_AIR));
        KineticModule::change_kinetic(boma, *FIGHTER_KINETIC_TYPE_AIR_STOP);
        MotionModule::change_motion(boma, Hash40::new("fall"), 0.0, 1.0, false, 0.0, false, false);
    }
    // (pas de zoom caméra : la statue géante doit rester entièrement visible)
    let mut v = L2CValue::new_void();
    v.val_type = L2CValueType::Pointer;
    v.inner.raw = final_loop as *const () as u64;
    fighter.sub_shift_status_main(v)
}

unsafe extern "C" fn final_loop(fighter: &mut L2CFighterCommon) -> L2CValue {
    let boma = fighter.module_accessor;
    // marche en boucle
    if MotionModule::is_end(boma) {
        let m = MotionModule::motion_kind(boma);
        MotionModule::change_motion(boma, smash::phx::Hash40 { hash: m }, 0.0, 0.7, false, 0.0, false, false);
    }
    if crate::state::st(boma).fs_frame >= END {
        WorkModule::off_flag(boma, *FIGHTER_INSTANCE_WORK_ID_FLAG_FINAL);
        let next = if StatusModule::situation_kind(boma) == *SITUATION_KIND_GROUND {
            *FIGHTER_STATUS_KIND_WAIT
        } else {
            *FIGHTER_STATUS_KIND_FALL
        };
        fighter.change_status(next.into(), false.into());
        return 1.into();
    }
    0.into()
}

pub fn install() {
    Agent::new(crate::state::HOST)
        .acmd("game_finalstart", game_finalstart, Priority::Low)
        .acmd("game_finalairstart", game_finalstart, Priority::Low)
        .acmd("game_finalattack", game_finalattack, Priority::Low)
        .status(Init, *FIGHTER_STATUS_KIND_FINAL, final_noop)
        .status(Exec, *FIGHTER_STATUS_KIND_FINAL, final_noop)
        .status(Main, *FIGHTER_STATUS_KIND_FINAL, final_main)
        .install();
}
