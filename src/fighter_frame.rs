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
        orbit_skulls(fighter, st(boma), false);
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

// ───────────── Mumbo Tokens en orbite (jauge visuelle) ─────────────
// Les tokens sont de vrais meshes du modèle c00 (tools/model/add_tokens.py). Un jeu de meshes
// par niveau de jauge : mumbo_tok{n}_{k}, n tokens régulièrement espacés. On n'affiche que le jeu
// correspondant au nombre de crânes.
// Os : « throw » (inutilisé par Mumbo hors projections) porte l'orbite ; chaque token a ses os
// h_tok{n}_{k}_root / _jaw / _eyea / _eyeb (repère local : Y vertical, Z vers l'avant du token).
const ORBIT_SPEED_DEG: f32 = 150.0; // °/s
const TAU: f32 = core::f32::consts::TAU;

fn smooth(x: f32) -> f32 {
    let x = x.clamp(0.0, 1.0);
    x * x * (3.0 - 2.0 * x)
}

/// Regard en boucle : gauche, haut, droite, haut, gauche… -> (tangage, lacet) en degrés.
fn gaze(t: f32) -> (f32, f32) {
    const KEYS: [(f32, f32); 4] = [(0.0, -28.0), (-24.0, 0.0), (0.0, 28.0), (-24.0, 0.0)];
    const SEG: f32 = 0.75; // s par regard (pause puis transition)
    const HOLD: f32 = 0.35;
    let u = (t / SEG).rem_euclid(4.0);
    let i = u as usize % 4;
    let a = KEYS[i];
    let b = KEYS[(i + 1) % 4];
    let f = smooth((u.fract() * SEG - HOLD) / (SEG - HOLD));
    (a.0 + (b.0 - a.0) * f, a.1 + (b.1 - a.1) * f)
}

unsafe fn rotate_bone(boma: *mut smash::app::BattleObjectModuleAccessor, name: &str, x: f32, y: f32, z: f32) {
    ModelModule::set_joint_rotate(boma, Hash40::new(name), &smash::phx::Vector3f { x, y, z },
        smash::app::MotionNodeRotateCompose { _address: *MOTION_NODE_ROTATE_COMPOSE_AFTER as u8 },
        smash::app::MotionNodeRotateOrder { _address: *MOTION_NODE_ROTATE_ORDER_XYZ as u8 });
}
const TOKEN_MESHES: [[&str; 3]; 3] = [
    ["mumbo_tok1_1", "", ""],
    ["mumbo_tok2_1", "mumbo_tok2_2", ""],
    ["mumbo_tok3_1", "mumbo_tok3_2", "mumbo_tok3_3"],
];

unsafe fn is_throw_status(status: i32) -> bool {
    (*FIGHTER_STATUS_KIND_CATCH..=*FIGHTER_STATUS_KIND_THROW).contains(&status)
        || status == *FIGHTER_STATUS_KIND_THROW_KIRBY
}

pub unsafe fn orbit_skulls(fighter: &mut L2CFighterCommon, s: &mut MumboState, visible: bool) {
    let boma = fighter.module_accessor;
    let status = StatusModule::status_kind(boma);
    let n = s.skulls.clamp(0, MAX_SKULLS) as usize;
    let show = visible && n > 0 && !is_throw_status(status);
    for (lvl, set) in TOKEN_MESHES.iter().enumerate() {
        for name in set.iter().filter(|m| !m.is_empty()) {
            ModelModule::set_mesh_visibility(boma, Hash40::new(name), show && lvl + 1 == n);
        }
    }
    if !show { return; }
    let t = (s.orbit_t % (60 * 3600)) as f32 / 60.0;
    s.orbit_t = s.orbit_t.wrapping_add(1);
    // Orbite + plan d'orbite qui ondule : chaque token monte et descend à son rythme (lévitation).
    rotate_bone(boma, "throw", 4.0 * (t * 1.1).sin(), (t * ORBIT_SPEED_DEG) % 360.0, 3.0 * (t * 0.8 + 1.0).sin());
    for k in 0..n {
        let p = k as f32 * 2.1; // déphasage entre tokens
        let tag = format!("h_tok{}_{}", n, k + 1);
        // Léger balancement du token sur lui-même.
        rotate_bone(boma, &format!("{tag}_root"),
            5.0 * (t * 1.9 + p).sin(), 7.0 * (t * 1.2 + p).sin(), 4.0 * (t * 1.4 + p).sin());
        // Bouche : ouvre et ferme en continu.
        let open = 0.5 - 0.5 * (t * TAU / 1.1 + p).cos();
        rotate_bone(boma, &format!("{tag}_jaw"), 24.0 * open * open, 0.0, 0.0);
        // Yeux : gauche, haut, droite, haut, gauche…
        let (pitch, yaw) = gaze(t + k as f32 * 0.25);
        rotate_bone(boma, &format!("{tag}_eyea"), pitch, yaw, 0.0);
        rotate_bone(boma, &format!("{tag}_eyeb"), pitch, yaw, 0.0);
    }
}

unsafe extern "C" fn diag_start(_fighter: &mut L2CFighterCommon) {
    println!("[mumbo_mod] on_start déclenché");
}

pub fn install() {
    Agent::new(HOST).on_start(diag_start).on_line(Main, mumbo_frame).install();
}
