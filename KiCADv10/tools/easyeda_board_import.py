"""Recreate the EasyEDA Pro MainBoard setup in a KiCad 10 board (run with KiCad's bundled Python).

  KPY=/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/3.9/bin/python3
  $KPY tools/easyeda_board_import.py <MainBoard.epcb> <PickAndPlace.csv> <NeatAmp.kicad_pcb>

Does: 4 copper layers, rounded-rect outline, 4x M3 plated holes, footprint placement + rotation
and reference-text positions from the EasyEDA board, inner-layer zones (In1/In2), version text.
Placement is verified against the pick-and-place "Pad X/Y" (pad-1 position) column.
The JLC04162H stackup and net classes are written afterwards by easyeda_board_post.py.
"""
import sys, json, csv, io, math, collections
import pcbnew

EPCB, PNP, PCB = sys.argv[1:4]
MIL = 0.0254
rows = []
for l in open(EPCB, encoding='utf-8'):
    try:
        rows.append(json.loads(l))
    except Exception:
        pass
R = lambda t: [r for r in rows if isinstance(r, list) and r and r[0] == t]

outline = [p for p in R('POLY') if p[4] == 11][0][6]          # ['R', x, y, w, h, rot, radius]
_, X0, Y0, W, H, _, RAD = outline
OX, OY = 50.0, 50.0                                           # board top-left in KiCad (mm)
def kx(x): return OX + (x - X0) * MIL
def ky(y): return OY + (Y0 - y) * MIL                         # EasyEDA Y is up
def V(x, y): return pcbnew.VECTOR2I(pcbnew.FromMM(x), pcbnew.FromMM(y))

b = pcbnew.LoadBoard(PCB)


def add_logo(flip_y):
    """EasyEDA IMAGE (vector logo on top solder mask) -> filled F.Mask polygons, even-odd holes."""
    for d in list(b.GetDrawings()):
        if d.GetLayer() == pcbnew.F_Mask and isinstance(d, pcbnew.PCB_SHAPE) and d.GetShape() == pcbnew.SHAPE_T_POLY:
            b.Remove(d)
    for img in R('IMAGE'):
        _, _, _, layer, x, y, w, h, rot, mirror, paths = img[:11]
        xs = [v for p in paths for v in [n for n in p if not isinstance(n, str)][0::2]]
        ys = [v for p in paths for v in [n for n in p if not isinstance(n, str)][1::2]]
        sx, sy = w / (max(xs) - min(xs)), h / (max(ys) - min(ys))
        cx, cy = (max(xs) + min(xs)) / 2, (max(ys) + min(ys)) / 2
        acc = pcbnew.SHAPE_POLY_SET()
        for p in paths:
            n = [v for v in p if not isinstance(v, str)]
            one = pcbnew.SHAPE_POLY_SET(); one.NewOutline()
            for px, py in zip(n[0::2], n[1::2]):
                ex = x + w / 2 + (px - cx) * sx                         # image (x, y) = top-left corner
                ey = y - h / 2 + (py - cy) * sy * (-1 if flip_y else 1)
                one.Append(pcbnew.FromMM(kx(ex)), pcbnew.FromMM(ky(ey)))
            acc.BooleanXor(one)
        # the traced image carries a hairline frame on its bounding box: trim 0.2 mm all round
        bb = acc.BBox(); m = pcbnew.FromMM(0.2)
        clip = pcbnew.SHAPE_POLY_SET(); clip.NewOutline()
        for cxy in ((bb.GetLeft() + m, bb.GetTop() + m), (bb.GetRight() - m, bb.GetTop() + m),
                    (bb.GetRight() - m, bb.GetBottom() - m), (bb.GetLeft() + m, bb.GetBottom() - m)):
            clip.Append(int(cxy[0]), int(cxy[1]))
        acc.BooleanIntersection(clip)
        acc.Fracture()
        for i in range(acc.OutlineCount()):
            s = pcbnew.PCB_SHAPE(b); s.SetShape(pcbnew.SHAPE_T_POLY); s.SetLayer(pcbnew.F_Mask)
            s.SetFilled(True); s.SetWidth(0)
            ps = pcbnew.SHAPE_POLY_SET(); ps.AddOutline(acc.Outline(i)); s.SetPolyShape(ps)
            b.Add(s)
        print('logo:', len(paths), 'paths ->', acc.OutlineCount(), 'F.Mask polygons')


if '--logo-only' in sys.argv:
    add_logo('--flip' in sys.argv)
    b.Save(PCB)
    raise SystemExit
b.SetCopperLayerCount(4)

# --- clear previous outline / holes / zones / texts made by this script (idempotent)
for d in list(b.GetDrawings()):
    if d.GetLayer() == pcbnew.Edge_Cuts or (isinstance(d, pcbnew.PCB_TEXT) and 'Class D amp' in d.GetText()):
        b.Remove(d)
for z in list(b.Zones()):
    b.Remove(z)
for fp in list(b.GetFootprints()):
    if fp.GetReference().startswith('MH'):
        b.Remove(fp)

# --- outline: rounded rectangle
x1, y1, x2, y2, r = kx(X0), ky(Y0), kx(X0 + W), ky(Y0 - H), RAD * MIL
def seg(a, c):
    s = pcbnew.PCB_SHAPE(b); s.SetShape(pcbnew.SHAPE_T_SEGMENT); s.SetLayer(pcbnew.Edge_Cuts)
    s.SetWidth(pcbnew.FromMM(0.1)); s.SetStart(V(*a)); s.SetEnd(V(*c)); b.Add(s)
def arc(a, m, c):
    s = pcbnew.PCB_SHAPE(b); s.SetShape(pcbnew.SHAPE_T_ARC); s.SetLayer(pcbnew.Edge_Cuts)
    s.SetWidth(pcbnew.FromMM(0.1)); s.SetArcGeometry(V(*a), V(*m), V(*c)); b.Add(s)
k = r * (1 - math.sqrt(0.5))
seg((x1 + r, y1), (x2 - r, y1)); seg((x2, y1 + r), (x2, y2 - r))
seg((x2 - r, y2), (x1 + r, y2)); seg((x1, y2 - r), (x1, y1 + r))
arc((x2 - r, y1), (x2 - k, y1 + k), (x2, y1 + r)); arc((x2, y2 - r), (x2 - k, y2 - k), (x2 - r, y2))
arc((x1 + r, y2), (x1 + k, y2 - k), (x1, y2 - r)); arc((x1, y1 + r), (x1 + k, y1 + k), (x1 + r, y1))

# --- mounting holes (board-only footprints MH1..MH4)
lib = PCB.rsplit('/', 1)[0] + '/libs/NeatAmp_custom.pretty' if '/' in PCB else 'libs/NeatAmp_custom.pretty'
holes = sorted(R('PAD'), key=lambda p: (-p[7], p[6]))
for i, p in enumerate(holes, 1):
    fp = pcbnew.FootprintLoad(lib, 'MountingHole_3.2mm_M3_Pad_7mm')
    fp.SetReference('MH%d' % i); fp.SetPosition(V(kx(p[6]), ky(p[7])))
    fp.SetFPIDAsString('NeatAmp_custom:MountingHole_3.2mm_M3_Pad_7mm')
    b.Add(fp)

# --- placement
attrs = collections.defaultdict(dict)
for a in R('ATTR'):
    attrs[a[3]][a[7]] = a
pnp = {}
txt = open(PNP, 'rb').read().decode('utf-16')
for row in csv.DictReader(io.StringIO(txt), delimiter='\t'):
    pnp[row['Designator']] = row
mm = lambda s: float(s.replace('mm', ''))
placed, missing, bad = 0, [], []
for c in R('COMPONENT'):
    a = attrs[c[1]].get('Designator')
    if not a:
        continue
    ref = a[8]
    fp = b.FindFootprintByReference(ref)
    if fp is None:
        missing.append(ref); continue
    if c[3] != 1:
        raise SystemExit('bottom-side part not handled: ' + ref)
    fp.SetOrientationDegrees(c[6] % 360)
    fp.SetPosition(V(kx(c[4]), ky(c[5])))
    if a[5] is not None:                                      # reference text as in EasyEDA
        t = fp.Reference()
        t.SetPosition(V(kx(a[5]), ky(a[6])))
        ang = a[17] % 180
        t.SetTextAngleDegrees(ang)
        t.SetTextSize(V(1.0, 1.0)); t.SetTextThickness(pcbnew.FromMM(0.15))
        t.SetHorizJustify(pcbnew.GR_TEXT_H_ALIGN_CENTER); t.SetVertJustify(pcbnew.GR_TEXT_V_ALIGN_CENTER)
    placed += 1
    # verify: pad 1 vs pick-and-place pad position
    if ref in pnp:
        p1 = [p for p in fp.Pads() if p.GetNumber() in ('1', 'A1B12')]
        if p1:
            px, py = pcbnew.ToMM(p1[0].GetPosition().x), pcbnew.ToMM(p1[0].GetPosition().y)
            ex, ey = kx(mm(pnp[ref]['Pad X']) / MIL), ky(mm(pnp[ref]['Pad Y']) / MIL)
            d = math.hypot(px - ex, py - ey)
            if d > 0.05:
                bad.append((ref, fp.GetFPIDAsString().split(':')[1], round(d, 3), round(px - ex, 3), round(py - ey, 3)))
print('placed', placed, 'missing in KiCad', missing)
print('pad-1 mismatches (>0.05 mm):', len(bad))
for x in sorted(bad, key=lambda x: -x[2]):
    print('  ', x)

# --- inner-layer zones (copied from EasyEDA pours on Inner1/Inner2)
LAY = {15: pcbnew.In1_Cu, 16: pcbnew.In2_Cu}
def pts(path):
    if path[0] == 'R':
        _, x, y, w, h = path[:5]
        return [(x, y), (x + w, y), (x + w, y - h), (x, y - h)]
    out, i = [], 0
    nums = [v for v in path if not isinstance(v, str)]
    if any(isinstance(v, str) and v != 'L' for v in path):
        raise SystemExit('unsupported pour path token in %r' % path[:20])
    return list(zip(nums[0::2], nums[1::2]))
zs = []
for p in R('POUR'):
    if p[4] not in LAY:
        continue
    poly = pts(p[8][0])
    area = abs(sum(poly[i][0] * poly[i - 1][1] - poly[i - 1][0] * poly[i][1] for i in range(len(poly)))) / 2
    zs.append((area, p, poly))
zs.sort(key=lambda z: -z[0])                                  # bigger zone = lower priority
for prio, (area, p, poly) in enumerate(zs):
    net = b.FindNet(p[3])
    z = pcbnew.ZONE(b); z.SetLayer(LAY[p[4]]); z.SetNetCode(net.GetNetCode())
    z.SetAssignedPriority(prio); z.SetLocalClearance(pcbnew.FromMM(0.254))
    z.SetMinThickness(pcbnew.FromMM(0.254)); z.SetThermalReliefGap(pcbnew.FromMM(0.254))
    z.SetThermalReliefSpokeWidth(pcbnew.FromMM(0.254)); z.SetZoneName(p[3])
    o = z.Outline(); o.NewOutline()
    for x, y in poly:
        o.Append(pcbnew.FromMM(kx(x)), pcbnew.FromMM(ky(y)))
    b.Add(z)
print('zones', [(z.GetZoneName(), b.GetLayerName(z.GetLayer())) for z in b.Zones()])

# --- version text on top silk
for s in R('STRING'):
    t = pcbnew.PCB_TEXT(b); t.SetText(s[6].replace(' \n', '\n').strip()); t.SetLayer(pcbnew.F_SilkS)
    t.SetPosition(V(kx(s[4]), ky(s[5]))); t.SetTextSize(V(2.0, 2.0)); t.SetTextThickness(pcbnew.FromMM(0.25))
    t.SetHorizJustify(pcbnew.GR_TEXT_H_ALIGN_LEFT); t.SetVertJustify(pcbnew.GR_TEXT_V_ALIGN_BOTTOM)
    b.Add(t)

# --- library fix carried into the board: USB-C locating pegs are non-plated
usb = b.FindFootprintByReference('USBC1')
for pad in usb.Pads():
    if pad.GetNumber() == '' and pad.GetAttribute() == pcbnew.PAD_ATTRIB_PTH:
        pad.SetAttribute(pcbnew.PAD_ATTRIB_NPTH)

pcbnew.ZONE_FILLER(b).Fill(b.Zones())
b.Save(PCB)
print('saved', PCB)
