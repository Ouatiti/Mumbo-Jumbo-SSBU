"""Liste les os d'un ou plusieurs model.nusktb (lancé via blender -b --python bones.py -- f1 f2 ...)."""
import sys
argv = sys.argv[sys.argv.index('--') + 1:]
sys.path.insert(0, r"C:\Users\sofia\AppData\Roaming\Blender Foundation\Blender\5.1\scripts\addons\smash-ultimate-blender\dependencies\ssbh_data_py\win")
import ssbh_data_py
for p in argv:
    sk = ssbh_data_py.skel_data.read_skel(p)
    names = [b.name for b in sk.bones]
    print('SKEL', p, len(names))
    print('BONES', ' '.join(names))
