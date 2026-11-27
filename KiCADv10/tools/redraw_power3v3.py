"""Redraw Power_3_3V_DC.kicad_sch after Schematic.pdf p.3 (layout only; engine in schgen.py).

Usage: python3 tools/redraw_power3v3.py [src.kicad_sch [dst.kicad_sch]]
Grid unit u = 1.27 mm.
"""
import sys

from schgen import Sheet

s = Sheet('Power_3_3V_DC.kicad_sch', src=sys.argv[1] if len(sys.argv) > 1 else None)
P, W, PW, NC, LBL, GL, T = s.P, s.W, s.PW, s.NC, s.LBL, s.GL, s.T

# ---- 3.3 V digital buck (AP63203, fixed output: FB tied to 3.3V), GND bus y=52
P('U4', 'AP', 50, 44, 0, txt=(-6, -6, -6, 6, 'left'))   # left x=42: FB 42 EN 44 VIN 46; right x=58: BST 42 SW 44 GND 46
W((26, 46), (42, 46))                                    # +5V -> VIN
W((42, 44), (38, 44), (38, 46))                          # EN tied to VIN
PW('+5V', 30, 46)
P('TP4', 'TP', 34, 46, 0, txt='tp')
P('C38', 'C', 26, 49)                                    # (26,46)-(26,52)
W((42, 42), (40, 42), (40, 32), (98, 32), (98, 44))      # FB -> 3.3V output
PW('3.3V', 70, 32)
P('C37', 'C', 62, 38, 90, txt='h')                       # pin1 (59,38)=BST pin2 (65,38)=SW
W((58, 42), (59, 42), (59, 38))
W((65, 38), (65, 44))
W((58, 44), (65, 44))
LBL('U4_SW', 60, 44)
P('L5', 'L', 68, 44, 90, txt='h')                        # pin1 (65,44)=SW pin2 (71,44)=3.3V
W((71, 44), (106, 44))
P('TP5', 'TP', 74, 44, 0, txt='tp')
P('C39', 'C', 78, 47)                                    # pin1 top = 3.3V
P('C40', 'CP', 86, 47)                                   # + top
P('C41', 'C', 94, 47, 180)                               # pin2 top = 3.3V
for x in (78, 86, 94):
    W((x, 50), (x, 52))
P('CN5', 'CN', 110, 44, 0, txt=(-1, -3, -1, 5, None))    # pin1 (106,44)=3.3V pin2 (106,46)=GND
W((106, 46), (104, 46), (104, 52))
W((58, 46), (58, 52))
W((26, 52), (104, 52))
PW('GND', 50, 52)
P('TP6', 'TP', 70, 52, 0, txt='tp')

# ---- 3.3 V analog LDO (TPS7A2033) for TAS3251 DAC_AVDD, AGND domain
P('U5', 'LDO20', 66, 74, 0, txt=(-5, -6, -1, -6, 'left'))  # IN (59,72) EN (59,76) OUT (73,72) NC (73,76) GND (66,80)
PW('+5V', 38, 72)
W((38, 72), (59, 72))
P('C42', 'C', 42, 75)                                    # pin1 (42,72)=+5V pin2 (42,78)=AGND
PW('AGND', 42, 78)
W((59, 76), (57, 76), (57, 84), (36, 84))                # EN
GL('ENABLE_3.3V', 36, 84, 'input', 180)
P('R10', 'R', 52, 81, 180, txt='l')                      # pin2 (52,78)=3.3V pin1 (52,84)=EN
PW('3.3V', 52, 78)
NC(73, 76)
W((66, 80), (66, 82), (70, 82))
PW('AGND', 66, 82)
P('TP8', 'TP', 70, 82, 0, txt='tp')
W((73, 72), (94, 72))
P('TP7', 'TP', 85, 72, 0, txt='tp')
P('C43', 'C', 80, 75)                                    # pin1 (80,72)=+3.3VA pin2 (80,78)=AGND
PW('AGND', 80, 78)
PW('+3.3VA', 94, 72)

# ---- notes
T('3.3 V DIGITAL  (AP63203 buck, fixed 3.3 V)', 24, 26, 1.8, True)
T('3.3 V ANALOG  (TPS7A2033 LDO)  ->  +3.3VA = TAS3251 DAC_AVDD', 24, 64, 1.8, True)
T('U5 returns to AGND (C42, C43, U5 GND)', 76, 86)
T('5V_SYS\n├── AP63203 -- 3.3V_DI\n└── ferrite bead → TPS7A20 → 3.3V_ANA\n'
  '(ferrite bead not fitted yet: U5 IN is fed straight from +5V, see review P2-1)', 16, 162)

s.save(title='Power 3.3V DC', page='Schematic.pdf p.3', dst=sys.argv[2] if len(sys.argv) > 2 else None)
