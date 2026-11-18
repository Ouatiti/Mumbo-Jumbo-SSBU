"""Lecture des modèles / animations Banjo-Tooie extraits (format BK)."""
import struct, os
A = r"E:\Emulateurs\bt_extract\assets"

def rd(i):
    return open(f"{A}\\{i:04x}.bin", 'rb').read()

def bones_of(d):
    """Liste des os : [(id, parent_index, (x,y,z))] dans l'ordre du fichier."""
    bo, = struct.unpack('>I', d[0x18:0x1c])
    n, = struct.unpack('>H', d[bo+4:bo+6]); p = bo + 8; out = []
    for k in range(n):
        x, y, z, bid, par = struct.unpack('>fffhh', d[p:p+16]); out.append((bid, par, (x, y, z))); p += 16
    return out

def parse_anim(d):
    """-> (start, end, [(bone_id, ttype, [(interp, frame, value)])]) ou None."""
    if len(d) < 8: return None
    s, e, n, pad = struct.unpack('>hhhh', d[:8])
    if not (0 <= s <= e < 4000 and 0 < n < 600 and pad == 0):
        return None
    p = 8; els = []
    for _ in range(n):
        if p + 4 > len(d): return None
        h, c = struct.unpack('>Hh', d[p:p+4]); p += 4
        if c < 0 or p + 4 * c > len(d): return None
        keys = []
        for k in range(c):
            kf, v = struct.unpack('>Hh', d[p+4*k:p+4*k+4]); keys.append((kf >> 14, kf & 0x3FFF, v))
        p += 4 * c
        els.append((h >> 4, h & 0xF, keys))
    if p != len(d) and len(d) - p > 16: return None
    return s, e, els

def all_anims():
    out = {}
    for i in range(1, 0x600):
        fn = f"{A}\\{i:04x}.bin"
        if os.path.exists(fn):
            r = parse_anim(open(fn, 'rb').read())
            if r: out[i] = r
    return out
