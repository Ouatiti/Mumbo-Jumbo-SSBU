"""Ajoute les Mumbo Tokens (jauge de cranes en orbite) au modele c00.

blender -b mumbo_build/step2.blend -P tools/model/add_tokens.py
Source : 01_Modeles_3D/Mumbo token_ssbu.glb (crane, mandibule, 2 yeux, textures PBR).
Sortie : mumbo_build/out_tok (fichiers modele) + mumbo_build/step3.blend.
Les tokens sont skinnes a 100% sur l'os 'Throw' (enfant de Rot, inutilise par Mumbo) ;
le code Rust fait tourner cet os pour l'orbite et gere la visibilite mesh par mesh.
"""
import bpy, math, os
import numpy as np
from mathutils import Matrix, Vector

ROOT = r"E:\Project Mumbo\Emulateurs_Mumbo_Banjo"
TOKEN_GLB = r"E:\Project Mumbo\01_Modeles_3D\Mumbo token_ssbu.glb"
VANILLA = r"E:\Emulateurs\ness_model\fighter\ness\model\body\c00" + "\\"
EXP = ROOT + r"\mumbo_build\out_tok"
os.makedirs(EXP, exist_ok=True)

N, R, H, SIZE = 3, 7.0, 9.0, 2.6        # nombre, rayon, hauteur, taille du token
TEX = 512                               # resolution d'une demi-planche
# Le modele source est tres dense (Tripo) : on le decime fortement.
DECIM = {'Mumbo_token_crane': 0.03, 'Mumbo_token_mandibule': 0.04, 'Eye_L': 0.012, 'Eye_R': 0.012}

bpy.ops.preferences.addon_enable(module="smash-ultimate-blender")
arm = bpy.data.objects['smush_blender_import']
before = set(bpy.data.objects)
bpy.ops.import_scene.gltf(filepath=TOKEN_GLB)
imported = [o for o in bpy.data.objects if o not in before]
bpy.context.scene.frame_set(0)


def tex_of(mat, socket):
    b = next(n for n in mat.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
    stack = [l.from_node for l in b.inputs[socket].links]
    while stack:
        n = stack.pop()
        if n.type == 'TEX_IMAGE':
            return n.image
        stack += [l.from_node for i in n.inputs for l in i.links]


def pix(im):
    im = im.copy()
    im.scale(TEX, TEX)
    a = np.empty(TEX * TEX * 4, dtype=np.float32)
    im.pixels.foreach_get(a)
    bpy.data.images.remove(im)
    return a.reshape(TEX, TEX, 4)


# ---------- Planche de textures : crane a gauche, oeil a droite ----------
# Noms de textures vanilla de Ness (non utilises par Mumbo) : pas d'ajout de fichier pour ARCropolis.
skull_mat = bpy.data.objects['Mumbo_token_crane'].data.materials[0]
eye_mat = bpy.data.objects['Eye_L'].data.materials[0]
col = np.ones((TEX, 2 * TEX, 4), dtype=np.float32)
skull = pix(tex_of(skull_mat, 'Base Color'))
# Chrome : couleur desaturee et eclaircie (en metal, l'albedo teinte les reflets ; le beige donnait du dore).
lum = (skull[..., :3] @ np.array([0.30, 0.59, 0.11], dtype=np.float32))[..., None]
skull[..., :3] = np.clip((lum + 0.15 * (skull[..., :3] - lum)) * 1.25 + 0.08, 0.0, 1.0)
col[:, :TEX] = skull
col[:, TEX:] = pix(tex_of(eye_mat, 'Base Color'))
col[..., 3] = 1.0
orm = pix(tex_of(skull_mat, 'Roughness'))       # glTF ORM : R=occlusion, G=rugosite, B=metal
prm = np.empty_like(col)                         # SSBU prm : R=metal, G=rugosite, B=AO, A=speculaire
one = np.ones_like(orm[..., 0])
prm[:, :TEX] = np.stack([one, np.clip(orm[..., 1] * 0.35, 0.06, 0.3), orm[..., 0], one], -1)
prm[:, TEX:] = (0.0, 0.1, 1.0, 0.6)


def new_img(name, arr, colorspace):
    old = bpy.data.images.get(name)
    if old:
        old.name = name + "_old"
    im = bpy.data.images.new(name, arr.shape[1], arr.shape[0], alpha=True)
    im.colorspace_settings.name = colorspace
    im.pixels.foreach_set(arr.ravel())
    im.pack()
    return im


col_img = new_img("def_ness_002_col", col, 'sRGB')
prm_img = new_img("def_ness_002_prm", prm, 'Non-Color')

mat = bpy.data.materials['mumbo_body'].copy()
mat.name = 'mumbo_token'
for t in mat.sub_matl_data.textures:
    if t.param_id_name == 'Texture0':
        t.image = col_img
    elif t.param_id_name == 'Texture6':
        t.image = prm_img

# ---------- Pieces du token : pose de repos figee en espace monde ----------
dg = bpy.context.evaluated_depsgraph_get()
# Pivots d'animation (espace monde du glb) : charniere de la machoire et centre des yeux.
ga = next(o for o in imported if o.type == 'ARMATURE')
PIVOT = {'root': None,
         'jaw': ga.matrix_world @ ga.pose.bones['Jaw'].head,
         'eyea': ga.matrix_world @ ga.pose.bones['Bone_Eye_L'].head,
         'eyeb': ga.matrix_world @ ga.pose.bones['Bone_Eye_R'].head}
GROUP = {'Mumbo_token_crane': 'root', 'Mumbo_token_mandibule': 'jaw', 'Eye_L': 'eyea', 'Eye_R': 'eyeb'}
parts = []
for name, ratio in DECIM.items():
    src = bpy.data.objects[name]
    me = bpy.data.meshes.new_from_object(src.evaluated_get(dg))
    me.transform(src.matrix_world)
    o = bpy.data.objects.new(name + "_tok", me)
    bpy.context.scene.collection.objects.link(o)
    bpy.context.view_layer.objects.active = o
    bpy.ops.object.select_all(action='DESELECT'); o.select_set(True)
    d = o.modifiers.new('dec', 'DECIMATE'); d.ratio = ratio
    bpy.ops.object.modifier_apply(modifier='dec')
    # UV vers la demi-planche correspondante
    uv = o.data.uv_layers[0]
    a = np.empty(len(uv.data) * 2, dtype=np.float32)
    uv.data.foreach_get('uv', a)
    a = a.reshape(-1, 2) % 1.0
    a[:, 0] = a[:, 0] * 0.5 + (0.5 if name.startswith('Eye') else 0.0)
    uv.data.foreach_set('uv', a.ravel())
    uv.name = 'map1'
    while len(o.data.uv_layers) > 1:
        o.data.uv_layers.remove(o.data.uv_layers[1])
    o.data.materials.clear(); o.data.materials.append(mat)
    o.vertex_groups.new(name=GROUP[name]).add(list(range(len(o.data.vertices))), 1.0, 'REPLACE')
    parts.append(o)

for o in imported:
    bpy.data.objects.remove(o, do_unlink=True)

bpy.ops.object.select_all(action='DESELECT')
for o in parts:
    o.select_set(True)
bpy.context.view_layer.objects.active = parts[0]
bpy.ops.object.join()
tok = bpy.context.view_layer.objects.active
me = tok.data
# Recentre, met a l'echelle et tourne la face (+Y dans le glb) vers -Y
co = np.array([v.co[:] for v in me.vertices])
lo, hi = co.min(0), co.max(0)
c = Vector((lo + hi) / 2)
k = SIZE / (hi[2] - lo[2])
MTOK = Matrix.Rotation(math.pi, 4, 'Z') @ Matrix.Scale(k, 4) @ Matrix.Translation(-c)
me.transform(MTOK)
PIVOT = {g: (MTOK @ p if p is not None else Vector((0, 0, 0))) for g, p in PIVOT.items()}
print("TOKEN faces", len(me.polygons), "verts", len(me.vertices), "pivots", {g: p.to_tuple(2) for g, p in PIVOT.items()})

for ca in list(me.color_attributes):
    me.color_attributes.remove(ca)
ca = me.color_attributes.new('colorSet1', 'BYTE_COLOR', 'CORNER')
ca.data.foreach_set('color', [0.5, 0.5, 0.5, 0.5] * len(ca.data))

# ---------- Copies autour du personnage, skinnees sur leurs propres os ----------
# Un jeu de meshes par niveau de jauge (1, 2 ou 3 tokens regulierement espaces) :
# le code n'affiche que le jeu mumbo_tok{n}_* correspondant au nombre de cranes.
# Chaque token a 4 os (racine au centre, machoire, deux yeux), enfants de 'Throw' qui porte l'orbite.
# Prefixe H_ : l'exporteur les place en fin de squelette, sans decaler les os vanilla de Ness.
# Orientation = celle de Throw tournee comme le token : dans le repere local de chaque os,
# Y est vertical, +Z pointe vers l'avant du token et X est lateral, pour tous les tokens.
bpy.context.view_layer.objects.active = arm
bpy.ops.object.select_all(action='DESELECT'); arm.select_set(True)
bpy.ops.object.mode_set(mode='EDIT')
ebs = arm.data.edit_bones
for eb in [b for b in ebs if b.name.startswith('H_tok')]:
    ebs.remove(eb)
throw_eb = ebs['Throw']
throw_rot = throw_eb.matrix.to_3x3().to_4x4()
placements = []
for n in range(1, N + 1):
    for i in range(n):
        th = i * 2 * math.pi / n
        M = Matrix.Translation((R * math.sin(th), -R * math.cos(th), H)) @ Matrix.Rotation(-th, 4, 'Z')
        tag = f"{n}_{i + 1}"
        bones = {}
        for g in ('root', 'jaw', 'eyea', 'eyeb'):
            eb = ebs.new(f"H_tok{tag}_{g}")
            eb.length = 0.3
            eb.matrix = Matrix.Translation(M @ PIVOT[g]) @ Matrix.Rotation(-th, 4, 'Z') @ throw_rot
            eb.parent = throw_eb if g == 'root' else bones['root']
            eb.use_connect = False
            eb.use_deform = True
            bones[g] = eb
        placements.append((n, i, M, tag))
bpy.ops.object.mode_set(mode='OBJECT')

base = tok.data.copy()
first = True
for n, i, M, tag in placements:
    o = tok if first else tok.copy()
    if not first:
        o.data = base.copy()
        bpy.context.scene.collection.objects.link(o)
    first = False
    o.name = o.data.name = f"mumbo_tok{tag}"
    # face (-Y) tournee vers l'exterieur
    o.data.transform(M)
    o.matrix_world = Matrix.Identity(4)
    for vg in o.vertex_groups:
        vg.name = f"H_tok{tag}_{vg.name}"
    for md in list(o.modifiers):
        o.modifiers.remove(md)
    md = o.modifiers.new('Armature', 'ARMATURE'); md.object = arm
    o.parent = arm
    o.matrix_parent_inverse = arm.matrix_world.inverted()

bpy.ops.wm.save_as_mainfile(filepath=ROOT + r"\mumbo_build\step3.blend")

ssp = bpy.context.scene.sub_scene_properties
ssp.model_export_arma = arm
ssp.vanilla_nusktb = VANILLA + "model.nusktb"
print("EXPORT", bpy.ops.sub.model_exporter(directory=EXP + "\\", linked_nusktb_settings='ORDER_AND_VALUES',
                                           optimize_mesh_weights_to_parent_bone='DISABLED'))
print("DONE")
