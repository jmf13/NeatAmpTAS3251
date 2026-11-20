"""Redraw Power_12V_DC.kicad_sch after Schematic.pdf p.1 (layout only; engine in schgen.py).

Usage: python3 tools/redraw_power12v.py [src.kicad_sch [dst.kicad_sch]]
Grid unit u = 1.27 mm.
"""
import sys

from schgen import Sheet

s = Sheet('Power_12V_DC.kicad_sch', src=sys.argv[1] if len(sys.argv) > 1 else None)
P, W, PW, NC, LBL, GL, T = s.P, s.W, s.PW, s.NC, s.LBL, s.GL, s.T

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
s.shift(12, 56)     # everything right of the old Q1 moves 12 u to the right
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
PW('GND', 178, 38, 90, show=False)                       # GND/DAP
P('R1', 'R', 188, 37, 180)                               # pin2 (188,34) pin1 (188,40)
W((178, 40), (198, 40))                                  # PG -> GOOD_13.2V
GL('GOOD_13.2V', 198, 40, 'output', 0)
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
T('13.2 V BUCK  (LMQ66430)', 146, 26, 1.8, True)
T('Keep in FPWM mode', 190, 31)
T('VOUT = 1.0 V x (1 + R3/R6)\n= 1.0 V x (1 + 100k/8.2k) = 13.2 V', 240, 44)

# ---- 12V_GVDD LDO
s.shift(0)
P('U2', 'TPS', 166, 118, 0, txt='chip2')                 # left x=151, right x=181, bottom y=139
P('L3', 'FB', 112, 113, 270, txt='h')                    # pin2 (109,113) pin1 (115,113)
PW('+13.2V', 104, 113)
W((104, 113), (109, 113))
W((115, 113), (151, 113))
W((148, 113), (148, 115), (151, 115))
LBL('U2_IN', 117, 113)
P('C22', 'C', 124, 116)                                  # (124,113)-(124,119)
PW('GND', 124, 119)
GL('ENABLE_12V', 128, 109, 'input', 180)
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
T('12V_GVDD LOW-NOISE LDO  (TPS7A4701)', 100, 96, 1.8, True)
T('ANY-OUT: 6P4V1 + 3P2V + 0P8V + 0P2V tied to GND\nVOUT = 1.4 V + 6.4 V + 3.2 V + 0.8 V + 0.2 V = 12.0 V', 152, 152)
T('For PCB use:\nJLC04162H-7628 - sufficient\nJLC04162H-3313 - better', 16, 162)
T('LMQ66410 → 13.2V\nLC/ferrite filter\nlow-noise TPS7A49 / TPS7A47 / LT1763 / TLV767 / TPS7A26 → 12V_GVDD\n'
  'local decoupling at TAS pins', 16, 176)

s.save(title='Power 12V DC', page='Schematic.pdf p.1', dst=sys.argv[2] if len(sys.argv) > 2 else None)
