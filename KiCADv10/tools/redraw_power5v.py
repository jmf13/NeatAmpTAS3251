"""Redraw Power_5V_DC.kicad_sch after Schematic.pdf p.2 (layout only; engine in schgen.py).

Usage: python3 tools/redraw_power5v.py [src.kicad_sch [dst.kicad_sch]]
Grid unit u = 1.27 mm.
"""
import sys

from schgen import Sheet

s = Sheet('Power_5V_DC.kicad_sch', src=sys.argv[1] if len(sys.argv) > 1 else None)
P, W, PW, NC, LBL, GL, T = s.P, s.W, s.PW, s.NC, s.LBL, s.GL, s.T

# ---- input decoupling: PVDDLMQ rail y=40, GND bus y=58
PW('PVDDLMQ', 20, 40)
P('C24', 'CP', 24, 49)                                   # + (24,46) - (24,52)
for i, r in enumerate(['C25', 'C26', 'C27', 'C28']):
    P(r, 'C', 32 + 8 * i, 49, 180)                       # pin2 top = PVDDLMQ
for x in (24, 32, 40, 48, 56):
    W((x, 40), (x, 46)); W((x, 52), (x, 58))
W((20, 40), (68, 40))
W((65, 40), (65, 44), (68, 44))                          # VIN
W((24, 58), (56, 58))
PW('GND', 40, 58)

# ---- LMQ66430 buck
P('U3', 'LMQ', 80, 45, 0, txt='chip')                    # left x=68 rows 40..52, right x=92 rows 38..52
for y in (42, 46, 48):
    NC(68, y)
PW('GND', 68, 50, 270, show=False)                       # PGND
PW('GND', 92, 38, 90, show=False)                        # GND/DAP
NC(92, 44); NC(92, 50); NC(92, 52)
# PG pull-up + MODE/SYNC to 3.3V
P('R50', 'R', 102, 35, 180)                              # pin2 (102,32)=3.3V pin1 (102,38)=PG
W((102, 38), (102, 40))
W((92, 40), (114, 40))
LBL('U3_PG', 106, 40)
P('TP13', 'TP', 114, 40, 0, txt='tp')
W((92, 42), (98, 42), (98, 32), (102, 32))
PW('3.3V', 100, 32)
# VCC
W((92, 48), (100, 48))
P('C29', 'C', 100, 51)                                   # (100,48)-(100,54)
PW('GND', 100, 54)
# SW -> L4 -> 5V_PVDD bus (y=64): buck output before the OR-ing diode D5
P('L4', 'L', 64, 58, 180)                                # pin2 (64,55)=SW pin1 (64,61)
W((68, 52), (64, 52), (64, 55))
W((64, 61), (64, 64), (165, 64))
LBL('5V_PVDD', 128, 64)
for i, r in enumerate(['C30', 'C31', 'C32', 'C33', 'C34', 'C35', 'C36']):
    x = 70 + 8 * i
    P(r, 'C', x, 67, 180 if r == 'C36' else 0)           # C30..C35 pin1 top, C36 pin2 top
    W((x, 70), (x, 74))
W((70, 74), (118, 74))
PW('GND', 94, 74)
P('TP27', 'TP', 124, 64, 0, txt='tp')
# feedback divider: FB line y=46, R8 / C23 down to the 5V_PVDD bus, R9 to GND
W((92, 46), (162, 46))
LBL('U3_VOUT_FB', 112, 46)
P('C23', 'C', 142, 55)                                   # pin1 (142,52)=FB pin2 (142,58)=5V_PVDD
P('R8', 'R', 150, 55)                                    # pin1 (150,52)=FB pin2 (150,58)=5V_PVDD
W((142, 46), (142, 52)); W((142, 58), (142, 64))
W((150, 46), (150, 52)); W((150, 58), (150, 64))
P('R9', 'R', 162, 49, 180)                               # pin2 (162,46)=FB pin1 (162,52)=GND
PW('GND', 162, 52)
# OR-ing diode to the +5V bus (USB-C VBUS joins +5V on the Microcontroler sheet)
P('D5', 'DS', 168, 64, 180, txt='h')                     # A (165,64) K (171,64)
W((171, 64), (204, 64))
P('C104', 'C', 176, 67, 180)                             # pin2 top = +5V
P('C105', 'CP', 186, 67)                                 # + top
P('C106', 'CP', 196, 67)
for x in (176, 186, 196):
    W((x, 70), (x, 74))
W((176, 74), (196, 74))
PW('GND', 186, 74)
PW('+5V', 204, 64)

# ---- notes
T('5 V BUCK  (LMQ66430)  +  OR-ing diode to +5V', 60, 26, 1.8, True)
T('Keep in FPWM mode', 104, 31)
T('VOUT = 1.0 V x (1 + R8/R9) = 1.0 V x (1 + 49.9k/12.4k) = 5.02 V (before D5)\n'
  '+5V = 5.02 V - V_F(SS34) = approx. 4.6 V  (see review P2-3)', 112, 82)
T('LMQ66430 → 5V_PVDD\n└── USB-C VBUS\n    └── ideal diode / power mux', 16, 162)

s.save(title='Power 5V DC', page='Schematic.pdf p.2', dst=sys.argv[2] if len(sys.argv) > 2 else None)
