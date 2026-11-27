"""Write the JLC04162H-7628 stackup into the board and net classes/rules into the project.

  python3 tools/easyeda_board_post.py NeatAmp.kicad_pcb NeatAmp.kicad_pro

Stackup and rules follow the EasyEDA Pro MainBoard (LAYER_PHYS / RULE records):
  2 oz outer, 0.5 oz inner, 7628 prepreg 0.2104 mm, 1.065 mm core -> ~1.6 mm.
"""
import sys, json, re

PCB, PRO = sys.argv[1:3]

# (name, type, thickness mm, material, eps_r)
STACK = [
    ('F.SilkS', 'Top Silk Screen', None, None, None),
    ('F.Paste', 'Top Solder Paste', None, None, None),
    ('F.Mask', 'Top Solder Mask', 0.01, None, None),
    ('F.Cu', 'copper', 0.07, None, None),
    ('dielectric 1', 'prepreg', 0.2104, '7628 RC49%', 4.4),
    ('In1.Cu', 'copper', 0.0152, None, None),
    ('dielectric 2', 'core', 1.065, 'FR4', 4.6),
    ('In2.Cu', 'copper', 0.0152, None, None),
    ('dielectric 3', 'prepreg', 0.2104, '7628 RC49%', 4.4),
    ('B.Cu', 'copper', 0.07, None, None),
    ('B.Mask', 'Bottom Solder Mask', 0.01, None, None),
    ('B.Paste', 'Bottom Solder Paste', None, None, None),
    ('B.SilkS', 'Bottom Silk Screen', None, None, None),
]
lines = ['\t\t(stackup']
for n, t, th, mat, er in STACK:
    s = f'\t\t\t(layer "{n}"\n\t\t\t\t(type "{t}")'
    if th is not None:
        s += f'\n\t\t\t\t(thickness {th})'
    if mat:
        s += f'\n\t\t\t\t(material "{mat}")\n\t\t\t\t(epsilon_r {er})\n\t\t\t\t(loss_tangent 0.02)'
    lines.append(s + '\n\t\t\t)')
lines += ['\t\t\t(copper_finish "None")', '\t\t\t(dielectric_constraints no)', '\t\t)']
block = '\n'.join(lines) + '\n'
total = round(sum(th for n, t, th, m, e in STACK if th and 'Mask' not in n), 4)

s = open(PCB).read()
s = re.sub(r'\n\t\t\(stackup\n.*?\n\t\t\)\n', '\n', s, flags=re.S)       # replace if re-run
s = s.replace('\n\t(setup\n', '\n\t(setup\n' + block, 1)
s = re.sub(r'(\(general\n\t\t\(thickness )[\d.]+', r'\g<1>%s' % total, s, count=1)
open(PCB, 'w').write(s)
print('stackup written, board thickness', total, 'mm')

# --- net classes and rules
d = json.load(open(PRO))
ns = d['net_settings']
default = next(c for c in ns['classes'] if c['name'] == 'Default')
default.update(track_width=0.254, clearance=0.152, via_diameter=0.61, via_drill=0.305,
               diff_pair_width=0.254, diff_pair_gap=0.152)
def cls(name, **kw):
    c = dict(default); c.update(name=name, priority=len(ns['classes']) - 1, **kw); return c
ns['classes'] = [default,
                 cls('Power', track_width=1.016, clearance=0.152, via_diameter=1.016, via_drill=0.508),
                 cls('Speaker', track_width=1.778, clearance=0.152, via_diameter=1.016, via_drill=0.508)]
ns['classes'][1]['priority'], ns['classes'][2]['priority'] = 1, 0
POWER = ['PVDD', 'PVDDLMQ', '+13.2V', '12V_GVDD', '+5V', '3.3V', '+3.3VA', 'VBUS1', 'GND', 'AGND',
         '/Power 12V DC/CN1_P1', '/Power 12V DC/Q1_D', '/Power 12V DC/L1_P2', '/Power 12V DC/U2_IN',
         '/Power 5V DC/5V_PVDD', '/Power 3.3V DC/U4_SW', '/Microcontroler/C46_P2']
SPEAKER = ['OUTA+', 'OUTA-', 'OUTB+', 'OUTB-', 'A+', 'A-', 'B+', 'B-']
ns['netclass_patterns'] = ([{'netclass': 'Power', 'pattern': n} for n in POWER] +
                           [{'netclass': 'Speaker', 'pattern': n} for n in SPEAKER])
ds = d['board']['design_settings']
ds['rules'].update(min_clearance=0.127, min_track_width=0.127, min_via_diameter=0.4,
                   min_through_hole_diameter=0.2, min_via_annular_width=0.1,
                   min_copper_edge_clearance=0.3, min_hole_clearance=0.25, min_hole_to_hole=0.25)
ds['track_widths'] = [0.0, 0.254, 0.381, 0.508, 0.762, 1.016, 1.524, 1.778, 2.032, 2.54]
ds['via_dimensions'] = [{'diameter': 0.0, 'drill': 0.0}, {'diameter': 0.61, 'drill': 0.305},
                        {'diameter': 1.016, 'drill': 0.508}]
ds['diff_pair_dimensions'] = [{'gap': 0.0, 'via_gap': 0.0, 'width': 0.0},
                              {'gap': 0.152, 'via_gap': 0.25, 'width': 0.254}]
json.dump(d, open(PRO, 'w'), indent=2)
open(PRO, 'a').write('\n')
print('net classes:', [c['name'] for c in ns['classes']], 'patterns:', len(ns['netclass_patterns']))
