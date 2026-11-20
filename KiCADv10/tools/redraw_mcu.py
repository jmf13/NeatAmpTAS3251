"""Redraw Microcontroler.kicad_sch after Schematic.pdf p.4 (layout only; engine in schgen.py).

NOTE (2026-11-17): the project sheet was hand-edited in KiCad after generation (D4, R19/R20,
SW1/EN block, H2, U10, SW2 moved and partly wired directly). Re-running this script on the
project sheet would discard those edits, so it refuses to unless --force is given.

U6 (ESP32-S3) pins connect through short stubs and the existing net labels,
so each block reads on its own. Usage:
    python3 tools/redraw_mcu.py [src.kicad_sch [dst.kicad_sch]]
Grid unit u = 1.27 mm.
"""
import sys

from schgen import Sheet

args = [x for x in sys.argv[1:] if x != '--force']
if len(args) < 2 and '--force' not in sys.argv:
    sys.exit('refusing to overwrite the hand-edited Microcontroler.kicad_sch: give src and dst, or --force')
s = Sheet('Microcontroler.kicad_sch', src=args[0] if args else None)
P, W, PW, NC, LBL, GL, T = s.P, s.W, s.PW, s.NC, s.LBL, s.GL, s.T


def lbl_left(name, x, y, stub=4, glob=False):
    """Stub from a right-facing pin end (x, y) to the left, label text to the left."""
    W((x, y), (x - stub, y))
    (GL if glob else LBL)(name, x - stub, y, ang=180)


def lbl_right(name, x, y, stub=4, glob=False):
    W((x, y), (x + stub, y))
    (GL if glob else LBL)(name, x + stub, y, ang=0)


def lbl_down(name, x, y, stub=3, glob=False):
    W((x, y), (x, y + stub))
    (GL if glob else LBL)(name, x, y + stub, ang=270)


# ====================================================== USB-C input (top left)
P('USBC1', 'USBC', 28, 50, 0, txt=(-6, -16, -6, -14, 'left'))
# right pins x=38: VBUS 39/41, CC1 44, CC2 46, DP1 50, DP2 52, DN1 54, DN2 56, SBU1 59, SBU2 61
# bottom y=69: GND x=27/30, SHIELD x=24
W((38, 39), (40, 39)); W((38, 41), (40, 41), (40, 39), (40, 30), (57, 30))   # VBUS -> VBUS1 rail y=30
PW('VBUS1', 44, 30)
P('C107', 'C', 50, 33, 180)                              # pin2 (50,30)=VBUS1
PW('GND', 50, 36)
P('L6', 'FB', 60, 30, 270, txt=(0, -5, 0, -3, None))                      # pin2 (57,30)=VBUS1 pin1 (63,30)
W((63, 30), (77, 30))
LBL('C46_P2', 64, 30)
P('C46', 'C', 72, 33, 180)
PW('GND', 72, 36)
P('D3', 'DS', 80, 30, 180, txt=(0, -5, 0, -3, None))                      # A (77,30) K (83,30)
W((83, 30), (100, 30))
P('C44', 'C', 88, 33)                                    # pin1 (88,30)=+5V
PW('GND', 88, 36)
P('R11', 'R', 96, 33, 180)                               # pin2 (96,30)=+5V
PW('GND', 96, 36)
PW('+5V', 100, 30)
# CC pull-downs 5.1k
P('R13', 'R', 44, 44, 90, txt=(-4, -1.5, 0, -1.5, 'left'))   # pin1 (41,44)=CC1
P('R12', 'R', 44, 46, 90, txt=(-4, 2.2, 0, 2.2, 'left'))     # pin1 (41,46)=CC2
W((38, 44), (41, 44)); W((38, 46), (41, 46))
W((47, 44), (50, 44), (50, 46), (47, 46))
PW('GND', 50, 45, 90, show=False)
# DP / DN: both receptacle rows joined, ESD array D4 between connector and MCU
W((38, 50), (40, 50), (40, 52), (38, 52)); W((40, 50), (44, 50))
W((38, 54), (40, 54), (40, 56), (38, 56)); W((40, 54), (44, 54))
GL('DP', 44, 50, ang=0); GL('DN', 44, 54, ang=0)
NC(38, 59); NC(38, 61)
P('D4', 'ESD', 72, 52, 0, txt=(-5, -6, 7, 7, 'left'))   # IO1 (65,50)/(79,50) IO2 (65,54)/(79,54) VBUS (72,45) GND (72,59)
W((65, 50), (62, 50)); GL('DP', 62, 50, ang=180)
W((65, 54), (62, 54)); GL('DN', 62, 54, ang=180)
PW('VBUS1', 72, 45)
PW('GND', 72, 59)
lbl_right('USBD+', 79, 50, glob=True)
lbl_right('USBD-', 79, 54, glob=True)
# GND + shield
W((27, 69), (27, 70), (30, 70), (30, 69))
PW('GND', 28, 70)
W((24, 69), (24, 76), (44, 76))
LBL('USBC1_EH', 25, 76)
P('C45', 'C', 36, 79, 180)                               # pin2 (36,76)=EH
P('R14', 'R', 44, 79, 180)
PW('GND', 36, 82); PW('GND', 44, 82)

# ====================================================== ESP32-S3 module U6
P('U6', 'ESP', 160, 120, 0, txt=(-19, -18, -15, -18, 'left'))
# left x=139, rows 107..133 (pin n at 107+2(n-1)); right x=181 (pin 40 at 107 .. pin 27 at 133)
# bottom y=139, pins 15..26 at x=149..171; top pin 41 at (160,102)
PW('GND', 139, 107, 270, show=False)                     # 1 GND
PW('3.3V', 139, 109, 90)                                 # 2 3V3
lbl_left('U6_EN', 139, 111)
for n, io in zip(range(4, 13), ['IO4', 'IO5', 'IO6', 'IO7', 'IO15', 'IO16', 'IO17', 'IO18', 'IO8']):
    lbl_left('U6_' + io, 139, 107 + 2 * (n - 1))
P('R16', 'R', 118, 131, 270, txt=(-3, -2, 1, -2, 'left'))    # pin1 (121,131)=IO19 pin2 (115,131)
P('R15', 'R', 118, 133, 90, txt=(-3, 2.5, 1, 2.5, 'left'))   # pin2 (121,133)=IO20 pin1 (115,133)
W((139, 131), (121, 131)); W((139, 133), (121, 133))
W((115, 131), (112, 131)); GL('USBD-', 112, 131, ang=180)
W((115, 133), (112, 133)); GL('USBD+', 112, 133, ang=180)
PW('GND', 160, 102, 180, show=False)                     # 41 GND (top)
PW('GND', 181, 107, 90, show=False)                      # 40 GND
right = {39: 'U6_IO1', 38: 'U6_IO2', 37: 'TXD', 36: 'RXD', 35: 'U6_IO42', 34: 'U6_IO41', 33: 'U6_IO40',
         32: 'U6_IO39', 31: 'U6_IO38', 27: 'SDA'}
for n, name in right.items():
    g = name in ('TXD', 'RXD', 'SDA')
    lbl_right(name, 181, 107 + 2 * (40 - n), stub=12 if g else 4, glob=g)
for n in (30, 29, 28):
    NC(181, 107 + 2 * (40 - n))
bottom = {15: 'U6_IO3', 16: 'U6_IO46', 17: 'U6_IO9', 18: 'U6_IO10', 19: 'U6_IO11', 21: 'U6_IO13',
          22: 'U6_IO14', 23: 'U6_IO21'}
for n, name in bottom.items():
    lbl_down(name, 149 + 2 * (n - 15), 139)
lbl_down('ESP_TAS_ADR', 159, 139, stub=13, glob=True)    # 20, long stub clears the neighbouring labels
for k, (n, name) in enumerate([(26, 'SCL'), (25, 'DSP_SELFBOOT'), (24, 'DSP_RESET')]):
    x, y = 149 + 2 * (n - 15), 142 + 2 * k                # fan out to the right
    W((x, 139), (x, y), (186, y))
    GL(name, 186, y, ang=0)
T('PSRAM - NC', 184, 130)

# ====================================================== 3V3 decoupling + EN / reset (left)
PW('3.3V', 40, 92)
W((40, 92), (56, 92))
P('C49', 'C', 46, 95, 180)                               # pin2 (46,92)=3.3V
P('C50', 'C', 56, 95)                                    # pin1 (56,92)=3.3V
PW('GND', 46, 98); PW('GND', 56, 98)
T('U6 3V3 decoupling (at module pin 2)', 62, 95)
P('SW1', 'SW4', 44, 110, 0, txt=(-4, -6.5, 0, -6.5, 'left'))  # 1 (40,106) 2 (48,106) 3 (40,114) 4 (48,114)
P('C47', 'C', 36, 110, 180, txt='l')                     # pin2 (36,107)=SW1_P1 pin1 (36,113)
W((40, 106), (36, 106), (36, 107)); W((36, 113), (36, 114), (40, 114))
LBL('SW1_P1', 36, 106, ang=180)
PW('GND', 48, 114)
W((48, 106), (84, 106))
P('C48', 'C', 64, 109, 180)                              # pin2 (64,106)=EN
PW('GND', 64, 112)
P('TP9', 'TP', 76, 106, 0, txt='tp')
LBL('U6_EN', 84, 106)
T('EN (CHIP_PU) has NO pull-up (review P0-1).\nV1.0/V1.1 patch: 10 kΩ from TP9 to 3.3V', 30, 121)

# ====================================================== U7 / H1 expansion headers (left)
P('U7', 'H1x6', 60, 135, 0, txt=(3, -3, 3, -1, 'left'))  # pins x=56: 1 GND 131, 2 3.3V 133, 3..6 IO4..IO7 135..141
PW('GND', 56, 131, 270, show=False)
PW('3.3V', 56, 133, 90)
for k, io in enumerate(['IO4', 'IO5', 'IO6', 'IO7']):
    lbl_left('U6_' + io, 56, 135 + 2 * k)
P('H1', 'H1x4', 60, 152, 0, txt=(3, -2, 3, 0, 'left'))   # pins x=56: IO15..IO18 at 150..156
for k, io in enumerate(['IO15', 'IO16', 'IO17', 'IO18']):
    lbl_left('U6_' + io, 56, 150 + 2 * k)

# ====================================================== H2 2x12 header (bottom left)
P('H2', 'H2x12', 40, 178, 0, txt=(-3, -12, -3, 14, 'left'))  # odd x=36, even x=46, pin1/2 at 168 .. 23/24 at 190
PW('+5V', 36, 168, 90)                                   # 1
W((36, 170), (24, 170)); GL('TXD', 24, 170, ang=180)     # 3
P('TP10', 'TP', 27, 170, 0, txt='tp')
W((36, 172), (24, 172)); GL('RXD', 24, 172, ang=180)     # 5
P('TP11', 'TP', 28, 172, 180, txt=(-1, 3, 0, 0, 'right', 'hidev'))
NC(36, 174)                                              # 7
W((36, 176), (34, 176), (34, 178), (36, 178))            # 9, 11 = 3.3V
PW('3.3V', 34, 177, 90)
lbl_left('TAS_ADR', 36, 180, stub=12, glob=True)         # 13
for y in (182, 184, 186, 188, 190):                      # 15..23 GND
    W((36, y), (34, y))
W((34, 182), (34, 190))
PW('GND', 34, 190)
W((46, 168), (48, 168), (48, 165))                       # 2 = 3.3V
PW('3.3V', 48, 165)
for y, name in [(170, 'U6_IO3'), (172, 'U6_IO46'), (178, 'U6_IO11'), (182, 'U6_IO13'), (184, 'U6_IO14'),
                (186, 'U6_IO21')]:
    lbl_right(name, 46, y)
lbl_right('ESP_TAS_ADR', 46, 180, stub=12, glob=True)    # 14
NC(46, 174); NC(46, 176)                                 # 8, 10
W((46, 188), (48, 188), (48, 190), (46, 190))            # 22, 24 GND
PW('GND', 48, 190)
T('Pick TAS address\nwith jumper (H2 13-14)', 12, 184)
T('H2 7, 8, 10: not connected in V1.2', 52, 196)

# ====================================================== U10 DSP connector (bottom middle)
P('U10', 'H1x6', 110, 180, 0, txt=(3, -3, 3, -1, 'left'))  # pins x=106: 1 GND 176, 2 3.3V 178, 3..6 at 180..186
PW('GND', 106, 176, 270, show=False)
PW('3.3V', 106, 178, 90)
for k, name in enumerate(['DSP_RESET', 'DSP_SDA', 'DSP_SCL', 'DSP_SELFBOOT']):
    lbl_left(name, 106, 180 + 2 * k, glob=True)
T('DSP controlling connector\nKeep it shorter than 30cm', 90, 194)

# ====================================================== I2C to DSP (22 ohm series)
GL('SDA', 196, 154, ang=180)
P('R19', 'R', 202, 154, 270, txt=(-3, -2, 1, -2, 'left'))   # pin2 (199,154)=SDA pin1 (205,154)=DSP_SDA
W((196, 154), (199, 154)); W((205, 154), (208, 154)); GL('DSP_SDA', 208, 154, ang=0)
GL('SCL', 196, 160, ang=180)
P('R20', 'R', 202, 160, 270, txt=(-3, -2, 1, -2, 'left'))
W((196, 160), (199, 160)); W((205, 160), (208, 160)); GL('DSP_SCL', 208, 160, ang=0)
T('I2C to ADAU1466 (DSP)', 190, 150)

# ====================================================== jumper blocks U14 / U15 (right)
P('U14', 'H2x4', 216, 110, 0, txt=(-8, -5, -4, -5, 'left'))  # odd x=212 rows 108..114, even x=222
for k, name in enumerate(['U6_IO1', 'U6_IO2', 'U6_IO42', 'U6_IO41']):
    lbl_left(name, 212, 108 + 2 * k)
for k, name in enumerate(['TAS_MUTE', 'TAS_CLIP', 'TAS_RESET', 'TAS_FAULT']):
    lbl_right(name, 222, 108 + 2 * k, glob=True)
P('U15', 'H2x4', 216, 126, 0, txt=(-8, -5, -4, -5, 'left'))  # odd x=212 rows 124..130, even x=222
PW('GND', 212, 124, 270, show=False)
for k, name in enumerate(['U6_IO40', 'U6_IO39', 'U6_IO38']):
    lbl_left(name, 212, 126 + 2 * k)
W((222, 124), (225, 124), (225, 121))
PW('3.3V', 225, 121)
for k, name in enumerate(['ENABLE_3.3V', 'GOOD_13.2V', 'ENABLE_12V']):
    lbl_right(name, 222, 126 + 2 * k, glob=True)
T('U14: ESP32 <-> TAS3251 control, U15: power control.\nFit shunts on each pair (see tas/README.md, rework B)',
  200, 98)
T('I2S adresses:\nTAS3251 - 0x90 and 0x92\nADAU1466 - 0x68\n(both ADDR pins to GND)', 242, 114)

# ====================================================== user button SW2 on IO10
LBL('U6_IO10', 198, 172, ang=180)
W((198, 172), (210, 172))
P('R51', 'R', 204, 169, 180, txt='l')                    # pin2 (204,166)=3.3V pin1 (204,172)=IO10
PW('3.3V', 204, 166)
P('TP12', 'TP', 207, 172, 0, txt='tp')
P('SW2', 'SW4', 214, 176, 0, txt=(5, 5.5, 5, 7.5, 'left'))  # 1 (210,172) 2 (218,172) 3 (210,180) 4 (218,180)
P('C51', 'C', 222, 176, 180)                             # pin2 (222,173)=SW2_P2 pin1 (222,179)
W((218, 172), (222, 172), (222, 173)); W((222, 179), (222, 180), (218, 180))
LBL('SW2_P2', 222, 172)
PW('GND', 210, 180)

# ====================================================== status LEDs U8 -> U9 (SK9822 chain)
P('U8', 'LED9822', 254, 152, 0, txt=(-4, -6, 0, -6, 'left'))   # SDI (248,150) CKI (248,152) GND (248,154); SDO (260,150) CKO (260,152) VCC (260,154)
P('U9', 'LED9822', 276, 152, 0, txt=(-4, -6, 0, -6, 'left'))   # SDI (270,150) CKI (270,152) GND (270,154); SDO/CKO NC; VCC (282,154)
P('R18', 'R', 240, 150, 270, txt=(-3, -2, 1, -2, 'left'))  # pin1 (243,150)=SDI pin2 (237,150)=IO8
P('R17', 'R', 240, 152, 270, txt=(-3, 2.5, 1, 2.5, 'left'))  # pin1 (243,152)=CKI pin2 (237,152)=IO9
W((243, 150), (248, 150)); W((243, 152), (248, 152))
lbl_left('U6_IO8', 237, 150, stub=2)
lbl_left('U6_IO9', 237, 152, stub=2)
PW('GND', 248, 154, 270, show=False)
W((260, 150), (270, 150)); LBL('U8_SDO', 262, 150)
W((260, 152), (270, 152)); LBL('U8_CKO', 262, 152)
PW('GND', 270, 154, 270, show=False)
NC(282, 150); NC(282, 152)
W((260, 154), (260, 158), (296, 158)); W((282, 154), (282, 158))
PW('+5V', 290, 158)
P('C52', 'C', 300, 161)                                  # pin1 (300,158)=+5V
P('C53', 'C', 308, 161)
W((296, 158), (308, 158))
PW('GND', 300, 164); PW('GND', 308, 164)
T('Status LEDs: data IO8, clock IO9 (V1.2 mapping)', 236, 142)

T('ESP32-S3 CONTROLLER', 120, 92, 1.8, True)
T('USB-C (VBUS -> +5V via ferrite + Schottky), ESD protection', 16, 22, 1.8, True)

s.save(title='Microcontroler', page='Schematic.pdf p.4', dst=args[1] if len(args) > 1 else None)
