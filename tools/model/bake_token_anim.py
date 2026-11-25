"""Convertit l'animation du Mumbo Token (01_Modeles_3D/work/Mumbo token_ssbu.blend) en table Rust.

blender -b "01_Modeles_3D/work/Mumbo token_ssbu.blend" -P tools/model/bake_token_anim.py -- <step3.blend>
Sortie : src/token_anim.rs (avec la levitation en translation). Une ligne par image a 60 i/s (boucle de 6 s), rotations Euler XYZ en degres,
deja exprimees dans le repere local SSBU des os du modele : throw (orbite), tok*_root (levitation),
tok*_jaw, tok*_eyea, tok*_eyeb. Les deltas sont relatifs a l'image 0, pose figee dans le modele
par add_tokens.py.
"""
import bpy, math, sys
from mathutils import Matrix

OUT = r"E:\Project Mumbo\Emulateurs_Mumbo_Banjo\mumbo-mod\src\token_anim.rs"
STEP3 = sys.argv[sys.argv.index('--') + 1]   # mumbo_build/step3.blend (sortie de add_tokens.py)
R_GAME, R_BLEND = 7.0, 0.712                 # rayon d'orbite : add_tokens.py / blend
FPS_OUT = 60

sc = bpy.context.scene
fps_in = sc.render.fps
f0, f1 = sc.frame_start, sc.frame_end           # 1..181, la derniere image = la premiere
n_out = round((f1 - f0) / fps_in * FPS_OUT)

pivot = bpy.data.objects['Orbit_Pivot']
offset = bpy.data.objects['Orbit_Offset']
arm = bpy.data.objects['Armature']


def rot3(m):
    return m.to_3x3().normalized()


def sample(t):
    sc.frame_set(int(math.floor(t)), subframe=t - math.floor(t))
    bl = {}
    # Orbite : rotation du pivot en espace monde.
    bl['throw'] = rot3(pivot.matrix_world)
    # Levitation : rotation de l'offset dans le repere du pivot (repere du token).
    bl['root'] = rot3(pivot.matrix_world).inverted() @ rot3(offset.matrix_world)
    # Levitation : position de l'offset dans le repere du pivot (y = rayon, z = hauteur).
    bl['loc'] = pivot.matrix_world.inverted() @ offset.matrix_world.translation
    # Os du token, en espace « token » (repere de l'offset).
    A = rot3(offset.matrix_world).inverted() @ rot3(arm.matrix_world)
    for key, name in (('jaw', 'Jaw'), ('eyea', 'Bone_Eye_L'), ('eyeb', 'Bone_Eye_R')):
        pb = arm.pose.bones[name]
        head = arm.pose.bones['Head'].matrix
        d = rot3(head).inverted() @ rot3(pb.matrix) @ rot3(arm.data.bones[name].matrix_local).inverted() \
            @ rot3(arm.data.bones['Head'].matrix_local)
        bl[key] = A @ d @ A.inverted()
    return bl


rest = sample(0.0)   # add_tokens.py fige la pose de l'image 0
frames = [sample(f0 + i * fps_in / FPS_OUT) for i in range(n_out)]

# Repere des os SSBU : add_tokens.py oriente chaque os comme Throw, tourne comme son token.
bpy.ops.wm.open_mainfile(filepath=STEP3)
throw_rot = bpy.data.objects['smush_blender_import'].data.bones['Throw'].matrix_local.to_3x3().normalized()
RZ = Matrix.Rotation(math.pi, 3, 'Z')            # add_tokens.py tourne le token de 180 deg
P = Matrix(((0, 1, 0), (-1, 0, 0), (0, 0, 1)))  # get_smash_transform de l'exporteur


def to_ssbu(r, flip):
    if flip:
        r = RZ @ r @ RZ.inverted()
    loc = throw_rot.inverted() @ r @ throw_rot
    e = (P @ loc @ P.inverted()).to_euler('XYZ')
    return tuple(math.degrees(a) for a in e)


rows = []
for fr in frames:
    row = []
    for key in ('throw', 'root', 'jaw', 'eyea', 'eyeb'):
        if key == 'throw':
            r = fr[key] @ rest[key].inverted()            # orbite en espace monde
        else:
            r = fr[key] @ rest[key].inverted()
        row += to_ssbu(r, key != 'throw')
    rows.append(row)

# Levitation : ecart (rayon, hauteur) par rapport a l'image 0, a l'echelle de l'orbite du jeu.
k = R_GAME / R_BLEND
bob = [((fr['loc'].y - rest['loc'].y) * k, (fr['loc'].z - rest['loc'].z) * k) for fr in frames]


with open(OUT, 'w', encoding='utf-8') as f:
    f.write("// Genere par tools/model/bake_token_anim.py depuis 01_Modeles_3D/work/Mumbo token_ssbu.blend.\n")
    f.write("// Ne pas modifier a la main. Par image (60 i/s) : [throw, root, jaw, eyea, eyeb] x (x, y, z) en degres.\n")
    f.write(f"pub const FRAMES: usize = {len(rows)};\n")
    f.write(f"pub static ANIM: [[f32; 15]; {len(rows)}] = [\n")
    for row in rows:
        f.write("    [" + ", ".join(f"{v:.2f}" for v in row) + "],\n")
    f.write("];\n")
    f.write("// Levitation par image : (ecart radial, ecart vertical) en unites du jeu.\n")
    f.write(f"pub static BOB: [[f32; 2]; {len(bob)}] = [\n")
    for r, z in bob:
        f.write(f"    [{r:.3f}, {z:.3f}],\n")
    f.write("];\n")

for i in (0, 30, 60, 90, 120, 150, 179, 240, 300, 359):
    if i < len(rows):
        print("ROW", i, [round(v, 1) for v in rows[i]])
print("BAKED", len(rows), "BOBMAX", max(abs(z) for r, z in bob))
