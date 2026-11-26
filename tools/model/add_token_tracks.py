"""Ajoute une piste fixe (pose de repos) pour chaque os Tok* dans toutes les animations de Ness.

blender -b -P tools/model/add_token_tracks.py
Le jeu n'applique ModelModule::set_joint_rotate qu'aux os presents dans l'animation en cours :
sans piste, les os des tokens (machoire, yeux, racine) restent figes. On ajoute donc a chaque
.nuanmb une piste constante egale a leur transformation de repos (lue dans le model.nusktb exporte
par add_tokens.py) ; le code Rust compose ensuite l'animation du blend par-dessus.
Sources : les animations propres a Mumbo (tools/anim/out) sinon celles de Ness vanilla.
Sortie : mumbo_build/out_motion (a copier dans fighter/ness/motion/body/c00 du mod).
"""
import bpy, os
from importlib import import_module
from mathutils import Matrix

ROOT = r"E:\Project Mumbo\Emulateurs_Mumbo_Banjo"
VANILLA = r"E:\Emulateurs\ness_model\fighter\ness\motion\body\c00"
CUSTOM = ROOT + r"\mumbo-mod\tools\anim\out"
SKEL = ROOT + r"\mumbo_build\out_tok\model.nusktb"
OUT = ROOT + r"\mumbo_build\out_motion"
os.makedirs(OUT, exist_ok=True)

bpy.ops.preferences.addon_enable(module="smash-ultimate-blender")
ssbh = import_module("smash-ultimate-blender.dependencies.ssbh_data_py")
A = ssbh.anim_data

def rest_of(b):
    m = Matrix([list(r) for r in b.transform]).transposed()   # ssbh : translation en derniere ligne
    loc, q, sc = m.decompose()
    if q.w < 0:
        q.negate()
    return A.Transform(list(sc), [q.x, q.y, q.z, q.w], list(loc))


skel = ssbh.skel_data.read_skel(SKEL).bones
rest = {b.name: rest_of(b) for b in skel if b.name.startswith("Tok")}
staff_rest = next(rest_of(b) for b in skel if b.name == "MumboStaff")
print("TOK BONES", len(rest))

def trans_node(grp):
    return next((nd for nd in grp.nodes if nd.name == "Trans"), None)


def moves(node):
    v = node.tracks[0].values
    return any(max(x.translation[i] for x in v) - min(x.translation[i] for x in v) > 0.01 for i in range(3))


def restore_root_motion(f, grp):
    """Le jeu deplace le personnage d'apres l'os Trans (marche, course, double saut) : une animation
    Mumbo qui le fige le cloue sur place. On reprend alors la piste Trans de Ness (les autres os sont
    relatifs a Trans, la pose ne change pas)."""
    van = A.read_anim(os.path.join(VANILLA, f))
    vgrp = next(g for g in van.groups if "Transform" in repr(g.group_type))
    mine, ref = trans_node(grp), trans_node(vgrp)
    if mine is None or ref is None or not moves(ref) or moves(mine):
        return
    mine.tracks = ref.tracks
    print("ROOT MOTION", f)


def values(node):
    return [(tuple(v.translation), tuple(v.rotation), tuple(v.scale)) for v in node.tracks[0].values]


def add_staff_track(f, grp):
    """Os MumboStaff (voir add_staff_bone.py) : recopie la piste HaveR quand l'animation Mumbo l'a
    modifiee ; sinon pose de repos, car les mouvements de batte de Ness n'ont jamais ete affiches."""
    node = next((nd for nd in grp.nodes if nd.name == "HaveR"), None)
    van = A.read_anim(os.path.join(VANILLA, f))
    vgrp = next(g for g in van.groups if "Transform" in repr(g.group_type))
    ref = next((nd for nd in vgrp.nodes if nd.name == "HaveR"), None)
    twin = A.NodeData("MumboStaff")
    if node is not None and (ref is None or values(node) != values(ref)):
        twin.tracks = node.tracks
        staffed.append(f)
    else:
        track = A.TrackData("Transform")
        track.values = [staff_rest]
        twin.tracks = [track]
    grp.nodes = [nd for nd in grp.nodes if nd.name != "MumboStaff"] + [twin]


staffed = []
n = 0
for f in sorted(os.listdir(VANILLA)):
    if not f.endswith(".nuanmb"):
        continue
    src = os.path.join(CUSTOM, f) if os.path.exists(os.path.join(CUSTOM, f)) else os.path.join(VANILLA, f)
    anim = A.read_anim(src)
    grp = next((g for g in anim.groups if "Transform" in repr(g.group_type)), None)
    if grp is None:
        continue
    have = {nd.name for nd in grp.nodes}
    if src.startswith(CUSTOM):
        restore_root_motion(f, grp)
    for name, tr in rest.items():
        if name in have:
            continue
        track = A.TrackData("Transform")
        track.values = [tr]
        node = A.NodeData(name)
        node.tracks = [track]
        grp.nodes.append(node)
    # Les os doivent rester tries par nom comme dans les fichiers du jeu : sinon le jeu ne retrouve
    # plus Trans et les mouvements pilotes par l'animation (marche, course, double saut) restent sur place.
    add_staff_track(f, grp)
    grp.nodes = sorted(grp.nodes, key=lambda nd: nd.name)
    anim.save(os.path.join(OUT, f))
    n += 1
print("STAFF animes", len(staffed), staffed)
print("WROTE", n)
