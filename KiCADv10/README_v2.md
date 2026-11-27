# NeatAmp MainBoard – schematic v2 (drop-in replacement)

**Replace in your KiCad project folder:** all `*.kicad_sch`, `NeatAmp.kicad_sym`, `tools/`.
**Keep:** `libs/`, `fp-lib-table`, `sym-lib-table`, `NeatAmp.kicad_pro`. Footprint fields are unchanged, so there is no need to re-run easyeda2kicad.

## What changed vs v1
- **Readable net names:** EasyEDA auto-nets are named after the IC pin they touch (`$4N1568` → `U6_EN`). Full mapping in `net_names.csv`.
- **Power symbols** for GND, AGND, 3.3V, +5V, +3.3VA, PVDD, PVDDLMQ, 12V_GVDD, +13.2V, VBUS1.
- **Wired local parts:** 51 passives that connect to a single IC pin (series resistors, bootstrap caps, pull-ups…) sit next to that pin with a real wire. Those nets get KiCad's automatic names, e.g. `Net-(U4-BST)`.
- **IC pins on a 5.08 mm pitch**, so the parts and text attached to them don't overlap.
- Named EasyEDA nets (SDA, USBD+, INA+, …) keep their names.

## Verification
KiCad netlist export vs EasyEDA netlist: 138/138 nets identical, 31/31 no-connects, 233 components, all named nets preserved.
Re-check any time:
```
kicad-cli sch export netlist --format kicadxml -o new.xml NeatAmp.kicad_sch
python3 tools/cmp.py Netlist_Class_D_amp_2026-11-10.enet new.xml
```
