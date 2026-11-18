"""Calcul des poses BT (numpy) + planche PNG de bonshommes bâtons."""
import numpy as np, struct, zlib, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from bt_lib import *

ORDER = os.environ.get('BT_ORDER', 'YXZ')
ROTK = 360.0 / float(os.environ.get('BT_ROTDIV', '32768'))

def rot(axis, deg):
    a = np.radians(deg); c, s = np.cos(a), np.sin(a)
    if axis == 'X': return np.array([[1,0,0],[0,c,-s],[0,s,c]])
    if axis == 'Y': return np.array([[c,0,s],[0,1,0],[-s,0,c]])
    return np.array([[c,-s,0],[s,c,0],[0,0,1]])

def sample(keys, f):
    if not keys: return None
    if f <= keys[0][1]: return keys[0][2]
    for (i0, f0, v0), (i1, f1, v1) in zip(keys, keys[1:]):
        if f0 <= f <= f1:
            if f1 == f0: return v1
            t = (f - f0) / (f1 - f0)
            return v0 + (v1 - v0) * t
    return keys[-1][2]

def channels(anim):
    s, e, els = anim
    ch = {}
    for b, t, k in els:
        ch.setdefault(b, {})[t] = k
    return ch

def local(ch, bid, f):
    c = ch.get(bid, {})
    r = [0.0, 0.0, 0.0]; sc = [1.0, 1.0, 1.0]; tr = [0.0, 0.0, 0.0]
    for t, k in c.items():
        v = sample(k, f)
        if t < 3: r[t] = v * ROTK
        elif t < 6: sc[t-3] = v / 1024.0
        elif t < 9: tr[t-6] = v / 4.0
    R = np.eye(3)
    for ax in ORDER:
        R = R @ rot(ax, r['XYZ'.index(ax)])
    return R, np.array(sc), np.array(tr)

def pose(bones, ch, f):
    """-> liste de matrices 4x4 monde par os (index fichier)."""
    W = []
    for bid, par, p in bones:
        R, S, T = local(ch, bid, f)
        p = np.array(p)
        M = np.eye(4); M[:3,:3] = R @ np.diag(S); M[:3,3] = p + T - (R @ np.diag(S)) @ p
        W.append(M if par < 0 else W[par] @ M)
    return W

def joints(bones, W):
    return np.array([(W[i] @ np.array([*p, 1.0]))[:3] for i, (b, par, p) in enumerate(bones)])

# ---------- PNG minimal ----------
def png(path, img):
    h, w, _ = img.shape
    raw = b''.join(b'\x00' + img[y].tobytes() for y in range(h))
    def chunk(t, d): return struct.pack('>I', len(d)) + t + d + struct.pack('>I', zlib.crc32(t + d) & 0xffffffff)
    open(path, 'wb').write(b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', w, h, 8, 2, 0, 0, 0)) + chunk(b'IDAT', zlib.compress(raw)) + chunk(b'IEND', b''))

def line(img, a, b, col):
    n = int(max(abs(b[0]-a[0]), abs(b[1]-a[1]))) + 1
    for t in np.linspace(0, 1, n):
        x = int(a[0] + (b[0]-a[0])*t); y = int(a[1] + (b[1]-a[1])*t)
        for dx in (0, 1):
            if 0 <= y < img.shape[0] and 0 <= x+dx < img.shape[1]: img[y, x+dx] = col

STAFF = {85,86,87,88,89}
def draw(img, ox, oy, bones, J, view, scale):
    for i, (bid, par, p) in enumerate(bones):
        if par < 0: continue
        a, b = J[par], J[i]
        def proj(v):
            x = v[0] if view == 'front' else v[2]
            return (ox + x*scale, oy - v[1]*scale)
        col = (255,200,0) if bid in STAFF else (255,80,80) if bones[i][2][0] < -1 else (80,160,255) if bones[i][2][0] > 1 else (230,230,230)
        line(img, proj(a), proj(b), col)

if __name__ == '__main__':
    model = int(sys.argv[1], 16); ids = [int(x, 16) for x in sys.argv[2].split(',')]; out = sys.argv[3]
    bones = bones_of(rd(model))
    N = 8; cw, chh = 110, 130; scale = float(os.environ.get('BT_SCALE', '0.3'))
    img = np.full((chh*len(ids)*2, cw*N + 40, 3), 30, np.uint8)
    for r, aid in enumerate(ids):
        an = parse_anim(rd(aid)); ch = channels(an); s, e = an[0], an[1]
        for v, view in enumerate(('front', 'side')):
            row = r*2 + v
            img[row*chh, :] = (90, 90, 90)
            for k in range(N):
                f = s + (e - s) * k / N
                J = joints(bones, pose(bones, ch, f))
                draw(img, 40 + k*cw + cw//2, row*chh + chh - 10, bones, J, view, scale)
            # étiquette : id en barres (on l'imprime dans la console)
    png(out, img)
    print('ok', out)
