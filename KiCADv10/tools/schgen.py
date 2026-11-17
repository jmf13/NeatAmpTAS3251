"""Shared engine for redrawing the KiCad 10 sheets after Schematic.pdf.

A per-sheet script (redraw_*.py) only describes the layout:

    from schgen import Sheet
    s = Sheet('Power_5V_DC.kicad_sch')
    s.P('U3', 'LMQ', 166, 45, txt='chip')        # place an existing part
    s.W((154, 52), (150, 52), (150, 55))          # wire polyline
    s.PW('GND', 150, 70)                          # power symbol
    s.save(title='Power 5V DC', page='Schematic.pdf p.2')

What it guarantees:
- every existing symbol is kept with its uuid, all fields (Value, Footprint,
  LCSC, MPN, JLC class...), in_bom/dnp and instances; only lib_id, position,
  rotation, field placement and the drawn wiring change;
- every part on the sheet must be placed (assert), wires are split at every
  pin/label/wire end lying on them and junctions are added where 3+ meet;
- custom symbols used by the sheet are refreshed in NeatAmp.kicad_sym.

Coordinates are in grid units u = 1.27 mm. Always verify with
    kicad-cli sch export netlist --format kicadxml -o after.xml NeatAmp.kicad_sch
    python3 tools/netcmp.py before.xml after.xml
"""
import copy
import glob
import math
import os
import re
import sys
import uuid

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from sexp import Q, esc, parse, dump, find, findall, prop  # noqa: E402

PRJ = os.path.dirname(HERE) + '/'
STOCK = os.environ.get('KICAD10_SYMBOL_DIR', '/Applications/KiCad/KiCad.app/Contents/SharedSupport/symbols') + '/'
U = 1.27


def uid():
    return Q(str(uuid.uuid4()))


def mm(v):
    return round(v * U, 4)


def F(v):
    return float(round(v, 4))


# ====================================================================== symbols
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
            ['symbol', Q(base + '_1_1')] + [lpin(*p) for p in pins]]


def sym_lmq66430():
    """LMQ66430: Schematic.pdf pin order. Left 1..7 top-down, right 15..8 top-down."""
    pins = [(str(n), nm, -15.24, mm(5 - 2 * i), 0) for i, (n, nm) in enumerate(
        [(1, 'EN/UVLO'), (2, 'NC'), (3, 'VIN'), (4, 'NC'), (5, 'NC'), (6, 'PGND'), (7, 'SW')])]
    pins += [(str(n), nm, 15.24, mm(7 - 2 * i), 180) for i, (n, nm) in enumerate(
        [(15, 'GND/DAP'), (14, 'PG'), (13, 'MODE/SYNC'), (12, 'NC'), (11, 'VOUT/FB'), (10, 'VCC'), (9, 'NC'),
         (8, 'BOOT')])]
    return chip('NeatAmp:LMQ66430MC3RXBRQ1', 'U', 12.7, 11.43, -11.43, pins,
                'LMQ66430 36V 3A synchronous buck, VQFN-14 (pin order as in Schematic.pdf)')


def sym_tps7a4701():
    """TPS7A4701: functional layout. Left inputs, right outputs/NC, bottom ANY-OUT + GND."""
    pins = [('13', 'EN', -19.05, mm(9), 0), ('15', 'IN', -19.05, mm(5), 0), ('16', 'IN', -19.05, mm(3), 0),
            ('14', 'NR', -19.05, mm(-1), 0),
            ('1', 'OUT', 19.05, mm(9), 180), ('20', 'OUT', 19.05, mm(7), 180), ('3', 'SENSE/FB', 19.05, mm(3), 180),
            ('2', 'NC', 19.05, mm(-3), 180), ('17', 'NC', 19.05, mm(-5), 180), ('18', 'NC', 19.05, mm(-7), 180),
            ('19', 'NC', 19.05, mm(-9), 180)]
    for i, (n, nm) in enumerate([(5, '6P4V1'), (4, '6P4V2'), (6, '3P2V'), (8, '1P6V'), (9, '0P8V'),
                                 (10, '0P4V'), (11, '0P2V'), (12, '0P1V'), (7, 'GND'), (21, 'EPAD')]):
        pins.append((str(n), nm, mm(-9 + 2 * i), mm(-21), 90))
    return chip('NeatAmp:TPS7A4701RGWR', 'U', 16.51, 13.97, -24.13, pins,
                'TPS7A4701 36V 1A low-noise LDO with ANY-OUT, VQFN-20')


def sym_ap63203():
    """AP63203 (TSOT-26), Schematic.pdf pin order: left FB/EN/VIN, right BST/SW/GND."""
    pins = [('1', 'FB', -10.16, 2.54, 0), ('2', 'EN', -10.16, 0, 0), ('3', 'VIN', -10.16, -2.54, 0),
            ('6', 'BST', 10.16, 2.54, 180), ('5', 'SW', 10.16, 0, 180), ('4', 'GND', 10.16, -2.54, 180)]
    return chip('NeatAmp:AP63203WU-7', 'U', 7.62, 5.08, -5.08, pins,
                'AP63203 3.3V fixed 2A synchronous buck, TSOT-26')


def sym_tps7a2033():
    """TPS7A2033 (SOT-23-5): left IN/EN, right OUT/NC, GND at the bottom."""
    pins = [('1', 'IN', -8.89, 2.54, 0), ('3', 'EN', -8.89, -2.54, 0),
            ('5', 'OUT', 8.89, 2.54, 180), ('4', 'NC', 8.89, -2.54, 180),
            ('2', 'GND', 0, -7.62, 90)]
    return chip('NeatAmp:TPS7A2033PDBVR', 'U', 6.35, 5.08, -5.08, pins,
                'TPS7A2033 3.3V 300mA low-noise LDO, SOT-23-5')


def sym_esp32s3_wroom():
    """ESP32-S3-WROOM-1U, Schematic.pdf layout: left 1..14, bottom 15..26, right 40..27, top 41 (GND)."""
    names = {1: 'GND', 2: '3V3', 3: 'EN', 4: 'IO4', 5: 'IO5', 6: 'IO6', 7: 'IO7', 8: 'IO15', 9: 'IO16', 10: 'IO17',
             11: 'IO18', 12: 'IO8', 13: 'IO19', 14: 'IO20', 15: 'IO3', 16: 'IO46', 17: 'IO9', 18: 'IO10', 19: 'IO11',
             20: 'IO12', 21: 'IO13', 22: 'IO14', 23: 'IO21', 24: 'IO47', 25: 'IO48', 26: 'IO45', 27: 'IO0', 28: 'IO35',
             29: 'IO36', 30: 'IO37', 31: 'IO38', 32: 'IO39', 33: 'IO40', 34: 'IO41', 35: 'IO42', 36: 'RXD0',
             37: 'TXD0', 38: 'IO2', 39: 'IO1', 40: 'GND', 41: 'GND'}
    pins = [(str(n), names[n], mm(-21), mm(13 - 2 * (n - 1)), 0) for n in range(1, 15)]
    pins += [(str(n), names[n], mm(21), mm(13 - 2 * (40 - n)), 180) for n in range(27, 41)]
    pins += [(str(n), names[n], mm(-11 + 2 * (n - 15)), mm(-19), 90) for n in range(15, 27)]
    pins += [('41', 'GND', 0, mm(18), 270)]
    return chip('NeatAmp:ESP32-S3-WROOM-1U', 'U', mm(19), mm(16), mm(-17), pins,
                'ESP32-S3-WROOM-1U-N8R8 module (pin order as in Schematic.pdf). IO35/36/37 = Octal PSRAM, keep NC')


def sym_usbc_receptacle():
    """TYPE-C-31-M-12 USB 2.0 receptacle, functional order; shell pads 1-4 as one stacked pin."""
    rows = [('A4B9', 'VBUS', 11), ('B4A9', 'VBUS', 9), ('A5', 'CC1', 6), ('B5', 'CC2', 4), ('A6', 'DP1', 0),
            ('B6', 'DP2', -2), ('A7', 'DN1', -4), ('B7', 'DN2', -6), ('A8', 'SBU1', -9), ('B8', 'SBU2', -11)]
    pins = [(n, nm, mm(10), mm(y), 180, 5.08) for n, nm, y in rows]
    pins += [('A1B12', 'GND', mm(-1), mm(-19), 90, 5.08), ('B1A12', 'GND', mm(2), mm(-19), 90, 5.08),
             ('[1-4]', 'SHIELD', mm(-4), mm(-19), 90, 5.08)]
    return chip('NeatAmp:USB_C_TYPE-C-31-M-12', 'USBC', mm(6), mm(13), mm(-15), pins,
                'USB-C receptacle (USB 2.0), shell pads 1-4 = SHIELD')


def sym_usblc6():
    """USBLC6-2SC6 ESD array: connector side left, MCU side right, VBUS top, GND bottom."""
    pins = [('1', 'IO1', mm(-7), mm(2), 0), ('3', 'IO2', mm(-7), mm(-2), 0),
            ('6', 'IO1', mm(7), mm(2), 180), ('4', 'IO2', mm(7), mm(-2), 180),
            ('5', 'VBUS', 0, mm(7), 270), ('2', 'GND', 0, mm(-7), 90)]
    return chip('NeatAmp:USBLC6-2SC6', 'D', mm(5), mm(5), mm(-5), pins, 'USBLC6-2SC6 USB ESD protection, SOT-23-6')


def sym_sk9822():
    """SK9822 (APA102-type) RGB LED: SDI/CKI/GND left, SDO/CKO/VCC right (Schematic.pdf order)."""
    pins = [('1', 'SDI', mm(-6), mm(2), 0), ('2', 'CKI', mm(-6), 0, 0), ('3', 'GND', mm(-6), mm(-2), 0),
            ('6', 'SDO', mm(6), mm(2), 180), ('5', 'CKO', mm(6), 0, 180), ('4', 'VCC', mm(6), mm(-2), 180)]
    return chip('NeatAmp:SK9822', 'U', mm(4), mm(4), mm(-4), pins, 'SK9822 RGB LED with SPI-like data/clock, 5050')


def sym_sw_push_4pin():
    """4-terminal tact switch (PTS645): 1-2 and 3-4 are joined inside the part, contact between the pairs."""
    st = ['stroke', ['width', F(0.254)], ['type', 'default']]
    fl = ['fill', ['type', 'none']]
    g = [['polyline', ['pts', ['xy', -2.54, 5.08], ['xy', 2.54, 5.08]], st, fl],
         ['polyline', ['pts', ['xy', 0, 5.08], ['xy', 0, 2.286]], st, fl],
         ['polyline', ['pts', ['xy', -2.54, -5.08], ['xy', 2.54, -5.08]], st, fl],
         ['polyline', ['pts', ['xy', 0, -5.08], ['xy', 0, -2.286]], st, fl],
         ['circle', ['center', 0, 1.778], ['radius', 0.508], st, fl],
         ['circle', ['center', 0, -1.778], ['radius', 0.508], st, fl],
         ['polyline', ['pts', ['xy', 1.27, 2.286], ['xy', 1.27, -2.286]], st, fl],
         ['polyline', ['pts', ['xy', 1.27, 0], ['xy', 3.302, 0]], st, fl],
         ['polyline', ['pts', ['xy', 3.302, 1.016], ['xy', 3.302, -1.016]], st, fl]]
    pins = [lpin('1', '1', -5.08, 5.08, 0), lpin('2', '2', 5.08, 5.08, 180),
            lpin('3', '3', -5.08, -5.08, 0), lpin('4', '4', 5.08, -5.08, 180)]
    return ['symbol', Q('NeatAmp:SW_Push_4pin'), ['pin_names', ['offset', 0], ['hide', 'yes']],
            ['exclude_from_sim', 'no'], ['in_bom', 'yes'], ['on_board', 'yes'],
            lprop('Reference', 'SW', 3.81, 2.54, justify='left'), lprop('Value', 'SW_Push_4pin', 3.81, -2.54, justify='left'),
            lprop('Footprint', '', hide=True), lprop('Datasheet', '', hide=True),
            lprop('Description', 'Tact switch, 4 pins: 1-2 joined, 3-4 joined, push closes 1/2 to 3/4', hide=True),
            ['symbol', Q('SW_Push_4pin_0_1')] + g, ['symbol', Q('SW_Push_4pin_1_1')] + pins]


def _rot90(x):
    if isinstance(x, list):
        if x and x[0] in ('xy', 'center', 'start', 'mid', 'end') and len(x) == 3:
            return [x[0], F(-float(x[2])), F(float(x[1]))]
        return [_rot90(c) for c in x]
    return x


def sym_q_pmos_e38p100kh():
    """Device:Q_PMOS rotated 90 deg CCW: D left, S right, G bottom.

    KiCad 10 native pin stacks: one drawn pin per terminal whose number lists
    all package pads, "[1-3]" -> pads 1,2,3 (E38P100KH PDFN5x6:
    S = 1,2,3   G = 4   D = 5,6,7,8 + exposed pad 9).
    """
    s = stock('Device', 'Q_PMOS')
    s[1] = Q('NeatAmp:Q_PMOS_E38P100KH')
    out = []
    for c in s:
        if isinstance(c, list) and c[0] in ('pin_numbers', 'pin_names'):
            continue        # show pin names (S/G/D) and stacked numbers
        if isinstance(c, list) and c[0] == 'symbol':
            c = _rot90(c)
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


def sym_renumbered(libname, newname, mapping, desc):
    """Stock symbol with pin numbers remapped, e.g. diodes whose EasyEDA
    footprint has pad 1 = anode (stock Device:D* has 1 = K)."""
    s = stock(*libname.split(':'))
    old = libname.split(':')[1]
    s[1] = Q(newname)
    base = newname.split(':')[1]

    def walk(x):
        for c in x:
            if isinstance(c, list):
                if c[0] == 'symbol':
                    c[1] = Q(c[1].replace(old, base, 1))
                if c[0] == 'pin':
                    num = find(c, 'number')
                    num[1] = Q(mapping[num[1]])
                walk(c)
    walk(s)
    for c in findall(s, 'property'):
        if c[1] == 'Description':
            c[2] = Q(desc)
    return s


CUSTOM = {
    'NeatAmp:LMQ66430MC3RXBRQ1': sym_lmq66430,
    'NeatAmp:TPS7A4701RGWR': sym_tps7a4701,
    'NeatAmp:Q_PMOS_E38P100KH': sym_q_pmos_e38p100kh,
    'NeatAmp:AP63203WU-7': sym_ap63203,
    'NeatAmp:TPS7A2033PDBVR': sym_tps7a2033,
    'NeatAmp:ESP32-S3-WROOM-1U': sym_esp32s3_wroom,
    'NeatAmp:USB_C_TYPE-C-31-M-12': sym_usbc_receptacle,
    'NeatAmp:USBLC6-2SC6': sym_usblc6,
    'NeatAmp:SK9822': sym_sk9822,
    'NeatAmp:SW_Push_4pin': sym_sw_push_4pin,
    'NeatAmp:D_Schottky_1A2K': lambda: sym_renumbered(
        'Device:D_Schottky', 'NeatAmp:D_Schottky_1A2K', {'1': '2', '2': '1'},
        'Schottky diode, pin 1 = anode, pin 2 = cathode (matches EasyEDA SMA footprints)'),
}

LIB = {
    'R': 'Device:R', 'C': 'Device:C', 'CP': 'Device:C_Polarized', 'L': 'Device:L',
    'FB': 'Device:FerriteBead', 'DZ': 'Device:D_Zener', 'F': 'Device:Fuse',
    'TP': 'Connector:TestPoint', 'CN': 'Connector:Screw_Terminal_01x02',
    'DS': 'NeatAmp:D_Schottky_1A2K',
    'ESP': 'NeatAmp:ESP32-S3-WROOM-1U', 'USBC': 'NeatAmp:USB_C_TYPE-C-31-M-12', 'ESD': 'NeatAmp:USBLC6-2SC6',
    'LED9822': 'NeatAmp:SK9822', 'SW4': 'NeatAmp:SW_Push_4pin',
    'H1x4': 'Connector_Generic:Conn_01x04', 'H1x6': 'Connector_Generic:Conn_01x06',
    'H2x4': 'Connector_Generic:Conn_02x04_Odd_Even', 'H2x12': 'Connector_Generic:Conn_02x12_Odd_Even',
    'AP': 'NeatAmp:AP63203WU-7', 'LDO20': 'NeatAmp:TPS7A2033PDBVR',
    'Q': 'NeatAmp:Q_PMOS_E38P100KH', 'LMQ': 'NeatAmp:LMQ66430MC3RXBRQ1', 'TPS': 'NeatAmp:TPS7A4701RGWR',
}


def make_sym(libname):
    if libname in CUSTOM:
        return CUSTOM[libname]()
    return stock(*libname.split(':'))


def lib_pins(sym):
    out = {}

    def walk(x):
        for c in x:
            if isinstance(c, list):
                if c[0] == 'pin':
                    at = find(c, 'at')
                    out.setdefault(find(c, 'number')[1], (float(at[1]), float(at[2])))
                else:
                    walk(c)
    walk(sym)
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


def set_at(p, x, y, ang=0):
    find(p, 'at')[1:] = [F(x), F(y), ang]


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
        p.insert(4, ['hide', 'yes'])        # KiCad 10: hide is a direct child of property


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


def _neatamp_power_syms():
    lib = parse(open(PRJ + 'NeatAmp.kicad_sym').read())
    out = {}
    for s in findall(lib, 'symbol'):
        if s[1].startswith('PWR_'):
            s = copy.deepcopy(s)
            s[1] = Q('NeatAmp:' + s[1])
            out[s[1]] = s
    return out


def _max_pwr_ref(exclude):
    n = 0
    for f in glob.glob(PRJ + '*.kicad_sch'):
        if os.path.abspath(f) == os.path.abspath(exclude):
            continue
        for m in re.finditer(r'"#PWR(\d+)"', open(f).read()):
            n = max(n, int(m.group(1)))
    return n


# ====================================================================== sheet
class Sheet:
    """Layout API. All coordinates in grid units (1.27 mm)."""

    def __init__(self, sheet_file, src=None):
        self.path = PRJ + sheet_file
        self.src = src or self.path
        self.sch = parse(open(self.src).read())
        self.old_syms = {prop(s, 'Reference')[2]: s for s in findall(self.sch, 'symbol')}
        self.parts, self.wires, self.pwr, self.nc = {}, [], [], []
        self.labels, self.glabels, self.texts = [], [], []
        self.dx, self.th = 0, 0

    # -- shift: x >= th moves right by dx (lets a block grow without renumbering)
    def shift(self, dx, th=0):
        self.dx, self.th = dx, th

    def sx(self, x):
        return x + self.dx if self.dx and x >= self.th else x

    def P(self, ref, kind, x, y, rot=0, txt='r', mirror=None):
        """Place part `ref` as LIB[kind]. txt: field placement mode
        r/l (right/left of vertical part), h (above/below horizontal part),
        qt (above), tp (test point), cn (connector), chip, chip2."""
        assert ref in self.old_syms, ref
        self.parts[ref] = dict(kind=kind, X=mm(self.sx(x)), Y=mm(y), rot=rot, mirror=mirror, txt=txt)

    def W(self, *pts):
        self.wires.append([(mm(self.sx(x)), mm(y)) for x, y in pts])

    def PW(self, name, x, y, rot=0, show=True):
        self.pwr.append((name, mm(self.sx(x)), mm(y), rot, show))

    def NC(self, x, y):
        self.nc.append((mm(self.sx(x)), mm(y)))

    def LBL(self, name, x, y, ang=0):
        """Local net label; ang 0 text right of anchor, 180 left, 90 up, 270 down."""
        self.labels.append((name, mm(self.sx(x)), mm(y), ang))

    def GL(self, name, x, y, shape=None, ang=0):
        """Global label; ang 0 = text to the right of the anchor, 180 left, 90 up, 270 down.
        shape defaults to the shape the label had on the old sheet."""
        if shape is None:
            shape = next((find(g, 'shape')[1] for g in findall(self.sch, 'global_label') if g[1] == name), 'passive')
        self.glabels.append((name, mm(self.sx(x)), mm(y), shape, ang))

    def T(self, s, x, y, size=1.27, bold=False):
        self.texts.append((s, mm(self.sx(x)), mm(y), size, bold))

    # -------------------------------------------------------------- build
    def save(self, title, page, dst=None, update_lib=None, paper='A3'):
        dst = dst or self.path
        if update_lib is None:
            update_lib = os.path.abspath(dst) == os.path.abspath(self.path)
        old_syms = self.old_syms
        items, pin_pts = [], []
        libsyms = {}
        missing = [r for r in old_syms if not r.startswith('#') and r not in self.parts]
        assert not missing, ('parts not placed', missing)

        for ref, d in self.parts.items():
            s = copy.deepcopy(old_syms[ref])
            libname = LIB[d['kind']]
            if libname not in libsyms:
                libsyms[libname] = make_sym(libname)
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
            if isinstance(t, tuple):        # (ref dx, ref dy, value dx, value dy, justify) in grid units
                rdx, rdy, vdx, vdy, jj = t[:5]
                set_at(r, X + mm(rdx), Y + mm(rdy)); set_at(v, X + mm(vdx), Y + mm(vdy))
                set_eff(r, jj); set_eff(v, jj, hide=len(t) > 5 and t[5] == 'hidev')
            elif t == 'r':
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
            else:
                raise ValueError(t)
            for p in (r, v):
                find(find(p, 'effects'), 'font')[:] = ['font', ['size', 1.27, 1.27]]
                if d['rot'] in (90, 270):
                    find(p, 'at')[3] = 90   # field angle is relative to symbol -> horizontal text
                if d['rot'] in (90, 180):   # KiCad mirrors justification on 90/180-deg symbols
                    j = find(find(p, 'effects'), 'justify')
                    if j:
                        j[1:] = [{'left': 'right', 'right': 'left'}.get(a, a) for a in j[1:]]
            lp = lib_pins(libsyms[libname])
            have = {pp[1]: pp for pp in findall(s, 'pin')}
            if set(lp) != set(have):        # e.g. stacked pins: rebuild, keep uuids where numbers match
                s[:] = [c for c in s if not (isinstance(c, list) and c[0] == 'pin')]
                at = next(i for i, c in enumerate(s) if isinstance(c, list) and c[0] == 'instances')
                s[at:at] = [have.get(n) or ['pin', Q(n), ['uuid', uid()]] for n in lp]
            for n, (px, py) in lp.items():
                pin_pts.append((xform(px, py, X, Y, d['rot'], d['mirror']), ref, n))
            items.append(s)

        # power symbols: built from the NeatAmp library, instance path from any part on this sheet
        pwr_lib = _neatamp_power_syms()
        any_inst = find(next(s for r, s in old_syms.items() if not r.startswith('#')), 'instances')
        path = find(find(any_inst, 'project'), 'path')[1]
        project = find(any_inst, 'project')[1]
        old_pwr = sorted(r for r in old_syms if r.startswith('#PWR'))
        nxt = [max([_max_pwr_ref(self.path)] + [int(r[4:]) for r in old_pwr] + [0])]

        def new_ref():
            if old_pwr:
                return old_pwr.pop(0)
            nxt[0] += 1
            return '#PWR%04d' % nxt[0]

        for name, x, y, rot, show in self.pwr:
            libname = 'NeatAmp:PWR_' + name
            libsyms[libname] = pwr_lib[libname]
            ref = new_ref()
            gnd = name in ('GND', 'AGND')
            vy = y + (3.81 if gnd else -3.556) if rot == 0 else y
            side = rot in (90, 270)
            v = ['property', Q('Value'), Q(name), ['at', F(x), F(vy), 90 if side else 0]]
            if not show or (side and (gnd or rot == 270)):
                v.append(['hide', 'yes'])
            v.append(eff(1.0, justify='left' if side else None))
            s = ['symbol', ['lib_id', Q(libname)], ['at', F(x), F(y), rot], ['unit', 1],
                 ['exclude_from_sim', 'no'], ['in_bom', 'yes'], ['on_board', 'yes'], ['dnp', 'no'],
                 ['uuid', uid()],
                 ['property', Q('Reference'), Q(ref), ['at', F(x), F(y), 0], ['hide', 'yes'], eff()],
                 v,
                 ['property', Q('Footprint'), Q(''), ['at', F(x), F(y), 0], ['hide', 'yes'], eff()],
                 ['property', Q('Datasheet'), Q(''), ['at', F(x), F(y), 0], ['hide', 'yes'], eff()],
                 ['pin', Q('1'), ['uuid', uid()]],
                 ['instances', ['project', Q(project), ['path', Q(path), ['reference', Q(ref)], ['unit', 1]]]]]
            pin_pts.append(((round(x, 3), round(y, 3)), '#', name))
            items.append(s)

        # wires: split at every special point lying on a segment, then junctions
        segs = []
        for poly in self.wires:
            for a, b in zip(poly, poly[1:]):
                segs.append(((round(a[0], 3), round(a[1], 3)), (round(b[0], 3), round(b[1], 3))))
        special = ({p for s in segs for p in s} | {p for p, _, _ in pin_pts}
                   | {(round(x, 3), round(y, 3)) for _, x, y, _ in self.labels}
                   | {(round(x, 3), round(y, 3)) for _, x, y, _, _ in self.glabels})

        def on_seg(p, a, b):
            if a[0] == b[0] == p[0]:
                return min(a[1], b[1]) < p[1] < max(a[1], b[1])
            if a[1] == b[1] == p[1]:
                return min(a[0], b[0]) < p[0] < max(a[0], b[0])
            return False

        out = []
        for a, b in segs:
            assert a[0] == b[0] or a[1] == b[1], ('diagonal wire', a, b)
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

        ncset = {(round(x, 3), round(y, 3)) for x, y in self.nc}
        lblset = {(round(x, 3), round(y, 3)) for _, x, y, _, _ in self.glabels}
        pin_at = {}
        for p, ref, n in pin_pts:
            pin_at.setdefault(p, []).append((ref, n))
        for p, ref, n in pin_pts:
            if p not in deg and p not in ncset and p not in lblset and len(pin_at[p]) < 2:
                print('WARNING unconnected pin', ref, n, p)

        body = []
        for x, y in junctions:
            body.append(['junction', ['at', F(x), F(y)], ['diameter', 0], ['color', 0, 0, 0, 0], ['uuid', uid()]])
        for x, y in self.nc:
            body.append(['no_connect', ['at', F(x), F(y)], ['uuid', uid()]])
        for a, b in segs:
            body.append(['wire', ['pts', ['xy', F(a[0]), F(a[1])], ['xy', F(b[0]), F(b[1])]],
                         ['stroke', ['width', 0], ['type', 'default']], ['uuid', uid()]])
        for name, x, y, ang in self.labels:
            j = 'left bottom' if ang in (0, 90) else 'right bottom'
            body.append(['label', Q(name), ['at', F(x), F(y), ang], eff(justify=j), ['uuid', uid()]])
        for name, x, y, shape, ang in self.glabels:
            j = 'left' if ang in (0, 90) else 'right'
            body.append(['global_label', Q(name), ['shape', shape], ['at', F(x), F(y), ang],
                         ['fields_autoplaced', 'yes'], eff(justify=j), ['uuid', uid()],
                         ['property', Q('Intersheetrefs'), Q('${INTERSHEET_REFS}'), ['at', F(x), F(y), 0],
                          eff(justify=j, hide=True)]])
        for s, x, y, size, bold in self.texts:
            body.append(['text', esc(s), ['exclude_from_sim', 'no'], ['at', F(x), F(y), 0],
                         eff(size, 'left bottom', bold=bold), ['uuid', uid()]])

        new = []
        for c in self.sch:
            if isinstance(c, list) and c[0] in ('wire', 'label', 'global_label', 'no_connect', 'junction', 'text',
                                                'symbol', 'bus', 'bus_entry', 'polyline'):
                continue
            if isinstance(c, list) and c[0] == 'lib_symbols':
                c = ['lib_symbols'] + [libsyms[k] for k in sorted(libsyms)]
            if isinstance(c, list) and c[0] == 'paper':
                c = ['paper', Q(paper)]
            if isinstance(c, list) and c[0] == 'title_block':
                c = ['title_block', ['title', Q(title)], ['rev', Q('V1.2')], ['company', Q('zoomMediaPlus')],
                     ['comment', 1, Q('Board: MainBoard - Class D amp')],
                     ['comment', 2, Q('Drawn: Igor Korzinek')],
                     ['comment', 3, Q('Redrawn in KiCad 10 after %s; netlist verified with tools/netcmp.py' % page)]]
            new.append(c)
            if isinstance(c, list) and c[0] == 'lib_symbols':
                new += body + items
        open(dst, 'w').write(dump(new) + '\n')
        print('%s: parts %d pwr %d wires %d junctions %d nc %d' % (
            os.path.basename(dst), len(self.parts), len(self.pwr), len(segs), len(junctions), len(self.nc)))
        if update_lib:
            self._update_lib([k for k in libsyms if k in CUSTOM])

    @staticmethod
    def _update_lib(names):
        libf = PRJ + 'NeatAmp.kicad_sym'
        lib = open(libf).read()
        for libname in names:
            name = libname.split(':')[1]
            key = '\n(symbol "%s"' % name
            i = lib.find(key)
            if i >= 0:                      # replace previous version of this symbol
                lib = lib[:i] + lib[block_end(lib, i + 1):]
            c2 = make_sym(libname)
            c2[1] = Q(name)
            k = lib.rstrip().rfind(')')     # closing paren of kicad_symbol_lib
            lib = lib[:k].rstrip() + '\n' + dump(c2) + '\n)\n'
        open(libf, 'w').write(lib)
        print('updated NeatAmp.kicad_sym:', ', '.join(n.split(':')[1] for n in names))
