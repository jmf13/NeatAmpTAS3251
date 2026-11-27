#!/usr/bin/env python3
"""EasyEDA Pro .enet netlist -> KiCad hierarchical schematic, v2.
- auto nets named after the IC pin they touch (U6_EN, ...)
- power nets drawn with power symbols
- passives that connect to exactly one IC pin (2-node net) are placed next to that pin and wired
Verified by tools/cmp.py against the source netlist."""
import json, re, sys, uuid, collections, os, csv, math

SRC = sys.argv[1]; OUT = sys.argv[2]; PROJ = sys.argv[3] if len(sys.argv) > 3 else "NeatAmp"
PAGES = {"1": "Power 12V DC", "2": "Power 5V DC", "3": "Power 3.3V DC", "4": "Microcontroler", "5": "Amplifier"}
POWER = ["GND", "AGND", "3.3V", "+5V", "PVDD", "+3.3VA", "12V_GVDD", "+13.2V", "PVDDLMQ", "VBUS1"]
GROUNDS = {"GND", "AGND"}
G = 1.27
def snap(v): return round(v / G) * G
def U(): return str(uuid.uuid4())
def q(s): return '"' + str(s).replace('\\', '\\\\').replace('"', '\\"') + '"'
def natkey(s): return [int(t) if t.isdigit() else t.lower() for t in re.split(r'(\d+)', str(s))]
def tw(s): return len(s) * 1.05 + 1.5
def F(v): return f"{v:.4f}".rstrip('0').rstrip('.')
def san(s): return re.sub(r'[^A-Za-z0-9_+.-]', '_', s)

d = json.load(open(SRC, encoding='utf-8'))
comps = []
for v in d["components"].values():
    p = v["props"]
    pins = sorted(((k, x["name"] or k, x["net"]) for k, x in v["pinInfoMap"].items()), key=lambda t: natkey(t[0]))
    comps.append(dict(ref=p["Designator"], props=p, pins=pins, page=re.match(r'\$(\d+)', p["Channel ID"]).group(1)))
byref = {c["ref"]: c for c in comps}
nets = collections.defaultdict(list)
for c in comps:
    for num, nm, n in c["pins"]:
        if n: nets[n].append((c["ref"], num, nm))

# ---------- net naming ----------
netname = {}
used = set(n for n in nets if not n.startswith('$'))
for n in sorted(nets, key=natkey):
    if not n.startswith('$'): netname[n] = n; continue
    nodes = sorted(nets[n], key=lambda t: (-len(byref[t[0]]["pins"]), natkey(t[0]), natkey(t[1])))
    r, num, nm = nodes[0]
    base = f"{r}_{san(nm)}" if (nm != num and not nm.isdigit() and len(byref[r]["pins"]) > 2) else f"{r}_P{num}"
    name = base; i = 2
    while name in used: name = f"{base}_{i}"; i += 1
    used.add(name); netname[n] = name

# ---------- symbols ----------
symbols = {}
def build_symbol(c):
    n = len(c["pins"]); pre = re.sub(r'\d+$', '', c["ref"])
    if n <= 2:
        k = san(f"{pre}_{n}pin" + ("_" + "_".join(f"{a}{b}" for a, b, _ in c["pins"]) if any(b != a for a, b, _ in c["pins"]) else ""))
        if k not in symbols:
            if n == 1: symbols[k] = dict(kind='one', pins=[(c["pins"][0][0], c["pins"][0][1], 2.54, 0.0, 180, 'R')])
            else:
                (a, an, _), (b, bn, _) = c["pins"]
                symbols[k] = dict(kind='two', pins=[(a, an, -5.08, 0.0, 0, 'L'), (b, bn, 5.08, 0.0, 180, 'R')])
        return k
    k = san(c["props"]["DeviceName"]) + f"_{n}p"
    if k in symbols: return k
    half = math.ceil(n / 2); left, right = c["pins"][:half], c["pins"][half:]
    lw = max([tw(x[1]) for x in left] + [2]); rw = max([tw(x[1]) for x in right] + [2])
    w = snap(max(lw + rw + 1.27, 10.16) / 2) * 2; h = snap(half * 5.08 + 2.54)
    pins = [(num, nm, -w / 2 - 2.54, snap(h / 2 - 3.81 - i * 5.08), 0, 'L') for i, (num, nm, _) in enumerate(left)]
    pins += [(num, nm, w / 2 + 2.54, snap(h / 2 - 3.81 - i * 5.08), 180, 'R') for i, (num, nm, _) in enumerate(right)]
    symbols[k] = dict(kind='ic', pins=pins, w=w, h=h); return k
for c in comps: c["sym"] = build_symbol(c)

def sym_sexpr(name, lp):
    s = symbols[name]; o = [f'(symbol {q(lp+name)} (pin_names (offset 0.508)) (in_bom yes) (on_board yes)']
    for i, (pk, pv) in enumerate([("Reference", "U"), ("Value", name), ("Footprint", ""), ("Datasheet", "")]):
        o.append(f'(property {q(pk)} {q(pv)} (at 0 {F(-i*2.54)} 0) (effects (font (size 1.27 1.27)){" hide" if i > 1 else ""}))')
    if s["kind"] == 'one':
        o.append(f'(symbol {q(name+"_0_1")} (circle (center 0 0) (radius 0.762) (stroke (width 0.254) (type default)) (fill (type none))))'); pl = 1.778
    elif s["kind"] == 'two':
        o.append(f'(symbol {q(name+"_0_1")} (rectangle (start -2.54 1.016) (end 2.54 -1.016) (stroke (width 0.254) (type default)) (fill (type background))))'); pl = 2.54
    else:
        o.append(f'(symbol {q(name+"_0_1")} (rectangle (start {F(-s["w"]/2)} {F(s["h"]/2)}) (end {F(s["w"]/2)} {F(-s["h"]/2)}) (stroke (width 0.254) (type default)) (fill (type background))))'); pl = 2.54
    o.append(f'(symbol {q(name+"_1_1")}')
    hide = ' hide' if s["kind"] != 'ic' else ''
    for num, nm, x, y, ang, _ in s["pins"]:
        o.append(f'(pin passive line (at {F(x)} {F(y)} {ang}) (length {F(pl)}) (name {q(nm)} (effects (font (size 1.0 1.0)){hide})) (number {q(num)} (effects (font (size 1.0 1.0)){hide})))')
    o.append('))'); return "\n".join(o)

def pwr_name(n): return "PWR_" + san(n)
def pwr_sexpr(n, lp):
    nm = pwr_name(n); gnd = n in GROUNDS
    o = [f'(symbol {q(lp+nm)} (power) (pin_names (offset 0)) (in_bom yes) (on_board yes)',
         f'(property "Reference" "#PWR" (at 0 {F(-6.35 if gnd else 6.35)} 0) (effects (font (size 1.27 1.27)) hide))',
         f'(property "Value" {q(n)} (at 0 {F(-3.81 if gnd else 3.556)} 0) (effects (font (size 1.0 1.0))))',
         '(property "Footprint" "" (at 0 0 0) (effects (font (size 1.27 1.27)) hide))', '(property "Datasheet" "" (at 0 0 0) (effects (font (size 1.27 1.27)) hide))']
    if gnd:
        o.append(f'(symbol {q(nm+"_0_1")} (polyline (pts (xy 0 0) (xy 0 -1.27) (xy 1.27 -1.27) (xy 0 -2.54) (xy -1.27 -1.27) (xy 0 -1.27)) (stroke (width 0.254) (type default)) (fill (type none))))')
    else:
        o.append(f'(symbol {q(nm+"_0_1")} (polyline (pts (xy 0 0) (xy 0 1.27)) (stroke (width 0.254) (type default)) (fill (type none))) (polyline (pts (xy -1.27 1.27) (xy 1.27 1.27)) (stroke (width 0.254) (type default)) (fill (type none))))')
    o.append(f'(symbol {q(nm+"_1_1")} (pin power_in line (at 0 0 {270 if gnd else 90}) (length 0) hide (name {q(n)} (effects (font (size 1.27 1.27)))) (number "1" (effects (font (size 1.27 1.27))))))')
    o.append(')'); return "\n".join(o)

# ---------- page drawing ----------
class Sheet:
    def __init__(s, path): s.o = []; s.path = path; s.pwr_used = set()
    pwr_ctr = [0]
    def wire(s, x1, y1, x2, y2):
        if abs(x1 - x2) < 1e-6 and abs(y1 - y2) < 1e-6: return
        s.o.append(f'(wire (pts (xy {F(x1)} {F(y1)}) (xy {F(x2)} {F(y2)})) (stroke (width 0) (type default)) (uuid {U()}))')
    def nc(s, x, y): s.o.append(f'(no_connect (at {F(x)} {F(y)}) (uuid {U()}))')
    def power(s, n, x, y, outward):  # outward: 'L','R'
        s.pwr_used.add(n); Sheet.pwr_ctr[0] += 1; ref = f"#PWR{Sheet.pwr_ctr[0]:04d}"
        gnd = n in GROUNDS
        rot = (270 if outward == 'L' else 90) if gnd else (90 if outward == 'L' else 270)
        s.o.append(f'(symbol (lib_id {q("NeatAmp:"+pwr_name(n))}) (at {F(x)} {F(y)} {rot}) (unit 1) (in_bom yes) (on_board yes) (dnp no) (uuid {U()})'
                   f' (property "Reference" {q(ref)} (at {F(x)} {F(y)} 0) (effects (font (size 1.27 1.27)) hide))'
                   f' (property "Value" {q(n)} (at {F(x + (-1 if outward=="L" else 1)*(3.6 + len(n)*0.5))} {F(y)} {rot}) (effects (font (size 1.0 1.0))))'
                   f' (property "Footprint" "" (at {F(x)} {F(y)} 0) (effects (font (size 1.27 1.27)) hide)) (property "Datasheet" "" (at {F(x)} {F(y)} 0) (effects (font (size 1.27 1.27)) hide))'
                   f' (pin "1" (uuid {U()})) (instances (project {q(PROJ)} (path {q(s.path)} (reference {q(ref)}) (unit 1)))))')
    def label(s, n, x, y, outward):
        if n in POWER: return s.power(n, x, y, outward)
        nm = netname[n]; la, js = (180, 'right') if outward == 'L' else (0, 'left')
        if n.startswith('$'):
            s.o.append(f'(label {q(nm)} (at {F(x)} {F(y)} {la}) (fields_autoplaced) (effects (font (size 1.27 1.27)) (justify {js} bottom)) (uuid {U()}))')
        else:
            s.o.append(f'(global_label {q(nm)} (shape passive) (at {F(x)} {F(y)} {la}) (fields_autoplaced) (effects (font (size 1.27 1.27)) (justify {js})) (uuid {U()}) (property "Intersheetrefs" "${{INTERSHEET_REFS}}" (at {F(x)} {F(y)} 0) (effects (font (size 1.27 1.27)) hide)))')
    def comp(s, c, X, Y, rot=0):
        p = c["props"]; sy = symbols[c["sym"]]
        val = p.get("Value") or p.get("DeviceName", "")
        inbom = "yes" if p.get("Add into BOM", "yes") == "yes" else "no"
        s.o.append(f'(symbol (lib_id {q("NeatAmp:"+c["sym"])}) (at {F(X)} {F(Y)} {rot}) (unit 1) (in_bom {inbom}) (on_board yes) (dnp no) (uuid {U()})')
        if sy["kind"] == 'ic': ro, vo, fs = (0, -sy["h"] / 2 - 1.905), (0, sy["h"] / 2 + 1.905), 1.27
        else: ro, vo, fs = (0, -1.905), (0, 1.905), 1.0
        fields = [("Reference", c["ref"], ro, False), ("Value", val, vo, False), ("Footprint", fp_for(c), (0, 0), True),
                  ("Datasheet", p.get("Datasheet", ""), (0, 0), True), ("LCSC", p.get("Supplier Part", ""), (0, 0), True),
                  ("MPN", p.get("Manufacturer Part", ""), (0, 0), True), ("Manufacturer", p.get("Manufacturer", ""), (0, 0), True),
                  ("JLC Class", p.get("JLCPCB Part Class", ""), (0, 0), True), ("Description", p.get("Description", "").strip(), (0, 0), True),
                  ("EasyEDA Footprint", p.get("FootprintName", ""), (0, 0), True), ("EasyEDA Device", p.get("DeviceName", ""), (0, 0), True)]
        for fk, fv, (dx, dy), hid in fields:
            s.o.append(f'(property {q(fk)} {q(fv)} (at {F(X+dx)} {F(Y+dy)} 0) (effects (font (size {fs} {fs})){" hide" if hid else ""}))')
        for num, *_ in sy["pins"]: s.o.append(f'(pin {q(num)} (uuid {U()}))')
        s.o.append(f'(instances (project {q(PROJ)} (path {q(s.path)} (reference {q(c["ref"])}) (unit 1)))))')
    @staticmethod
    def pin_pos(c, X, Y, rot=0):
        out = {}
        for num, nm, lx, ly, ang, side in symbols[c["sym"]]["pins"]:
            if rot == 180: dx, dy, sd = -lx, ly, ('R' if side == 'L' else 'L')
            else: dx, dy, sd = lx, -ly, side
            out[num] = (snap(X + dx), snap(Y + dy), sd)
        return out

STD_FP = {"TESTPOINT-SMD_1P-BD1.0": "TestPoint:TestPoint_Pad_D1.0mm"}
def fp_for(c):
    p = c["props"]; fpn = p.get("FootprintName", "")
    if fpn in STD_FP: return STD_FP[fpn]
    if p.get("Supplier Part"): return f"easyeda2kicad:{fpn}"
    return f"NeatAmp_custom:{fpn}"

def lab_len(n):
    if not n: return 2
    return 9 if n in POWER else tw(netname[n]) + 2.5

# ---------- grouping & attachments ----------
def plan_page(cs):
    refs = {c["ref"] for c in cs}
    anchors = sorted([c for c in cs if len(c["pins"]) > 2], key=lambda c: natkey(c["ref"]))
    # attachments: 2-node net, one IC pin + one passive pin
    attach = {}  # passive ref -> (ic ref, ic pin, passive pin, net)
    icpin_taken = set()
    for c in sorted([c for c in cs if len(c["pins"]) == 2], key=lambda c: natkey(c["ref"])):
        for num, nm, n in c["pins"]:
            if not n or not n.startswith("$") or len(nets[n]) != 2: continue
            other = [t for t in nets[n] if t[0] != c["ref"]]
            if len(other) != 1: continue
            r, pn, _ = other[0]
            if r in refs and len(byref[r]["pins"]) > 2 and (r, pn) not in icpin_taken:
                attach[c["ref"]] = (r, pn, num, n); icpin_taken.add((r, pn)); break
    # group remaining small parts by BFS over non-power nets
    netmap = collections.defaultdict(set)
    for c in cs:
        for _, _, n in c["pins"]:
            if n and n not in POWER: netmap[n].add(c["ref"])
    owner = {a["ref"]: a["ref"] for a in anchors}
    for pr, (r, *_ ) in attach.items(): owner[pr] = r
    frontier = list(owner)
    while frontier:
        nxt = []
        for r in frontier:
            for _, _, n in byref[r]["pins"]:
                if not n or n in POWER: continue
                for o in sorted(netmap[n], key=natkey):
                    if o not in owner and o in refs: owner[o] = owner[r]; nxt.append(o)
        frontier = nxt
    groups = collections.OrderedDict((a["ref"], [a]) for a in anchors)
    groups["_misc"] = []
    for c in sorted([c for c in cs if len(c["pins"]) <= 2 and c["ref"] not in attach], key=lambda c: natkey(c["ref"])):
        groups[owner.get(c["ref"], "_misc")].append(c)
    if not groups["_misc"]: del groups["_misc"]
    return groups, attach

def draw_page(cs, path):
    sh = Sheet(path)
    groups, attach = plan_page(cs)
    by_ic = collections.defaultdict(list)
    for pr, (r, pn, ppin, n) in attach.items(): by_ic[r].append((pn, pr, ppin, n))
    blocks = []
    for key, mem in groups.items():
        anchor = mem[0] if len(mem[0]["pins"]) > 2 else None
        smalls = mem[1:] if anchor else mem
        info = None
        if anchor:
            sy = symbols[anchor["sym"]]; pins = Sheet.pin_pos(anchor, 0, 0)
            att = {pn: (pr, ppin, n) for pn, pr, ppin, n in by_ic[anchor["ref"]]}
            # choose columns per side (alternate when consecutive rows)
            cols = {}; ext = {'L': 4.0, 'R': 4.0}
            for side in 'LR':
                rows = sorted([(pins[pn][1], pn) for pn in att if pins[pn][2] == side])
                last = []; colof = {}
                for y, pn in rows:
                    k = next((i for i, ly in enumerate(last) if y - ly >= 5.08 - 1e-6), None)
                    if k is None: last.append(y); k = len(last) - 1
                    else: last[k] = y
                    colof[pn] = k
                ncol = len(last)
                far = [max([lab_len(other_net(att[pn])) for pn in colof if colof[pn] == k] + [6]) for k in range(ncol)]
                offs = []; o_ = 2.54
                for k in range(ncol): offs.append(snap(o_)); o_ += 10.16 + far[k] + 2.54
                for pn, k in colof.items(): cols[pn] = (k, offs[k])
                e = 4.0
                for num, nm, n in anchor["pins"]:
                    if pins[num][2] != side: continue
                    if num in att:
                        k, wl = cols[num]; e = max(e, wl + 10.16 + lab_len(other_net(att[num])))
                    else: e = max(e, lab_len(n) + 2.54)
                ext[side] = e
            info = (sy, att, cols, ext)
            aw = ext['L'] + sy["w"] + 5.08 + ext['R']; ah = sy["h"]
        else: aw = ah = 0
        maxl = max([lab_len(n) for c in smalls for _, _, n in c["pins"]] + [6])
        colw = snap(2 * maxl + 10.16 + 2.54); rpc = 12
        ncols = math.ceil(len(smalls) / rpc) if smalls else 0
        bw = aw + ncols * colw + 10.16; bh = max(ah, min(len(smalls), rpc) * 6.35) + 17.78
        blocks.append((anchor, smalls, info, aw, colw, rpc, bw, bh))
    maxW = max(370.0, max(b[6] for b in blocks) + 40)
    x0, y0 = 25.4, 30.48; x, y, rowh = x0, y0, 0
    for (anchor, smalls, info, aw, colw, rpc, bw, bh) in blocks:
        if x + bw > maxW and x > x0: x = x0; y += rowh; rowh = 0
        if anchor:
            sy, att, cols, ext = info
            AX = snap(x + ext['L'] + sy["w"] / 2 + 2.54); AY = snap(y + sy["h"] / 2 + 5.08)
            sh.comp(anchor, AX, AY); pins = Sheet.pin_pos(anchor, AX, AY)
            for num, nm, n in anchor["pins"]:
                px, py, side = pins[num]; sgn = -1 if side == 'L' else 1
                if not n: sh.nc(px, py); continue
                if num in att:
                    pr, ppin, net = att[num]; c_, wl = cols[num]
                    near = px + sgn * wl; sh.wire(px, py, near, py)
                    pc = byref[pr]; pp = symbols[pc["sym"]]["pins"]
                    # passive pin 'ppin' must be the near end
                    ppin_side = [t for t in pp if t[0] == ppin][0][5]   # 'L' or 'R' in lib
                    want = 'R' if side == 'L' else 'L'                  # near end faces the IC
                    rot = 0 if ppin_side == want else 180
                    cx = near + sgn * 5.08
                    sh.comp(pc, snap(cx), py, rot)
                    for pnum, (qx, qy, qs) in Sheet.pin_pos(pc, snap(cx), py, rot).items():
                        if pnum == ppin: continue
                        on = [t for t in pc["pins"] if t[0] == pnum][0][2]
                        if on: sh.label(on, qx, qy, side)
                        else: sh.nc(qx, qy)
                else:
                    ex = px + sgn * 2.54; sh.wire(px, py, ex, py); sh.label(n, ex, py, side)
        for i, c in enumerate(smalls):
            col, row = divmod(i, rpc)
            cx = snap(x + aw + col * colw + colw / 2); cy = snap(y + 5.08 + row * 6.35)
            sh.comp(c, cx, cy)
            for pnum, (qx, qy, qs) in Sheet.pin_pos(c, cx, cy).items():
                n = [t for t in c["pins"] if t[0] == pnum][0][2]
                if n: sh.label(n, qx, qy, qs)
                else: sh.nc(qx, qy)
        x += bw; rowh = max(rowh, bh)
    return sh, maxW + 20, y + rowh + 20

def other_net(a):
    pr, ppin, n = a
    for num, nm, nn in byref[pr]["pins"]:
        if num != ppin: return nn
    return ''

def paper_for(W, H):
    for nm, pw, ph in [("A4", 297, 210), ("A3", 420, 297), ("A2", 594, 420), ("A1", 841, 594), ("A0", 1189, 841)]:
        if W <= pw and H <= ph: return f'(paper "{nm}")'
    return f'(paper "User" {F(math.ceil(W))} {F(math.ceil(H))})'

# ---------- write ----------
os.makedirs(OUT, exist_ok=True)
root_uuid = U(); sheets = []
for pg, pname in PAGES.items():
    pu = U(); cs = [c for c in comps if c["page"] == pg]
    sh, W, H = draw_page(cs, f"/{root_uuid}/{pu}")
    usedsym = sorted({c["sym"] for c in cs})
    o = ['(kicad_sch (version 20230121) (generator eeschema)', f'(uuid {pu})', paper_for(W, H),
         f'(title_block (title {q(pname)}) (company "zoomMediaPlus") (comment 1 "Generated from EasyEDA Pro netlist V1.2 - verified 1:1"))', '(lib_symbols']
    o += [sym_sexpr(s, "NeatAmp:") for s in usedsym] + [pwr_sexpr(n, "NeatAmp:") for n in sorted(sh.pwr_used)] + [')']
    o += sh.o + [')']
    fn = pname.replace(' ', '_').replace('.', '_') + ".kicad_sch"
    open(os.path.join(OUT, fn), "w", encoding="utf-8").write("\n".join(o)); sheets.append((pu, fn, pname))
o = ['(kicad_sch (version 20230121) (generator eeschema)', f'(uuid {root_uuid})', '(paper "A4")',
     f'(title_block (title {q(PROJ+" MainBoard")}) (company "zoomMediaPlus"))', '(lib_symbols)']
for i, (pu, fn, pname) in enumerate(sheets):
    x = 25.4 + (i % 3) * 88.9; y = 38.1 + (i // 3) * 50.8
    o.append(f'(sheet (at {F(x)} {F(y)}) (size 76.2 25.4) (fields_autoplaced) (stroke (width 0.1524) (type solid)) (fill (color 0 0 0 0.0000)) (uuid {pu})'
             f' (property "Sheetname" {q(pname)} (at {F(x)} {F(y-0.7)} 0) (effects (font (size 1.27 1.27)) (justify left bottom)))'
             f' (property "Sheetfile" {q(fn)} (at {F(x)} {F(y+26)} 0) (effects (font (size 1.27 1.27)) (justify left top)))'
             f' (instances (project {q(PROJ)} (path {q("/"+root_uuid)} (page {q(str(i+2))})))))')
o += ['(sheet_instances (path "/" (page "1")))', ')']
open(os.path.join(OUT, PROJ + ".kicad_sch"), "w", encoding="utf-8").write("\n".join(o))
lib = ['(kicad_symbol_lib (version 20220914) (generator neatamp_gen)'] + [sym_sexpr(s, "") for s in sorted(symbols)] + [pwr_sexpr(n, "") for n in POWER] + [')']
open(os.path.join(OUT, "NeatAmp.kicad_sym"), "w", encoding="utf-8").write("\n".join(lib))
with open(os.path.join(OUT, "net_names.csv"), "w", newline="") as f:
    w = csv.writer(f); w.writerow(["easyeda_net", "kicad_net", "nodes"])
    for n in sorted(netname, key=natkey):
        if n.startswith('$'): w.writerow([n, netname[n], " ".join(f"{r}.{p}" for r, p, _ in nets[n])])
print("components", len(comps), "attached", sum(1 for c in comps if False), "power refs", Sheet.pwr_ctr[0])
