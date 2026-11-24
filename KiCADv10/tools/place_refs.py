"""Auto-place footprint reference designators on F.Silkscreen.

Readable orientation for a board viewed with the speaker outputs on the right
(= normal KiCad view here): text angle 0 (left-to-right) or 90 (bottom-to-top).

Usage (KiCad bundled Python, KiCad closed):
  /Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/3.9/bin/python3 tools/place_refs.py NeatAmp.kicad_pcb out.kicad_pcb
References with no free spot keep their position and are reported as UNPLACED.
"""
import sys, math
import pcbnew

MM = pcbnew.FromMM
TO = pcbnew.ToMM

PAD_CLR = 0.20      # text to exposed copper
SILK_CLR = 0.15     # text to other silk
REF_CLR = 0.20      # text to text
EDGE_CLR = 0.60     # text to board edge
GAPS = (0.10, 0.35, 0.7, 1.1)  # distance from own courtyard
CELL = 2.0

src, dst = sys.argv[1], sys.argv[2]
board = pcbnew.LoadBoard(src)

ebb = board.GetBoardEdgesBoundingBox()
BX0, BY0 = TO(ebb.GetX()) + EDGE_CLR, TO(ebb.GetY()) + EDGE_CLR
BX1, BY1 = TO(ebb.GetRight()) - EDGE_CLR, TO(ebb.GetBottom()) - EDGE_CLR
CORNER_R = 4.6  # board corner arcs (~4.58 mm radius)


def inside_board(r):
    x0, y0, x1, y1 = r
    if x0 < BX0 or y0 < BY0 or x1 > BX1 or y1 > BY1:
        return False
    # rounded corners: keep out of the corner squares' outer part
    for cx, cy in ((BX0 - EDGE_CLR + CORNER_R, BY0 - EDGE_CLR + CORNER_R),
                   (BX1 + EDGE_CLR - CORNER_R, BY0 - EDGE_CLR + CORNER_R),
                   (BX0 - EDGE_CLR + CORNER_R, BY1 + EDGE_CLR - CORNER_R),
                   (BX1 + EDGE_CLR - CORNER_R, BY1 + EDGE_CLR - CORNER_R)):
        for px, py in ((x0, y0), (x1, y0), (x0, y1), (x1, y1)):
            if ((px < cx and cx < BX0 + CORNER_R) or (px > cx and cx > BX1 - CORNER_R)) and \
               ((py < cy and cy < BY0 + CORNER_R) or (py > cy and cy > BY1 - CORNER_R)):
                if math.hypot(px - cx, py - cy) > CORNER_R - EDGE_CLR:
                    return False
    return True


def bbox_mm(b):
    return (TO(b.GetX()), TO(b.GetY()), TO(b.GetRight()), TO(b.GetBottom()))


def inflate(r, d):
    return (r[0] - d, r[1] - d, r[2] + d, r[3] + d)


def rect_overlap(a, b):
    return a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]


def seg_hits_rect(p, q, r):
    # Liang-Barsky
    x0, y0 = p
    dx, dy = q[0] - p[0], q[1] - p[1]
    t0, t1 = 0.0, 1.0
    for pp, qq in ((-dx, x0 - r[0]), (dx, r[2] - x0), (-dy, y0 - r[1]), (dy, r[3] - y0)):
        if pp == 0:
            if qq < 0:
                return False
        else:
            t = qq / pp
            if pp < 0:
                if t > t1:
                    return False
                t0 = max(t0, t)
            else:
                if t < t0:
                    return False
                t1 = min(t1, t)
    return True


def point_in_poly(x, y, pts):
    c = False
    n = len(pts)
    for i in range(n):
        x1, y1 = pts[i]
        x2, y2 = pts[(i + 1) % n]
        if (y1 > y) != (y2 > y) and x < (x2 - x1) * (y - y1) / (y2 - y1) + x1:
            c = not c
    return c


class Obstacles:
    """Rect obstacles and polygon (silk stroke) obstacles in a bucket grid."""

    def __init__(self):
        self.items = []      # (kind, owner, data, bbox)
        self.grid = {}

    def _cells(self, r):
        for i in range(int(r[0] // CELL), int(r[2] // CELL) + 1):
            for j in range(int(r[1] // CELL), int(r[3] // CELL) + 1):
                yield (i, j)

    def add(self, kind, owner, data, bbox):
        idx = len(self.items)
        self.items.append((kind, owner, data, bbox))
        for c in self._cells(bbox):
            self.grid.setdefault(c, []).append(idx)
        return idx

    def hits(self, r, skip_kinds=(), skip_owner_kinds=(), owner=None):
        seen = set()
        for c in self._cells(r):
            for idx in self.grid.get(c, ()):
                if idx in seen:
                    continue
                seen.add(idx)
                kind, own, data, bb = self.items[idx]
                if kind in skip_kinds:
                    continue
                if own == owner and kind in skip_owner_kinds:
                    continue
                if kind == 'crtbig' and owner is not None and own != owner:
                    ox, oy = CENTER[owner]
                    if bb[0] < ox < bb[2] and bb[1] < oy < bb[3]:
                        continue
                clr = {'pad': PAD_CLR, 'silk': SILK_CLR, 'text': REF_CLR, 'crt': 0.0, 'crtbig': 0.0}[kind]
                rr = inflate(r, clr)
                if not rect_overlap(rr, bb):
                    continue
                if data is None:
                    return (kind, own)
                # polygon list (outlines incl. holes)
                for pts, filled in data:
                    n = len(pts)
                    for k in range(n):
                        if seg_hits_rect(pts[k], pts[(k + 1) % n], rr):
                            return (kind, own)
                    if filled and point_in_poly((rr[0] + rr[2]) / 2, (rr[1] + rr[3]) / 2, pts):
                        return (kind, own)
        return None


def shape_polys(item, layer):
    ps = pcbnew.SHAPE_POLY_SET()
    item.TransformShapeToPolygon(ps, layer, 0, MM(0.02), pcbnew.ERROR_INSIDE)
    out = []
    for i in range(ps.OutlineCount()):
        ol = ps.Outline(i)
        out.append(([(TO(ol.CPoint(k).x), TO(ol.CPoint(k).y)) for k in range(ol.PointCount())], True))
        for h in range(ps.HoleCount(i)):
            hl = ps.Hole(i, h)
            out.append(([(TO(hl.CPoint(k).x), TO(hl.CPoint(k).y)) for k in range(hl.PointCount())], False))
    return out


obs = Obstacles()
CENTER = {}
fps = list(board.GetFootprints())
info = {}

for fi, f in enumerate(fps):
    f = fi
    F = fps[fi]
    crt = F.GetCourtyard(pcbnew.F_CrtYd)
    if crt.OutlineCount():
        cb = bbox_mm(crt.BBox())
    else:
        cb = bbox_mm(F.GetBoundingBox(False))
    obs.add('crtbig' if (cb[2] - cb[0]) * (cb[3] - cb[1]) > 12.0 else 'crt', f, None, cb)
    ext_items = [cb]
    for p in F.Pads():
        ext_items.append(bbox_mm(p.GetBoundingBox()))
    for g in F.GraphicalItems():
        if g.GetLayer() == pcbnew.F_SilkS and g.GetClass() not in ('PCB_TEXT', 'PCB_FIELD'):
            ext_items.append(bbox_mm(g.GetBoundingBox()))
    CENTER[f] = (TO(F.GetPosition().x), TO(F.GetPosition().y))
    info[f] = (min(e[0] for e in ext_items), min(e[1] for e in ext_items),
               max(e[2] for e in ext_items), max(e[3] for e in ext_items))
    for p in F.Pads():
        if p.IsOnLayer(pcbnew.F_Cu) or p.IsOnLayer(pcbnew.F_Mask) or p.GetAttribute() == pcbnew.PAD_ATTRIB_NPTH:
            obs.add('pad', f, None, bbox_mm(p.GetBoundingBox()))
    for g in F.GraphicalItems():
        if g.GetLayer() != pcbnew.F_SilkS:
            continue
        if isinstance(g, pcbnew.PCB_TEXT) or g.GetClass() in ('PCB_TEXT', 'PCB_FIELD'):
            if g.IsVisible():
                obs.add('text', f, None, bbox_mm(g.GetBoundingBox()))
            continue
        polys = shape_polys(g, pcbnew.F_SilkS)
        if polys:
            obs.add('silk', f, polys, bbox_mm(g.GetBoundingBox()))
    # other visible silk fields (not reference)
    for fld in F.GetFields():
        if fld.IsReference() or not fld.IsVisible() or fld.GetLayer() != pcbnew.F_SilkS:
            continue
        obs.add('text', f, None, bbox_mm(fld.GetBoundingBox()))

for d in board.GetDrawings():
    if d.GetLayer() == pcbnew.F_SilkS:
        if d.GetClass() == 'PCB_TEXT':
            obs.add('text', None, None, bbox_mm(d.GetBoundingBox()))
        else:
            obs.add('silk', None, shape_polys(d, pcbnew.F_SilkS), bbox_mm(d.GetBoundingBox()))
for t in board.GetTracks():
    if t.GetClass() == 'PCB_VIA':
        pass  # vias are tented: not exposed copper

refs = [i for i, f in enumerate(fps) if f.Reference().IsVisible() and f.Reference().GetLayer() == pcbnew.F_SilkS]

# text extents at angle 0
ext = {}
orig = {}
for f in refs:
    r = fps[f].Reference()
    orig[f] = (r.GetTextAngleDegrees(), r.GetHorizJustify(), r.GetVertJustify(), r.GetPosition())
    r.SetHorizJustify(pcbnew.GR_TEXT_H_ALIGN_CENTER)
    r.SetVertJustify(pcbnew.GR_TEXT_V_ALIGN_CENTER)
    r.SetTextAngleDegrees(0)
    b = bbox_mm(r.GetBoundingBox())
    ext[f] = (b[2] - b[0], TO(r.GetTextHeight() + r.GetTextThickness()) + 0.05)


def candidates(f, gaps=GAPS, base=0.0):
    x0, y0, x1, y1 = info[f]
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    w, h = x1 - x0, y1 - y0
    tw0, th0 = ext[f]
    vertical = h > w * 1.25
    out = []
    for gi, g in enumerate(gaps):
        for ang in (0, 90):
            tw, th = (tw0, th0) if ang == 0 else (th0, tw0)
            sides = []
            # top / bottom: slide along x
            for side, yc in (('top', y0 - g - th / 2), ('bottom', y1 + g + th / 2)):
                span = max(w / 2 + tw / 2 + (0.8 if g > 1 else 0.2), 0)
                sides.append((side, [(cx + s, yc) for s in slides(span)]))
            for side, xc in (('left', x0 - g - tw / 2), ('right', x1 + g + tw / 2)):
                span = max(h / 2 + th / 2 + (0.8 if g > 1 else 0.2), 0)
                sides.append((side, [(xc, cy + s) for s in slides(span)]))
            for side, pts in sides:
                for (px, py) in pts:
                    off = math.hypot(px - cx, py - cy)
                    slide = abs(px - cx) if side in ('top', 'bottom') else abs(py - cy)
                    score = base + g * 3 + slide * 0.6
                    if side in ('top', 'bottom'):
                        score += 0.0 if ang == 0 else 1.5
                    else:
                        if vertical:
                            score += 0.0 if ang == 90 else 0.8
                        else:
                            score += 0.6 if ang == 0 else 1.2
                    if side == 'top':
                        score -= 0.05
                    r = (px - tw / 2, py - th / 2, px + tw / 2, py + th / 2)
                    out.append((score, ang, (px, py), r))
    # last resort: inside own body (big parts)
    for ang in (0, 90):
        tw, th = (tw0, th0) if ang == 0 else (th0, tw0)
        if tw < w - 0.4 and th < h - 0.4:
            for dx, dy in ((0, 0), (0, -h / 4), (0, h / 4), (-w / 4, 0), (w / 4, 0)):
                px, py = cx + dx, cy + dy
                r = (px - tw / 2, py - th / 2, px + tw / 2, py + th / 2)
                out.append((50 + abs(dx) + abs(dy) + (0 if ang == 0 else 0.5) + (0 if not vertical or ang == 90 else 0.5), ang, (px, py), r))
    out.sort(key=lambda c: c[0])
    return out


def slides(span):
    s = [0.0]
    step = 0.4
    k = step
    while k <= span + 1e-6:
        s += [-k, k]
        k += step
    return s


def ok(f, r, tier):
    if not inside_board(r):
        return False
    skip = ()
    if tier >= 2:
        skip = ('crt',)
    own_skip = ('crt', 'crtbig') if tier >= 3 else ()
    hit = obs.hits(r, skip_kinds=skip, skip_owner_kinds=own_skip, owner=f)
    return hit is None


# constrainedness ordering
cands = {f: candidates(f) for f in refs}


def nfree(f):
    return sum(1 for c in cands[f] if c[0] < 50 and ok(f, c[3], 1))


order = sorted(refs, key=lambda f: (nfree(f), -(info[f][2] - info[f][0]) * (info[f][3] - info[f][1])))

result = {}


def commit(f, tier, c):
    score, ang, (px, py), r = c
    ref = fps[f].Reference()
    ref.SetTextAngleDegrees(ang)
    ref.SetPosition(pcbnew.VECTOR2I(MM(px), MM(py)))
    obs.add('text', f, None, r)
    result[f] = (tier, ang)


later = []
for f in order:
    placed = None
    for tier in (1, 2, 3):
        for c in cands[f]:
            if (tier < 3) != (c[0] < 50):
                continue
            if ok(f, c[3], tier):
                placed = (tier, c)
                break
        if placed:
            break
    if placed:
        commit(f, *placed)
    else:
        later.append(f)

FAR = (1.5, 1.9, 2.4, 3.0, 3.6)
later.sort(key=lambda f: sum(1 for c in candidates(f, FAR, 20.0) if c[0] < 50 and ok(f, c[3], 2)))
for f in later:
    for c in candidates(f, FAR, 20.0):
        if c[0] < 50 and ok(f, c[3], 2):
            commit(f, 4, c)
            break
    else:
        result[f] = None
for f in later:
    if result[f] is None:
        r = fps[f].Reference()
        a, hj, vj, pos = orig[f]
        r.SetTextAngleDegrees(a); r.SetHorizJustify(hj); r.SetVertJustify(vj); r.SetPosition(pos)
        obs.add('text', f, None, bbox_mm(fps[f].Reference().GetBoundingBox()))

import collections
cnt = collections.Counter(v[0] if v else 'none' for v in result.values())
print('placed by tier:', dict(cnt))
for f, v in sorted(result.items(), key=lambda kv: fps[kv[0]].GetReference()):
    if v is None or v[0] > 1:
        print(' ', fps[f].GetReference(), 'tier', v[0] if v else 'UNPLACED')
pcbnew.SaveBoard(dst, board)
