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
// tok{n}_{k}_root / _jaw / _eyea / _eyeb. set_joint_rotate n'agit que sur les os ayant une piste
// dans l'animation en cours : tools/model/add_token_tracks.py ajoute une piste fixe pour ces os à
// toutes les motions (à relancer si les animations de tools/anim/out changent).
use crate::token_anim::{ANIM, BOB, FRAMES as ANIM_FRAMES};
const ORBIT_RADIUS: f32 = 7.0; // R de add_tokens.py

unsafe fn rotate_bone(boma: *mut smash::app::BattleObjectModuleAccessor, name: &str, x: f32, y: f32, z: f32) {
    ModelModule::set_joint_rotate(boma, Hash40::new(name), &smash::phx::Vector3f { x, y, z },
        smash::app::MotionNodeRotateCompose { _address: *MOTION_NODE_ROTATE_COMPOSE_AFTER as u8 },
        smash::app::MotionNodeRotateOrder { _address: *MOTION_NODE_ROTATE_ORDER_XYZ as u8 });
}
// Matrices 3x3 pour composer l'orbite et l'inclinaison. Convention Euler « XYZ » de Blender
// (R = Rz·Ry·Rx), celle de bake_token_anim.py, que le jeu interprète correctement.
type M3 = [[f32; 3]; 3];
fn mat_mul(a: &M3, b: &M3) -> M3 {
    let mut r = [[0.0; 3]; 3];
    for i in 0..3 { for j in 0..3 { for k in 0..3 { r[i][j] += a[i][k] * b[k][j]; } } }
    r
}
fn from_euler_xyz(x: f32, y: f32, z: f32) -> M3 {
    let (sx, cx) = x.to_radians().sin_cos();
    let (sy, cy) = y.to_radians().sin_cos();
    let (sz, cz) = z.to_radians().sin_cos();
    let rx = [[1.0, 0.0, 0.0], [0.0, cx, -sx], [0.0, sx, cx]];
    let ry = [[cy, 0.0, sy], [0.0, 1.0, 0.0], [-sy, 0.0, cy]];
    let rz = [[cz, -sz, 0.0], [sz, cz, 0.0], [0.0, 0.0, 1.0]];
    mat_mul(&rz, &mat_mul(&ry, &rx))
}
fn to_euler_xyz(m: &M3) -> [f32; 3] {
    let y = (-m[2][0]).clamp(-1.0, 1.0).asin();
    let x = m[2][1].atan2(m[2][2]);
    let z = m[1][0].atan2(m[0][0]);
    [x.to_degrees(), y.to_degrees(), z.to_degrees()]
}
/// Rotation d'axe ω (radians, petit angle) par la formule de Rodrigues.
fn small_rotation(x: f32, y: f32, z: f32) -> M3 {
    let a = (x * x + y * y + z * z).sqrt();
    if a < 1e-6 { return [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]]; }
    let (u, v, w) = (x / a, y / a, z / a);
    let (s, c) = a.sin_cos();
    let t = 1.0 - c;
    [[c + u * u * t, u * v * t - w * s, u * w * t + v * s],
     [v * u * t + w * s, c + v * v * t, v * w * t - u * s],
     [w * u * t - v * s, w * v * t + u * s, c + w * w * t]]
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
    // Animation du token (01_Modeles_3D/work/Mumbo token_ssbu.blend), boucle de 6 s précalculée.
    let i = (s.orbit_t as usize) % ANIM_FRAMES;
    s.orbit_t = s.orbit_t.wrapping_add(1);
    let a = &ANIM[i];
    // Lévitation (montée/descente du blend) : le jeu ignore set_joint_translate sur les os des
    // tokens et set_joint_rotate sur les os enfants directs de throw. On incline donc légèrement
    // le plan de l'orbite (petite rotation de throw autour d'un axe horizontal) : chaque token
    // monte de ω × p. L'inclinaison est choisie (moindres carrés) pour que le token k suive
    // BOB décalé de k/n de boucle ; ces décalages réguliers font que la somme des hauteurs,
    // que l'inclinaison ne peut pas produire, reste ~nulle.
    // Repère local de throw : Y vertical, le token k est en (-R·sin θk, H, R·cos θk).
    let (mut wx, mut wz) = (0.0f32, 0.0f32);
    for k in 0..n {
        let th = k as f32 * core::f32::consts::TAU / n as f32;
        let dz = BOB[(i + k * ANIM_FRAMES / n) % ANIM_FRAMES][1];
        wx -= dz * th.cos();
        wz -= dz * th.sin();
    }
    let c = if n == 1 { 1.0 } else { 2.0 / n as f32 } / ORBIT_RADIUS;
    let tilt = small_rotation(wx * c, 0.0, wz * c);
    let [ex, ey, ez] = to_euler_xyz(&mat_mul(&from_euler_xyz(a[0], a[1], a[2]), &tilt));
    rotate_bone(boma, "throw", ex, ey, ez);
    for k in 0..n {
        // Chaque token joue la même boucle, décalée pour ne pas bouger en même temps.
        let b = &ANIM[(i + k * 137) % ANIM_FRAMES];
        let tag = format!("tok{}_{}", n, k + 1);
        rotate_bone(boma, &format!("{tag}_root"), b[3], b[4], b[5]);
        rotate_bone(boma, &format!("{tag}_jaw"), b[6], b[7], b[8]);
        rotate_bone(boma, &format!("{tag}_eyea"), b[9], b[10], b[11]);
        rotate_bone(boma, &format!("{tag}_eyeb"), b[12], b[13], b[14]);
    }
}

unsafe extern "C" fn diag_start(_fighter: &mut L2CFighterCommon) {
    println!("[mumbo_mod] on_start déclenché");
}

pub fn install() {
    Agent::new(HOST).on_start(diag_start).on_line(Main, mumbo_frame).install();
}
