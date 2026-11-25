"""Ajoute 3 Mumbo Tokens (jauge de cranes en orbite) au modele c00.

blender -b mumbo_build/step2.blend -P tools/model/add_tokens.py
Sortie : mumbo_build/out_tok (fichiers modele) + mumbo_build/step3.blend.
Les tokens sont skinnes a 100% sur l'os 'Throw' (enfant de Rot, inutilise par Mumbo) ;
le code Rust fait tourner cet os pour l'orbite et gere la visibilite mesh par mesh.
"""
import bpy, math, os
import numpy as np

ROOT = r"E:\Project Mumbo\Emulateurs_Mumbo_Banjo"
TOKEN_BLEND = r"E:\Project Mumbo\Modeles_3D_Mumbo\4_Mumbo_Token\crane_jeton.blend"
VANILLA = r"E:\Emulateurs\ness_model\fighter\ness\model\body\c00" + "\\"
EXP = ROOT + r"\mumbo_build\out_tok"
os.makedirs(EXP, exist_ok=True)

N, R, H, SIZE = 3, 7.0, 9.0, 2.6        # nombre, rayon, hauteur, taille du token
DECIM = 0.008                            # le crane source fait 82k sommets

bpy.ops.preferences.addon_enable(module="smash-ultimate-blender")
arm = bpy.data.objects['smush_blender_import']

# ---------- Texture couleur / prm (4 cases : chrome, ivoire, or, gemme) ----------
# Noms de textures vanilla de Ness (non utilises par Mumbo) : pas d'ajout de fichier pour ARCropolis.
CELLS = {'Chrome': 0, 'Ivoire': 1, 'Or': 2, 'Gemme_or': 3}
COL = [(0.78, 0.80, 0.86), (0.93, 0.88, 0.74), (1.0, 0.72, 0.18), (1.0, 0.86, 0.32)]
PRM = [(1.0, 0.22, 1.0, 0.6), (0.0, 0.55, 1.0, 0.5), (1.0, 0.30, 1.0, 0.6), (0.6, 0.15, 1.0, 0.8)]
S = 64

def cell_img(name, vals, colorspace):
    px = np.zeros((S, S, 4), dtype=np.float32)
    for i, v in enumerate(vals):
        cx, cy = i % 2, i // 2
        px[cy * 32:(cy + 1) * 32, cx * 32:(cx + 1) * 32, :len(v)] = v
        if len(v) == 3:
            px[cy * 32:(cy + 1) * 32, cx * 32:(cx + 1) * 32, 3] = 1.0
    im = bpy.data.images.new(name, S, S, alpha=True)
    im.colorspace_settings.name = colorspace
    im.pixels.foreach_set(px.ravel())
    im.pack()
    return im

col_img = cell_img("def_ness_002_col", [(c[0] ** 2.2, c[1] ** 2.2, c[2] ** 2.2) for c in COL], 'sRGB')
prm_img = cell_img("def_ness_002_prm", PRM, 'Non-Color')

mat = bpy.data.materials['mumbo_body'].copy()
mat.name = 'mumbo_token'
for t in mat.sub_matl_data.textures:
    if t.param_id_name == 'Texture0':
        t.image = col_img
    elif t.param_id_name == 'Texture6':
        t.image = prm_img

def cell_uv(i):
    # les pixels Blender partent du bas : la ligne 0 du tableau numpy = v proche de 0
    return ((i % 2) * 0.5 + 0.25, (i // 2) * 0.5 + 0.25)

# ---------- Import et preparation du token ----------
with bpy.data.libraries.load(TOKEN_BLEND) as (src, dst):
    dst.objects = [n for n in src.objects if n in ('Crane', 'Croc', 'Croc.001', 'Croc.002', 'Croc_or', 'Oeil_D', 'Oeil_G')]
parts = []
for o in dst.objects:
    bpy.context.scene.collection.objects.link(o)
    o.data = o.data.copy()
    parts.append(o)

for o in parts:
    ms = [s.material for s in o.material_slots if s.material] + [x for x in o.data.materials if x]
    m = ms[0].name.split('.')[0] if ms else 'Chrome'
    print("PART", o.name, m, len(o.data.vertices))
    o['cell'] = CELLS.get(m, 0)
    if o.name.startswith('Crane'):
        bpy.context.view_layer.objects.active = o
        d = o.modifiers.new('dec', 'DECIMATE'); d.ratio = DECIM
        bpy.ops.object.select_all(action='DESELECT'); o.select_set(True)
        bpy.ops.object.modifier_apply(modifier='dec')
    # UV : chaque face pointe au centre de la case de son materiau
    me = o.data
    while me.uv_layers:
        me.uv_layers.remove(me.uv_layers[0])
    uv = me.uv_layers.new(name='map1')
    u, v = cell_uv(o['cell'])
    uv.data.foreach_set('uv', [u, v] * len(uv.data))
    me.materials.clear(); me.materials.append(mat)

bpy.ops.object.select_all(action='DESELECT')
for o in parts:
    o.select_set(True)
bpy.context.view_layer.objects.active = parts[0]
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
bpy.ops.object.join()
tok = bpy.context.view_layer.objects.active
me = tok.data
# Recentre et met a l'echelle
co = np.array([v.co[:] for v in me.vertices])
lo, hi = co.min(0), co.max(0)
c = (lo + hi) / 2
k = SIZE / (hi[2] - lo[2])
for vtx in me.vertices:
    vtx.co = (vtx.co - __import__('mathutils').Vector(c)) * k
print("TOKEN faces", len(me.polygons), "verts", len(me.vertices))

for ca in list(me.color_attributes):
    me.color_attributes.remove(ca)
ca = me.color_attributes.new('colorSet1', 'BYTE_COLOR', 'CORNER')
ca.data.foreach_set('color', [0.5, 0.5, 0.5, 0.5] * len(ca.data))

# ---------- 3 copies autour du personnage, skinnees sur Throw ----------
# Un jeu de meshes par niveau de jauge (1, 2 ou 3 tokens regulierement espaces) :
# le code n'affiche que le jeu mumbo_tok{n}_* correspondant au nombre de cranes.
from mathutils import Matrix
base = tok.data.copy()
first = True
for n in range(1, N + 1):
  for i in range(n):
    th = i * 2 * math.pi / n
    o = tok if first else tok.copy()
    if not first:
        o.data = base.copy()
        bpy.context.scene.collection.objects.link(o)
    first = False
    o.name = o.data.name = f"mumbo_tok{n}_{i + 1}"
    # face (-Y) tournee vers l'exterieur
    M = Matrix.Translation((R * math.sin(th), -R * math.cos(th), H)) @ Matrix.Rotation(-th, 4, 'Z')
    o.data.transform(M)
    o.matrix_world = Matrix.Identity(4)
    for vg in list(o.vertex_groups):
        o.vertex_groups.remove(vg)
    g = o.vertex_groups.new(name='Throw')
    g.add(list(range(len(o.data.vertices))), 1.0, 'REPLACE')
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
