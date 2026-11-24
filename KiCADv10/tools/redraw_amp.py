"""Redraw Amplifier.kicad_sch after Schematic.pdf p.5 (layout only; engine in schgen.py).

NOTE (2026-11-17): the project sheet was hand-edited in KiCad after generation (blocks moved,
DAC filter wired directly, C63 rotated). Re-running this script on the project sheet would
discard those edits, so it refuses to unless --force is given.

U12 (TAS3251) uses a 3-grid pin pitch: series parts sit right at the pins,
everything else is grouped in blocks joined by the existing net labels.
Usage: python3 tools/redraw_amp.py [src.kicad_sch [dst.kicad_sch]]
Grid unit u = 1.27 mm.
"""
import sys

from schgen import Sheet

args = [x for x in sys.argv[1:] if x != '--force']
if len(args) < 2 and '--force' not in sys.argv:
    sys.exit('refusing to overwrite the hand-edited Amplifier.kicad_sch: give src and dst, or --force')
s = Sheet('Amplifier.kicad_sch', src=args[0] if args else None)
P, W, PW, NC, LBL, GL, T = s.P, s.W, s.PW, s.NC, s.LBL, s.GL, s.T

UX, UY = 160, 112                       # U12 origin
LX, RX = UX - 17, UX + 17               # pin ends: left 143, right 177


def ly(k):                              # left pin k (1..28)
    return UY - 40 + 3 * (k - 1)


def ry(n):                              # right pin n (29..56)
    return UY - 40 + 3 * (56 - n)


def lbl_left(name, x, y, stub=4, glob=False):
    W((x, y), (x - stub, y))
    (GL if glob else LBL)(name, x - stub, y, ang=180)


def lbl_right(name, x, y, stub=4, glob=False):
    W((x, y), (x + stub, y))
    (GL if glob else LBL)(name, x + stub, y, ang=0)


def rail_right(name, y):
    """Power pin on the right edge: symbol pointing right, name as text."""
    PW(name, RX, y, 270, show=False)
    T(name, RX + 3, y + 0.5, 1.0)


# ====================================================== TAS3251
P('U12', 'TAS', UX, UY, 0, txt=(-15, -43.5, -11, -43.5, 'left'))

# ---- left side
for k, (r, net) in zip(range(1, 5), [('R23', 'C56_P2'), ('R24', 'C56_P1'), ('R25', 'C58_P1'), ('R26', 'C57_P1')]):
    y = ly(k)                                            # DAC_OUT -> 499R (pin2 at the U12 side)
    P(r, 'R', 130, y, 90, txt=(-4, -1.7, 0, -1.7, 'left'))
    W((133, y), (LX, y))
    lbl_left(net, 127, y)
lbl_left('U12_CPVSS', LX, ly(5))
P('C64', 'C', 136, ly(7), 0, txt='l')                    # flying cap CN (pin 6) / CP (pin 8)
W((LX, ly(6)), (136, ly(6))); W((LX, ly(8)), (136, ly(8)))
LBL('U12_CP', 137, ly(8))
PW('GND', LX, ly(7), 270, show=False)
PW('3.3V', LX, ly(9), 90)                                # DAC_DVDD
PW('GND', LX, ly(10), 270, show=False)                   # DGND
P('C71', 'C', 136, ly(11), 90, txt=(-12, 0, -8, 0, 'right'))   # DVDD_REG cap, pin2 at U12
W((139, ly(11)), (LX, ly(11))); PW('GND', 133, ly(11), 270, show=False)
PW('12V_GVDD', LX, ly(12), 90)                           # GVDD_A
PW('GND', LX, ly(13), 270, show=False)
PW('GND', LX, ly(14), 270, show=False)                   # MODE
lbl_left('INA+', LX, ly(15), glob=True)
lbl_left('INA-', LX, ly(16), glob=True)
lbl_left('U12_OC_ADJ', LX, ly(17))
lbl_left('U12_FREQ_ADJ', LX, ly(18))
lbl_left('U12_OSC_IOM', LX, ly(19))
lbl_left('U12_OSC_IOP', LX, ly(20))
lbl_left('U12_DVDD', LX, ly(21))
PW('GND', LX, ly(22), 270, show=False)
lbl_left('U12_AVDD', LX, ly(23))
P('C81', 'C', 136, ly(24), 90, txt=(-13, 0, -8, 0, 'right'))   # C_START
W((139, ly(24)), (LX, ly(24))); PW('GND', 133, ly(24), 270, show=False)
lbl_left('INB+', LX, ly(25), glob=True)
lbl_left('INB-', LX, ly(26), glob=True)
lbl_left('TAS_RESET', LX, ly(27), glob=True)
lbl_left('TAS_FAULT', LX, ly(28), glob=True)

# ---- right side
W((RX, ry(56)), (RX + 3, ry(56)), (RX + 3, ry(56) - 3))  # DAC_AVDD
PW('+3.3VA', RX + 3, ry(56) - 3)
PW('AGND', RX, ry(55), 90, show=False); T('AGND', RX + 3, ry(55) + 0.5, 1.0)
lbl_right('SDA', RX, ry(54), glob=True)
lbl_right('SCL', RX, ry(53), glob=True)
rail_right('3.3V', ry(52))                               # XPU
for n, r, lab, net in [(51, 'R48', None, 'SDOUT'), (50, 'R31', 'U12_MCLK', 'MCLK'), (49, 'R32', 'U12_SCLK', 'SCLK'),
                       (48, 'R33', 'U12_SDIN', 'SDIN'), (47, 'R34', 'U12_LRCK', 'LRCK')]:
    y = ry(n)                                            # 22R series, pin1 at the U12 side
    P(r, 'R', 190, y, 90, txt=(-3, -1.7, 1, -1.7, 'left'))
    W((RX, y), (187, y))
    if lab:
        LBL(lab, RX + 1, y)
    lbl_right(net, 193, y, glob=True)
lbl_right('TAS_ADR', RX, ry(46), glob=True)
lbl_right('TAS_MUTE', RX, ry(45), glob=True)
for n, c, net, cx in [(44, 'C72', 'OUTA+', 190), (43, 'C73', 'OUTA-', 208),
                      (32, 'C83', 'OUTB+', 190), (31, 'C82', 'OUTB-', 208)]:
    y = ry(n)                                            # bootstrap caps, pin2 at the U12 side
    P(c, 'C', cx, y, 270, txt=(-3, -2.2, 1, -2.2, 'left'))
    W((RX, y), (cx - 3, y))
    lbl_right(net, cx + 3, y, glob=True)
for n in (42, 38, 37, 33):
    PW('GND', RX, ry(n), 90, show=False)
lbl_right('OUTA+', RX, ry(41), glob=True)
rail_right('PVDD', ry(40))
lbl_right('OUTA-', RX, ry(39), glob=True)
lbl_right('OUTB+', RX, ry(36), glob=True)
rail_right('PVDD', ry(35))
lbl_right('OUTB-', RX, ry(34), glob=True)
rail_right('12V_GVDD', ry(30))
lbl_right('TAS_CLIP', RX, ry(29), glob=True)

# ====================================================== DAC output filter -> amplifier inputs (top left)
T('DAC OUTPUT FILTER -> POWER STAGE INPUTS', 16, 54, 1.8, True)
for (p_net, n_net, pr, nr, cb, cp, cn, gp, gn, y0, rot_cb) in [
        ('C56_P2', 'C56_P1', 'R30', 'R29', 'C56', 'C60', 'C59', 'INB+', 'INB-', 60, 180),
        ('C57_P1', 'C58_P1', 'R27', 'R28', 'C63', 'C57', 'C58', 'INA+', 'INA-', 88, 0)]:
    y1 = y0 + 14
    for y, net, r, c, g in [(y0, p_net, pr, cp, gp), (y1, n_net, nr, cn, gn)]:
        LBL(net, 40, y, ang=180)
        W((40, y), (69, y))
        P(r, 'R', 58, y + 3, 180)                        # 100k to AGND, pin2 on the line
        PW('AGND', 58, y + 6)
        P(c, 'C', 72, y, 90, txt='h')                    # 10uF coupling, pin1 on the line
        W((75, y), (79, y)); GL(g, 79, y, ang=0)
    P(cb, 'C', 48, y0 + 7, rot_cb)                       # 1nF across the pair
    W((48, y0), (48, y0 + 4)); W((48, y0 + 10), (48, y1))
T('DAC_OUT -> 499 Ω + 1 nF (differential) -> 10 µF -> SPK_IN', 16, 116)

# ====================================================== TAS3251 supply decoupling (left)
T('TAS3251 SUPPLY DECOUPLING', 16, 122, 1.8, True)
PW('+3.3VA', 18, 128); W((18, 128), (30, 128))
P('C61', 'C', 22, 131, 180); P('C62', 'C', 30, 131)
PW('AGND', 22, 134); PW('AGND', 30, 134)
PW('3.3V', 42, 128); W((42, 128), (54, 128))
P('C67', 'C', 46, 131, 180); P('C68', 'C', 54, 131)
PW('GND', 46, 134); PW('GND', 54, 134)
PW('12V_GVDD', 66, 128); W((66, 128), (84, 128))
P('C69', 'C', 70, 131, 180); P('C87', 'C', 78, 131, 180)
P('TP18', 'TP', 84, 128, 0, txt='tp')
PW('GND', 70, 134); PW('GND', 78, 134)
LBL('U12_CPVSS', 16, 146); W((16, 146), (34, 146))
P('C65', 'C', 26, 149, 180); P('C66', 'C', 34, 149, 180)
PW('GND', 26, 152); PW('GND', 34, 152)
LBL('U12_DVDD', 46, 146); W((46, 146), (60, 146))
P('C78', 'C', 56, 149, 180); P('TP23', 'TP', 60, 146, 0, txt='tp')
PW('GND', 56, 152)
LBL('U12_AVDD', 70, 146); W((70, 146), (84, 146))
P('C80', 'C', 80, 149, 180); P('TP25', 'TP', 84, 146, 0, txt='tp')
PW('GND', 80, 152)

# ====================================================== pull-ups / pull-downs (top right)
T('CONTROL LINES: I2C pull-ups 6.8k, status pull-ups 10k', 214, 58, 1.27, True)
PW('3.3V', 216, 66); W((216, 66), (260, 66))
for x, r, rot, net in [(220, 'R21', 0, 'SDA'), (230, 'R22', 180, 'SCL'), (240, 'R43', 180, 'TAS_CLIP'),
                       (250, 'R44', 180, 'TAS_FAULT'), (260, 'R45', 180, 'TAS_RESET')]:
    P(r, 'R', x, 69, rot)                                # 3.3V on top
    W((x, 72), (x, 79)); GL(net, x, 79, ang=270)
P('TP28', 'TP', 250, 76, 270, txt=(3, 0, 0, 0, 'left', 'hidev'))
P('TP29', 'TP', 260, 76, 270, txt=(3, 0, 0, 0, 'left', 'hidev'))
for x, r, rot, net in [(274, 'R35', 180, 'TAS_MUTE'), (284, 'R42', 0, 'TAS_ADR')]:
    GL(net, x, 64, ang=90); W((x, 64), (x, 69))         # pull-downs to GND
    P(r, 'R', x, 72, rot)
    PW('GND', x, 75)
P('TP19', 'TP', 274, 66, 270, txt=(3, 0, 0, 0, 'left', 'hidev'))

# ---- fault / clip LEDs (open-drain outputs pull the cathode low)
for x, r, led, kind, lab, net in [(296, 'R46', 'LED1', 'LED', 'LED1_P2', 'TAS_FAULT'),
                                  (310, 'R47', 'LED2', 'LED', 'LED2_P1', 'TAS_CLIP')]:
    PW('3.3V', x, 64)
    P(r, 'R', x, 67, 180)                                # pin2 (x,64)=3.3V, pin1 (x,70)
    W((x, 70), (x, 71)); LBL(lab, x, 71)
    P(led, kind, x, 74, 90)                              # anode (x,71) top, cathode (x,77)
    W((x, 77), (x, 80)); GL(net, x, 80, ang=270)
T('LED1 red = FAULT\nLED2 yellow = CLIP/OTW', 292, 96)

# ====================================================== I2S input connector + test points
T('I2S INPUT', 214, 92, 1.27, True)
P('U11', 'H1x6', 232, 102, 0, txt=(3, -3, 3, -1, 'left'))   # pins x=228: 1 GND 98, 2 +5V 100, 3..6 at 102..108
PW('GND', 228, 98, 270, show=False)
PW('+5V', 228, 100, 90)
for k, net in enumerate(['MCLK', 'LRCK', 'SCLK', 'SDIN']):
    lbl_left(net, 228, 102 + 2 * k, glob=True)
for k, (tp, net) in enumerate([('TP14', 'U12_MCLK'), ('TP15', 'U12_SCLK'), ('TP16', 'U12_SDIN'), ('TP17', 'U12_LRCK')]):
    x = 244 + 16 * k
    LBL(net, x, 108); W((x, 108), (x + 11, 108))
    P(tp, 'TP', x + 11, 108, 0, txt='tp')

# ====================================================== PVDD bulk + local decoupling
T('PVDD: bulk + local decoupling (A: C74-C76, B: C84-C86)', 214, 116, 1.27, True)
PVDD_END = 282
PW('PVDD', 214, 122); W((214, 122), (PVDD_END, 122))
caps = [('C54', 'CP', 0, 220), ('C55', 'CP', 0, 230), ('C74', 'C', 0, 240), ('C75', 'C', 0, 248), ('C76', 'C', 0, 256),
        ('C84', 'C', 180, 266), ('C85', 'C', 180, 274), ('C86', 'C', 180, 282)]
for r, kind, rot, x in caps:
    P(r, kind, x, 125, rot)
    W((x, 128), (x, 132))
W((220, 132), (282, 132))
PW('GND', 250, 132)

# ====================================================== FREQ_ADJ jumper (U13) + oscillator sync header (H3)
T('PWM FREQUENCY SELECT (fit one jumper on U13)', 200, 142, 1.27, True)
P('U13', 'H2x4', 232, 152, 0, txt=(-2, -5, 2, -5, 'left'))  # odd x=228 rows 150..156, even x=238
PW('3.3V', 228, 150, 90)
W((228, 156), (226, 156), (226, 160)); P('R41', 'R', 226, 163, 180)
W((228, 154), (216, 154), (216, 160)); P('R37', 'R', 216, 163, 180)
W((228, 152), (206, 152), (206, 160)); P('R38', 'R', 206, 163, 180, txt='l')
for x in (206, 216, 226):
    PW('GND', x, 166)
for y in (150, 152, 154, 156):
    W((238, y), (240, y))
W((240, 150), (240, 156)); W((240, 150), (244, 150))
LBL('U12_FREQ_ADJ', 244, 150)
T('U13 pair 3-4 = 768 kHz PWM (default, see README)', 200, 172)

T('H3: oscillator sync (OSC_IOM/OSC_IOP) + SDOUT', 258, 142, 1.27, True)
P('H3', 'H1x4', 290, 152, 0, txt=(3, -2, 3, 0, 'left'))   # pins x=286: 1 (150) 2 (152) 3 (154) 4 (156)
P('R39', 'R', 280, 150, 270, txt=(-3, -1.3, 1, -1.3, 'left'))   # pin1 (283,150)=H3.1 pin2 (277,150)
P('R40', 'R', 280, 154, 270, txt=(-3, 1.8, 1, 1.8, 'left'))
W((283, 150), (286, 150)); W((283, 154), (286, 154))
lbl_left('U12_OSC_IOM', 277, 150, stub=3)
lbl_left('U12_OSC_IOP', 277, 154, stub=3)
PW('GND', 286, 152, 270, show=False)
W((286, 156), (284, 156), (284, 160), (266, 160)); GL('SDOUT', 266, 160, ang=180)

T('OVER-CURRENT ADJUST', 290, 166, 1.27, True)
LBL('U12_OC_ADJ', 290, 172); W((290, 172), (304, 172))
P('R36', 'R', 300, 175, 180)                             # pin2 (300,172)=OC_ADJ
PW('GND', 300, 178)
P('TP21', 'TP', 304, 172, 0, txt='tp')

# ====================================================== AGND / GND star point
P('R49', 'R', 216, 188, 90, txt='h')                     # pin1 (213,188)=AGND pin2 (219,188)=GND
W((210, 188), (213, 188)); PW('AGND', 210, 188)
W((219, 188), (222, 188)); PW('GND', 222, 188)
T('AGND - GND star point (0 Ω)', 204, 182)

# ====================================================== output LC filters (bottom left)
T('OUTPUT LC FILTERS', 16, 158, 1.8, True)
T('Only 1 L of this 2 is needed (alternative footprints XGL1712-103 / MA5172-AE, see review P1-1)', 44, 161)
chans = [('OUTA+', 'A+', 'L7', 'L8', ['C88', 'C89', 'C90', 'C91'], 'TP20', 166),
         ('OUTA-', 'A-', 'L9', 'L10', ['C92', 'C93', 'C94', 'C95'], 'TP22', 180),
         ('OUTB+', 'B+', 'L11', 'L12', ['C96', 'C97', 'C98', 'C99'], 'TP24', 196),
         ('OUTB-', 'B-', 'L13', 'L14', ['C100', 'C101', 'C102', 'C103'], 'TP26', 210)]
for out, node, la, lb, cs, tp, y in chans:
    GL(out, 22, y, ang=180)
    W((22, y), (29, y)); W((27, y), (27, y + 4), (29, y + 4))
    P(tp, 'TP', 24, y, 0, txt='tp')
    P(la, 'L', 32, y, 90, txt=(-3, -2, 1, -2, 'left'))   # pin1 (29,y)=OUT  pin2 (35,y)=node
    P(lb, 'L', 32, y + 4, 90, txt=(-3, 2.2, 1, 2.2, 'left'))
    W((35, y + 4), (37, y + 4), (37, y)); W((35, y), (84, y))
    W((82, y), (82, y - 2)); GL(node, 82, y - 2, ang=90)
    for i, c in enumerate(cs):
        x = 48 + 9 * i
        P(c, 'C', x, y + 3, 180)                         # pin2 on the node line
        W((x, y + 6), (x, y + 8))
    W((48, y + 8), (75, y + 8)); PW('GND', 62, y + 8)
# speaker terminals: pin2 = +, pin1 = -  (mirrored so pin 2 is on top)
P('CN2', 'CN', 98, 174, 0, txt=(2, -4, 2, 3, 'left'), mirror='x')    # pin2 (94,172) pin1 (94,174)
W((84, 166), (88, 166), (88, 172), (94, 172)); W((84, 180), (86, 180), (86, 174), (94, 174))
P('CN3', 'CN', 98, 204, 0, txt=(2, -4, 2, 3, 'left'), mirror='x')
W((84, 196), (88, 196), (88, 202), (94, 202)); W((84, 210), (86, 210), (86, 204), (94, 204))
T('Speaker A (2 = +, 1 = -)', 100, 181); T('Speaker B (2 = +, 1 = -)', 100, 211)

s.save(title='Amplifier', page='Schematic.pdf p.5', dst=args[1] if len(args) > 1 else None)
