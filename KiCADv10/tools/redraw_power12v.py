"""Redraw Power_12V_DC.kicad_sch to follow Schematic.pdf page 1.

Keeps every component (uuid, all fields incl. Footprint/LCSC/MPN/JLC, in_bom,
instances) and only replaces symbol graphics, placement and wiring.
Layout grid unit u = 1.27 mm.
"""
import copy
import math
import sys
import uuid

import os

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from sexp import Q, esc, parse, dump, find, findall, prop  # noqa: E402

# Usage: python3 tools/redraw_power12v.py [src.kicad_sch [dst.kicad_sch]]
#   default src = dst = KiCADv10/Power_12V_DC.kicad_sch; also refreshes the
#   custom symbols in KiCADv10/NeatAmp.kicad_sym when dst is the project sheet.
PRJ = os.path.dirname(HERE) + '/'
SHEET = PRJ + 'Power_12V_DC.kicad_sch'
SRC = sys.argv[1] if len(sys.argv) > 1 else SHEET
DST = sys.argv[2] if len(sys.argv) > 2 else SHEET
STOCK = os.environ.get('KICAD10_SYMBOL_DIR', '/Applications/KiCad/KiCad.app/Contents/SharedSupport/symbols') + '/'
U = 1.27


def uid():
    return Q(str(uuid.uuid4()))


def mm(v):
    return round(v * U, 4)


def F(v):
    return float(round(v, 4))


sch = parse(open(SRC).read())
old_libs = {x[1]: x for x in findall(find(sch, 'lib_symbols'), 'symbol')}
old_syms = {prop(s, 'Reference')[2]: s for s in findall(sch, 'symbol')}
SHEET_PATH = find(find(find(old_syms['U1'], 'instances'), 'project'), 'path')[1]

# ------------------------------------------------------------------ symbols
_stock = {}


def stock(libname, name):
    if libname not in _stock:
        _stock[libname] = {x[1]: x for x in findall(parse(open(STOCK + libname + '.kicad_sym').read()), 'symbol')}
    s = copy.deepcopy(_stock[libname][name])
    s[1] = Q(libname + ':' + name)
    return s


def eff(size=1.27, justify=None, hide=False, bold=False):
    font = ['font', ['size', F(size), F(size)]]
    if bold:
        font.append(['bold', 'yes'])
    e = ['effects', font]
    if justify:
        e.append(['justify'] + justify.split())
    if hide:
        e.append(['hide', 'yes'])
    return e


def lprop(name, val, x=0, y=0, hide=False, justify=None):
    return ['property', Q(name), Q(val), ['at', F(x), F(y), 0], eff(justify=justify, hide=hide)]


def lpin(num, name, x, y, ang, length=2.54, hide=False, typ='passive'):
    p = ['pin', typ, 'line', ['at', F(x), F(y), ang], ['length', F(length)]]
    if hide:
        p.append(['hide', 'yes'])
    p += [['name', Q(name), eff()], ['number', Q(num), eff()]]
    return p


def chip(libname, refpfx, w, top, bot, pins, desc):
    """Box symbol. pins: (num, name, x, y, angle) in mm."""
    base = libname.split(':')[1]
    return ['symbol', Q(libname), ['pin_names', ['offset', F(0.508)]],
            ['exclude_from_sim', 'no'], ['in_bom', 'yes'], ['on_board', 'yes'],
            lprop('Reference', refpfx, -w, top + 1.27, justify='left'),
            lprop('Value', base, -w, bot - 1.27, justify='left'),
            lprop('Footprint', '', hide=True), lprop('Datasheet', '', hide=True),
            lprop('Description', desc, hide=True),
            ['symbol', Q(base + '_0_1'),
             ['rectangle', ['start', F(-w), F(top)], ['end', F(w), F(bot)],
              ['stroke', ['width', F(0.254)], ['type', 'default']], ['fill', ['type', 'background']]]],
            ['symbol', Q(base + '_1_1')] + [lpin(n, nm, x, y, a) for n, nm, x, y, a in pins]]


# LMQ66430: PDF pin order. Left 1..7 top-down, right 15..8 top-down.
lmq_pins = [(str(n), nm, -15.24, mm(5 - 2 * i), 0) for i, (n, nm) in enumerate(
    [(1, 'EN/UVLO'), (2, 'NC'), (3, 'VIN'), (4, 'NC'), (5, 'NC'), (6, 'PGND'), (7, 'SW')])]
lmq_pins += [(str(n), nm, 15.24, mm(7 - 2 * i), 180) for i, (n, nm) in enumerate(
    [(15, 'GND/DAP'), (14, 'PG'), (13, 'MODE/SYNC'), (12, 'NC'), (11, 'VOUT/FB'), (10, 'VCC'), (9, 'NC'), (8, 'BOOT')])]
SYM_LMQ = chip('NeatAmp:LMQ66430MC3RXBRQ1', 'U', 12.7, 11.43, -11.43, lmq_pins,
               'LMQ66430 36V 3A synchronous buck, VQFN-14 (pin order as in Schematic.pdf)')

# TPS7A4701: functional layout. Left inputs, right outputs/NC, bottom ANY-OUT + GND.
tps_pins = [('13', 'EN', -19.05, mm(9), 0), ('15', 'IN', -19.05, mm(5), 0), ('16', 'IN', -19.05, mm(3), 0),
            ('14', 'NR', -19.05, mm(-1), 0),
            ('1', 'OUT', 19.05, mm(9), 180), ('20', 'OUT', 19.05, mm(7), 180), ('3', 'SENSE/FB', 19.05, mm(3), 180),
            ('2', 'NC', 19.05, mm(-3), 180), ('17', 'NC', 19.05, mm(-5), 180), ('18', 'NC', 19.05, mm(-7), 180),
            ('19', 'NC', 19.05, mm(-9), 180)]
for i, (n, nm) in enumerate([(5, '6P4V1'), (4, '6P4V2'), (6, '3P2V'), (8, '1P6V'), (9, '0P8V'),
                             (10, '0P4V'), (11, '0P2V'), (12, '0P1V'), (7, 'GND'), (21, 'EPAD')]):
    tps_pins.append((str(n), nm, mm(-9 + 2 * i), mm(-21), 90))
SYM_TPS = chip('NeatAmp:TPS7A4701RGWR', 'U', 16.51, 13.97, -24.13, tps_pins,
               'TPS7A4701 36V 1A low-noise LDO with ANY-OUT, VQFN-20')


def make_pmos():
    """Device:Q_PMOS rotated 90 deg CCW: D left, S right, G bottom.

    Uses KiCad 10 native pin stacks: one drawn pin per terminal whose number
    lists all package pads, e.g. "[1-3]" -> pads 1,2,3 (E38P100KH PDFN5x6:
    S = 1,2,3   G = 4   D = 5,6,7,8 + exposed pad 9).
    """
    s = stock('Device', 'Q_PMOS')
    s[1] = Q('NeatAmp:Q_PMOS_E38P100KH')

    def rot(x):
        if isinstance(x, list):
            if x and x[0] in ('xy', 'center', 'start', 'mid', 'end') and len(x) == 3:
                return [x[0], F(-float(x[2])), F(float(x[1]))]
            return [rot(c) for c in x]
        return x
    out = []
    for c in s:
        if isinstance(c, list) and c[0] in ('pin_numbers', 'pin_names'):
            continue        # show pin names (S/G/D) and stacked numbers
        if isinstance(c, list) and c[0] == 'symbol':
            c = rot(c)
            c[1] = Q(c[1].replace('Q_PMOS', 'Q_PMOS_E38P100KH'))
            newc = []
            for g in c:
                if isinstance(g, list) and g[0] == 'pin':
                    nm = find(g, 'name')[1]
                    at = find(g, 'at')
                    x, y, a = float(at[1]), float(at[2]), int(at[3])
                    num = {'S': '[1-3]', 'G': '4', 'D': '[5-9]'}[nm]
                    px, py, ln = -y, x, float(find(g, 'length')[1])
                    if nm in 'DS':      # longer D/S pins so the stacked numbers clear the body
                        px += -2.54 if px < 0 else 2.54
                        ln += 2.54
                    newc.append(lpin(num, nm, px, py, (a + 90) % 360, ln))
                else:
                    newc.append(g)
            c = newc
        elif isinstance(c, list) and c[0] == 'property':
            if c[1] == 'Value':
                c[2] = Q('Q_PMOS_E38P100KH')
            if c[1] == 'Description':
                c[2] = Q('P-MOSFET E38P100KH, PDFN5x6: S = pads 1,2,3  G = pad 4  D = pads 5-8 + exposed pad 9')
            if c[1] in ('Reference', 'Value'):
                find(c, 'at')[1:3] = [F(3.81), F(-3.81 if c[1] == 'Reference' else -6.35)]
        out.append(c)
    out.insert(2, ['pin_names', ['offset', 0]])
    return out


SYM_Q = make_pmos()
CUSTOM = [SYM_LMQ, SYM_TPS, SYM_Q]

LIB = {
    'R': 'Device:R', 'C': 'Device:C', 'CP': 'Device:C_Polarized', 'L': 'Device:L',
    'FB': 'Device:FerriteBead', 'DZ': 'Device:D_Zener', 'F': 'Device:Fuse',
    'TP': 'Connector:TestPoint', 'CN': 'Connector:Screw_Terminal_01x02',
    'Q': 'NeatAmp:Q_PMOS_E38P100KH', 'LMQ': 'NeatAmp:LMQ66430MC3RXBRQ1', 'TPS': 'NeatAmp:TPS7A4701RGWR',
}
libsyms = {}
for k, v in LIB.items():
    if v.startswith('NeatAmp:'):
        libsyms[v] = next(c for c in CUSTOM if c[1] == v)
    else:
        libsyms[v] = stock(*v.split(':'))
for name, s in old_libs.items():
    if name.startswith('NeatAmp:PWR_'):
        libsyms[name] = s


def lib_pins(libname):
    out = {}

    def walk(x):
        for c in x:
            if isinstance(c, list):
                if c[0] == 'pin':
                    at = find(c, 'at')
                    out.setdefault(find(c, 'number')[1], (float(at[1]), float(at[2])))
                else:
                    walk(c)
    walk(libsyms[libname])
    return out


def xform(px, py, X, Y, rot, mirror=None):
    # KiCad: mirror applied in symbol space before rotation
    if mirror == 'y':
        px = -px
    elif mirror == 'x':
        py = -py
    a = math.radians(rot)
    rx = px * math.cos(a) - py * math.sin(a)
    ry = px * math.sin(a) + py * math.cos(a)
    return (round(X + rx, 3), round(Y - ry, 3))


# ------------------------------------------------------------------ layout
parts = {}   # ref -> dict(kind, X, Y, rot, mirror, txt)


DX, TH = 0, 0   # layout shift: x >= TH moves right by DX (lets a block grow without renumbering)


def sx(x):
    return x + DX if DX and x >= TH else x


def P(ref, kind, x, y, rot=0, txt='r', mirror=None):
    parts[ref] = dict(kind=kind, X=mm(sx(x)), Y=mm(y), rot=rot, mirror=mirror, txt=txt)


wires, pwr, nc, labels, glabels, texts = [], [], [], [], [], []


def W(*pts):
    wires.append([(mm(sx(x)), mm(y)) for x, y in pts])


def PW(name, x, y, rot=0, show=True):
    pwr.append((name, mm(sx(x)), mm(y), rot, show))


def NC(x, y):
    nc.append((mm(sx(x)), mm(y)))


def LBL(name, x, y):
    labels.append((name, mm(sx(x)), mm(y)))


def T(s, x, y, size=1.27, bold=False):
    texts.append((s, mm(sx(x)), mm(y), size, bold))


# ---- input protection: rail y=40, GND bus y=58
P('CN1', 'CN', 16, 40, 0, txt='cn', mirror='y')           # pins (20,40) (20,42)
P('F1', 'F', 28, 40, 90, txt='h')                        # (25,40)-(31,40)
# Reverse-polarity P-FET: DRAIN to input, SOURCE to load (PVDD). The body diode
# conducts input->load at power-up, then Vgs<0 turns the channel on; with a
# reversed input the body diode blocks and Vgs>=0 keeps Q1 off.
# D1 (15 V Vgs clamp) and R2 sit between SOURCE and GATE, R5 pulls the gate to GND.
P('Q1', 'Q', 42, 42, 0, txt='qt')                        # D (36,40) S (48,40) G (42,46)
P('D1', 'DZ', 50, 46, 270)                               # K (50,43) A (50,49)
P('R2', 'R', 64, 46, 180)                                # pin2 (64,43)=S  pin1 (64,49)=G
P('R5', 'R', 64, 55, 180)                                # pin2 (64,52)=G  pin1 (64,58)=GND
W((31, 40), (36, 40))
W((48, 40), (68, 40))
W((50, 40), (50, 43)); W((64, 40), (64, 43))
W((50, 49), (50, 52)); W((42, 46), (42, 52), (64, 52)); W((64, 49), (64, 52))
LBL('Q1_D', 31, 40); LBL('Q1_G', 52, 52)
DX, TH = 12, 56     # everything right of the old Q1 moves 12 u to the right
P('TP1', 'TP', 63, 40, 0, txt='tp')
P('C4', 'CP', 66, 49)                                    # + (66,46)  - (66,52)
P('D2', 'DZ', 78, 49, 270)                               # K (78,46) A (78,52)
P('L1', 'FB', 86, 40, 90, txt='h')                       # (83,40)-(89,40)
P('R4', 'R', 98, 40, 90, txt='h')                        # (95,40)-(101,40)
P('C5', 'CP', 108, 49)
P('C6', 'C', 116, 49, 180)
P('C7', 'C', 124, 49, 180)
P('TP30', 'TP', 128, 40, 0, txt='tp')
P('C2', 'C', 132, 49, 180)
P('C3', 'C', 140, 49, 180)

W((20, 40), (25, 40))
W((56, 40), (83, 40))
W((89, 40), (95, 40))
W((101, 40), (151, 40), (154, 40))
W((151, 40), (151, 44), (154, 44))                       # VIN
for x in (66, 78, 108, 116, 124, 132, 140):
    W((x, 40), (x, 46)); W((x, 52), (x, 58))
W((20, 42), (21, 42), (21, 58), (140, 58))
PW('GND', 90, 58)
PW('PVDD', 59, 40)
PW('PVDDLMQ', 104, 40)
LBL('CN1_P1', 22, 40); LBL('L1_P2', 90, 40)

# ---- 13.2 V buck
P('U1', 'LMQ', 166, 45, 0, txt='chip')                  # left x=154 rows 40..52, right x=178 rows 38..52
for y in (42, 46, 48):
    NC(154, y)
PW('GND', 154, 50, 270, show=False)                      # PGND
P('L2', 'L', 150, 58, 180)                               # pin2 (150,55) pin1 (150,61)
W((154, 52), (150, 52), (150, 55))
W((150, 61), (150, 64), (212, 64))
for i, r in enumerate(['C9', 'C10', 'C11', 'C12', 'C13', 'C14', 'C15']):
    x = 156 + 8 * i
    P(r, 'C', x, 67, 180 if r == 'C15' else 0)
    W((x, 70), (x, 74))
W((156, 74), (204, 74))
PW('GND', 180, 74)
PW('+13.2V', 212, 64)
# right side
PW('GND', 178, 38, 90, show=False)                       # GND/DAP
P('R1', 'R', 188, 37, 180)                               # pin2 (188,34) pin1 (188,40)
W((178, 40), (198, 40))                                  # PG -> GOOD_13.2V
glabels.append(('GOOD_13.2V', mm(sx(198)), mm(40), 'output', 0))
W((178, 42), (184, 42), (184, 32), (188, 32), (188, 34))  # MODE/SYNC + R1 -> 3.3V
PW('3.3V', 186, 32)
NC(178, 44); NC(178, 50); NC(178, 52)
W((178, 46), (232, 46))                                  # VOUT/FB
LBL('U1_VOUT_FB', 200, 46)
W((178, 48), (208, 48))                                  # VCC
P('C8', 'C', 208, 51)
PW('GND', 208, 54)
P('R3', 'R', 222, 39, 180)                               # pin2 (222,36) pin1 (222,42)
P('C1', 'C', 232, 39, 180)                               # pin2 (232,36) pin1 (232,42)
P('R6', 'R', 222, 49, 180)                               # pin2 (222,46) pin1 (222,52)
PW('GND', 222, 52)
W((218, 32), (232, 32))
W((222, 32), (222, 36)); W((232, 32), (232, 36))
W((222, 42), (222, 46)); W((232, 42), (232, 46))
PW('+13.2V', 218, 32)
P('TP2', 'TP', 227, 32, 0, txt='tp')

# ---- 12V_GVDD LDO
DX = 0
P('U2', 'TPS', 166, 118, 0, txt='chip2')                 # left x=151, right x=181, bottom y=139
P('L3', 'FB', 112, 113, 270, txt='h')                    # pin2 (109,113) pin1 (115,113)
PW('+13.2V', 104, 113)
W((104, 113), (109, 113))
W((115, 113), (151, 113))
W((148, 113), (148, 115), (151, 115))
LBL('U2_IN', 117, 113)
P('C22', 'C', 124, 116)                                  # (124,113)-(124,119)
PW('GND', 124, 119)
glabels.append(('ENABLE_12V', mm(128), mm(109), 'input', 180))
W((128, 109), (151, 109))
P('R7', 'R', 136, 106, 180)                              # pin2 (136,103) pin1 (136,109)
PW('3.3V', 136, 103)
W((151, 119), (142, 119))
P('C16', 'C', 142, 122)                                  # (142,119)-(142,125)
PW('GND', 142, 125)
W((181, 109), (236, 109))
W((181, 111), (184, 111)); W((184, 109), (184, 115)); W((181, 115), (184, 115))
P('TP3', 'TP', 188, 109, 0, txt='tp')
for i, r in enumerate(['C17', 'C18', 'C19', 'C20', 'C21']):
    x = 192 + 8 * i
    P(r, 'C', x, 112)
    W((x, 115), (x, 119))
W((192, 119), (224, 119))
PW('GND', 208, 119)
PW('12V_GVDD', 236, 109)
for y in (121, 123, 125, 127):
    NC(181, y)
for x in (159, 163, 167, 171):
    NC(x, 139)
for x in (157, 161, 165, 169, 173, 175):
    W((x, 139), (x, 143))
W((157, 143), (175, 143))
PW('GND', 166, 143)

# ---- notes
T('INPUT: fuse, reverse-polarity P-FET, 36 V TVS', 16, 30, 1.8, True)
DX = 12                                                  # top-section notes follow the shifted parts
T('13.2 V BUCK  (LMQ66430)', 146, 26, 1.8, True)
T('Keep in FPWM mode', 190, 31)
T('VOUT = 1.0 V x (1 + R3/R6)\n= 1.0 V x (1 + 100k/8.2k) = 13.2 V', 240, 44)
DX = 0
T('12V_GVDD LOW-NOISE LDO  (TPS7A4701)', 100, 96, 1.8, True)
T('ANY-OUT: 6P4V1 + 3P2V + 0P8V + 0P2V tied to GND\nVOUT = 1.4 V + 6.4 V + 3.2 V + 0.8 V + 0.2 V = 12.0 V', 152, 152)
T('For PCB use:\nJLC04162H-7628 - sufficient\nJLC04162H-3313 - better', 16, 162)
T('LMQ66410 → 13.2V\nLC/ferrite filter\nlow-noise TPS7A49 / TPS7A47 / LT1763 / TLV767 / TPS7A26 → 12V_GVDD\n'
  'local decoupling at TAS pins', 16, 176)

# ------------------------------------------------------------------ build
items = []          # top-level schematic items
pin_pts = []        # all pin connection points (sheet mm)
pwr_refs = sorted(prop(s, 'Reference')[2] for s in old_syms.values() if prop(s, 'Reference')[2].startswith('#PWR'))
next_pwr = [282]


def new_pwr_ref():
    if pwr_refs:
        return pwr_refs.pop(0)
    next_pwr[0] += 1
    return '#PWR%04d' % next_pwr[0]


def set_at(p, x, y, ang=0):
    at = find(p, 'at')
    at[1:] = [F(x), F(y), ang]


def set_eff(p, justify=None, hide=None, size=None):
    e = find(p, 'effects')
    if e is None:
        e = ['effects', ['font', ['size', 1.27, 1.27]]]
        p.append(e)
    e[:] = [c for c in e if not (isinstance(c, list) and c[0] in ('justify', 'hide'))]
    if size:
        find(e, 'font')[:] = ['font', ['size', F(size), F(size)]]
    if justify:
        e.append(['justify'] + justify.split())
    p[:] = [c for c in p if not (isinstance(c, list) and c[0] == 'hide')]
    if hide:
        # KiCad 10 stores hide as a direct child of property
        p.insert(4, ['hide', 'yes'])


for ref, d in parts.items():
    s = copy.deepcopy(old_syms[ref])
    libname = LIB[d['kind']]
    find(s, 'lib_id')[1] = Q(libname)
    find(s, 'at')[1:] = [F(d['X']), F(d['Y']), d['rot']]
    s[:] = [c for c in s if not (isinstance(c, list) and c[0] == 'mirror')]
    if d['mirror']:
        s.insert(3, ['mirror', d['mirror']])
    X, Y = d['X'], d['Y']
    for p in findall(s, 'property'):
        if p[1] not in ('Reference', 'Value'):
            set_at(p, X, Y)
            set_eff(p, hide=True)
    r, v = prop(s, 'Reference'), prop(s, 'Value')
    t = d['txt']
    if t == 'r':
        set_at(r, X + mm(2), Y - mm(1)); set_at(v, X + mm(2), Y + mm(1))
        set_eff(r, 'left'); set_eff(v, 'left')
    elif t == 'l':
        set_at(r, X - mm(2), Y - mm(1)); set_at(v, X - mm(2), Y + mm(1))
        set_eff(r, 'right'); set_eff(v, 'right')
    elif t == 'h':
        set_at(r, X, Y - mm(3)); set_at(v, X, Y + mm(3))
        set_eff(r); set_eff(v)
    elif t == 'qt':
        set_at(r, X, Y - mm(8)); set_at(v, X, Y - mm(6))
        set_eff(r); set_eff(v)
    elif t == 'tp':
        set_at(r, X + mm(1), Y - mm(4)); set_at(v, X, Y)
        set_eff(r, 'left'); set_eff(v, hide=True)
    elif t == 'cn':
        set_at(r, X - mm(1), Y - mm(3)); set_at(v, X - mm(1), Y + mm(5))
        set_eff(r); set_eff(v)
    elif t == 'chip':
        set_at(r, X - mm(10), Y - mm(10)); set_at(v, X - mm(10), Y + mm(10))
        set_eff(r, 'left'); set_eff(v, 'left')
    elif t == 'chip2':
        set_at(r, X - mm(13), Y - mm(12)); set_at(v, X - mm(9), Y - mm(12))
        set_eff(r, 'left'); set_eff(v, 'left')
    for p in (r, v):
        find(find(p, 'effects'), 'font')[:] = ['font', ['size', 1.27, 1.27]]
        if d['rot'] in (90, 270):
            find(p, 'at')[3] = 90   # field angle is relative to symbol -> horizontal text
        if d['rot'] == 180:
            j = find(find(p, 'effects'), 'justify')
            if j:
                j[1:] = [{'left': 'right', 'right': 'left'}.get(a, a) for a in j[1:]]
    lp = lib_pins(libname)
    have = {pp[1]: pp for pp in findall(s, 'pin')}
    if set(lp) != set(have):
        s[:] = [c for c in s if not (isinstance(c, list) and c[0] == 'pin')]
        at = next(i for i, c in enumerate(s) if isinstance(c, list) and c[0] == 'instances')
        s[at:at] = [have.get(n) or ['pin', Q(n), ['uuid', uid()]] for n in lp]
    for n, (px, py) in lp.items():
        pin_pts.append((xform(px, py, X, Y, d['rot'], d['mirror']), ref, n))
    items.append(s)

missing = [r for r in old_syms if not r.startswith('#') and r not in parts]
assert not missing, missing

tmpl = {}
for s in old_syms.values():
    if prop(s, 'Reference')[2].startswith('#PWR'):
        tmpl.setdefault(find(s, 'lib_id')[1], s)

for name, x, y, rot, show in pwr:
    libname = 'NeatAmp:PWR_' + name
    s = copy.deepcopy(tmpl[libname])
    find(s, 'at')[1:] = [F(x), F(y), rot]
    find(s, 'uuid')[1] = uid()
    ref = new_pwr_ref()
    prop(s, 'Reference')[2] = Q(ref)
    find(find(find(find(s, 'instances'), 'project'), 'path'), 'reference')[1] = Q(ref)
    for pn in findall(s, 'pin'):
        find(pn, 'uuid')[1] = uid()
    for p in findall(s, 'property'):
        set_at(p, x, y, 0)
    v = prop(s, 'Value')
    gnd = name == 'GND'
    if rot == 0:
        set_at(v, x, y + (3.81 if gnd else -3.556))
    set_eff(v, hide=not show)
    pin_pts.append(((round(x, 3), round(y, 3)), '#', name))
    items.append(s)

# ------------------------------------------------------------------ wires: split + junctions
segs = []
for poly in wires:
    for a, b in zip(poly, poly[1:]):
        segs.append(((round(a[0], 3), round(a[1], 3)), (round(b[0], 3), round(b[1], 3))))
special = {p for s in segs for p in s} | {p for p, _, _ in pin_pts} | {(round(x, 3), round(y, 3)) for _, x, y in labels}


def on_seg(p, a, b):
    if a[0] == b[0] == p[0]:
        return min(a[1], b[1]) < p[1] < max(a[1], b[1])
    if a[1] == b[1] == p[1]:
        return min(a[0], b[0]) < p[0] < max(a[0], b[0])
    return False


out = []
for a, b in segs:
    assert a[0] == b[0] or a[1] == b[1], ('diagonal', a, b)
    cuts = sorted([p for p in special if on_seg(p, a, b)], key=lambda p: abs(p[0] - a[0]) + abs(p[1] - a[1]))
    pts = [a] + cuts + [b]
    out += [(p, q) for p, q in zip(pts, pts[1:]) if p != q]
segs = out
deg = {}
for a, b in segs:
    deg[a] = deg.get(a, 0) + 1
    deg[b] = deg.get(b, 0) + 1
for p, _, _ in pin_pts:
    if p in deg:
        deg[p] += 1
junctions = [p for p, n in deg.items() if n >= 3]

# dangling pin check (pins neither on wire, nc, nor directly on another pin)
ncset = {(round(x, 3), round(y, 3)) for x, y in nc}
pin_at = {}
for p, ref, n in pin_pts:
    pin_at.setdefault(p, []).append((ref, n))
for p, ref, n in pin_pts:
    if p not in deg and p not in ncset and len(pin_at[p]) < 2:
        print('WARNING unconnected pin', ref, n, p)

# ------------------------------------------------------------------ emit
body = []
for x, y in junctions:
    body.append(['junction', ['at', F(x), F(y)], ['diameter', 0], ['color', 0, 0, 0, 0], ['uuid', uid()]])
for x, y in nc:
    body.append(['no_connect', ['at', F(x), F(y)], ['uuid', uid()]])
for a, b in segs:
    body.append(['wire', ['pts', ['xy', F(a[0]), F(a[1])], ['xy', F(b[0]), F(b[1])]],
                 ['stroke', ['width', 0], ['type', 'default']], ['uuid', uid()]])
for name, x, y in labels:
    body.append(['label', Q(name), ['at', F(x), F(y), 0], eff(justify='left bottom'), ['uuid', uid()]])
for name, x, y, shape, ang in glabels:
    j = 'left' if ang == 0 else 'right'
    body.append(['global_label', Q(name), ['shape', shape], ['at', F(x), F(y), ang],
                 ['fields_autoplaced', 'yes'], eff(justify=j), ['uuid', uid()],
                 ['property', Q('Intersheetrefs'), Q('${INTERSHEET_REFS}'), ['at', F(x), F(y), 0],
                  eff(justify=j, hide=True)]])
for s, x, y, size, bold in texts:
    body.append(['text', esc(s), ['exclude_from_sim', 'no'], ['at', F(x), F(y), 0],
                 eff(size, 'left bottom', bold=bold), ['uuid', uid()]])

new = []
for c in sch:
    if isinstance(c, list) and c[0] in ('wire', 'label', 'global_label', 'no_connect', 'junction', 'text', 'symbol'):
        continue
    if isinstance(c, list) and c[0] == 'lib_symbols':
        c = ['lib_symbols'] + [libsyms[k] for k in sorted(libsyms)]
    if isinstance(c, list) and c[0] == 'title_block':
        c = ['title_block', ['title', Q('Power 12V DC')], ['rev', Q('V1.2')], ['company', Q('zoomMediaPlus')],
             ['comment', 1, Q('Board: MainBoard - Class D amp')],
             ['comment', 2, Q('Drawn: Igor Korzinek')],
             ['comment', 3, Q('Redrawn in KiCad 10 after Schematic.pdf p.1; netlist = EasyEDA V1.2 (verified)')]]
    new.append(c)
    if isinstance(c, list) and c[0] == 'lib_symbols':
        new += body + items
text = dump(new) + '\n'
open(DST, 'w').write(text)
print('parts', len(parts), 'pwr', len(pwr), 'wires', len(segs), 'junctions', len(junctions), 'nc', len(nc))


# ------------------------------------------------------------------ NeatAmp.kicad_sym
def block_end(s, i):
    """Index just past the S-expression starting at s[i] == '('."""
    depth, j, n = 0, i, len(s)
    while j < n:
        ch = s[j]
        if ch == '"':
            j += 1
            while s[j] != '"':
                j += 2 if s[j] == '\\' else 1
        elif ch == '(':
            depth += 1
        elif ch == ')':
            depth -= 1
            if depth == 0:
                return j + 1
        j += 1
    raise ValueError('unbalanced')


if os.path.abspath(DST) == os.path.abspath(SHEET):
    libf = PRJ + 'NeatAmp.kicad_sym'
    lib = open(libf).read()
    for c in CUSTOM:
        name = c[1].split(':')[1]
        key = '\n(symbol "%s"' % name
        i = lib.find(key)
        if i >= 0:                      # replace previous version of this symbol
            lib = lib[:i] + lib[block_end(lib, i + 1):]
        c2 = copy.deepcopy(c)
        c2[1] = Q(name)
        k = lib.rstrip().rfind(')')     # closing paren of kicad_symbol_lib
        lib = lib[:k].rstrip() + '\n' + dump(c2) + '\n)\n'
    open(libf, 'w').write(lib)
    print('updated', libf)
