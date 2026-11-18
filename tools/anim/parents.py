"""Affiche la chaîne de parents de quelques os (blender -b --python parents.py -- skel os...)."""
import sys
argv = sys.argv[sys.argv.index('--') + 1:]
sys.path.insert(0, r"C:\Users\sofia\AppData\Roaming\Blender Foundation\Blender\5.1\scripts\addons\smash-ultimate-blender\dependencies\ssbh_data_py\win")
import ssbh_data_py
sk = ssbh_data_py.skel_data.read_skel(argv[0])
by = {b.name: b for b in sk.bones}
for n in argv[1:]:
    chain = []; b = by.get(n)
    while b is not None:
        chain.append(b.name)
        b = sk.bones[b.parent_index] if b.parent_index is not None else None
    print('CHAIN', ' <- '.join(chain))
