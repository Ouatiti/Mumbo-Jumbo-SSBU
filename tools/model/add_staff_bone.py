"""Rattache le baton a son propre os, MumboStaff, pour que son animation soit visible en jeu.

blender -b --factory-startup -P tools/model/add_staff_bone.py   (apres add_tokens.py, avant add_token_tracks.py)
Le rendu du jeu ne suit pas les pistes de l'os HaveR (os de prise d'objet) : verifie en jeu, ni
l'animation ni set_joint_rotate/translate ne deplacent le maillage, alors que le moteur (hitboxes,
effets) lit bien la position animee. On ajoute donc un jumeau de HaveR sous HandR, on y reporte les
poids du baton, et add_token_tracks.py recopie la piste HaveR des animations Mumbo sur ce jumeau.
Modifie mumbo_build/out_tok (model.nusktb et model.numshb) ; peut etre relance sans risque.
"""
import bpy
from importlib import import_module

ROOT = r"E:\Project Mumbo\Emulateurs_Mumbo_Banjo"
EXP = ROOT + r"\mumbo_build\out_tok" + "\\"
SRC, NEW = "HaveR", "MumboStaff"

bpy.ops.preferences.addon_enable(module="smash-ultimate-blender")
ssbh = import_module("smash-ultimate-blender.dependencies.ssbh_data_py")

skel = ssbh.skel_data.read_skel(EXP + "model.nusktb")
bones = list(skel.bones)
if not any(b.name == NEW for b in bones):
    i = next(k for k, b in enumerate(bones) if b.name == SRC)
    twin = ssbh.skel_data.BoneData(NEW, bones[i].transform, bones[i].parent_index, bones[i].billboard_type)
    # insere juste apres HaveR : les indices des parents situes plus loin sont decales d'un cran
    for b in bones:
        if b.parent_index is not None and b.parent_index > i:
            b.parent_index += 1
    bones.insert(i + 1, twin)
    skel.bones = bones
    skel.save(EXP + "model.nusktb")

mesh = ssbh.mesh_data.read_mesh(EXP + "model.numshb")
moved = []
for o in mesh.objects:
    infl = list(o.bone_influences)
    for b in infl:
        if b.bone_name == SRC:
            b.bone_name = NEW
            moved.append((o.name, len(b.vertex_weights)))
    o.bone_influences = infl
    if o.parent_bone_name == SRC:
        o.parent_bone_name = NEW
mesh.save(EXP + "model.numshb")

check = ssbh.skel_data.read_skel(EXP + "model.nusktb").bones
for k, b in enumerate(check):
    if b.name in (SRC, NEW, "HandR"):
        print("STAFF os", k, b.name, "parent", check[b.parent_index].name)
left = [o.name for o in ssbh.mesh_data.read_mesh(EXP + "model.numshb").objects
        if any(b.bone_name == SRC for b in o.bone_influences)]
print("STAFF deplaces", moved, "restent sur", SRC, left)
