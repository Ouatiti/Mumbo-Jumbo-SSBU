// Jauge de crânes (0..=3) : variable de work de l'hôte, gain par dégâts infligés, effet sur le bâton.
use smash::app::lua_bind::*;
use smash::lib::lua_const::*;
use smash::lua2cpp::L2CFighterCommon;
use smashline::*;

/// Variable de work libre (à adapter si elle entre en collision avec une autre du mod).
pub const SKULLS: i32 = 0x1000_0001;
/// Cumul de dégâts infligés depuis le dernier crâne (stocké en flottant).
pub const DMG_ACC: i32 = 0x1000_0002;
pub const MAX_SKULLS: i32 = 3;
/// Un crâne tous les X % de dégâts normaux infligés.
pub const DMG_PER_SKULL: f32 = 30.0;

unsafe extern "C" fn mumbo_frame(fighter: &mut L2CFighterCommon) {
    let module_accessor = fighter.module_accessor;
    let status = StatusModule::status_kind(module_accessor);

    // Réinitialisation à la mort / au respawn.
    if status == *FIGHTER_STATUS_KIND_ENTRY || status == *FIGHTER_STATUS_KIND_DEAD {
        WorkModule::set_int(module_accessor, 0, SKULLS);
        WorkModule::set_float(module_accessor, 0.0, DMG_ACC);
        return;
    }

    // Gain : on lit le dernier hit porté par une attaque normale.
    // (À affiner : brancher ici le hook sur le dégât réellement infligé.)
    let skulls = WorkModule::get_int(module_accessor, SKULLS);
    if skulls < MAX_SKULLS && WorkModule::get_float(module_accessor, DMG_ACC) >= DMG_PER_SKULL {
        WorkModule::set_int(module_accessor, skulls + 1, SKULLS);
        WorkModule::set_float(module_accessor, 0.0, DMG_ACC);
    }

    // Indicateur visuel : une particule sur le bâton, d'intensité = nombre de crânes.
    // Placeholder : à remplacer par des effets du mod une fois ton modèle intégré.
    let skulls = WorkModule::get_int(module_accessor, SKULLS);
    if skulls > 0 && smash::app::sv_information::is_ready_go() && MotionModule::frame(module_accessor) as i32 % 8 == 0 {
        // EffectModule::req_follow(module_accessor, Hash40::new("ness_pkflash_hold"), Hash40::new("haver"), &Vector3f{x:0.0,y:0.0,z:0.0}, &Vector3f{x:0.0,y:0.0,z:0.0}, 0.3 * skulls as f32, false, 0, 0, 0, 0, 0, false, false);
    }
}

/// À appeler depuis les scripts de normales : ajoute les dégâts d'un coup connecté.
pub unsafe fn add_damage(module_accessor: *mut smash::app::BattleObjectModuleAccessor, dmg: f32) {
    let acc = WorkModule::get_float(module_accessor, DMG_ACC);
    WorkModule::set_float(module_accessor, acc + dmg, DMG_ACC);
}

pub fn install() {
    Agent::new("ness").on_line(Main, mumbo_frame).install();
}
