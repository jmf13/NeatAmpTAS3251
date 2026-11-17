# NeatAmp MainBoard – KiCad schematic generated from EasyEDA Pro netlist

Source: `Netlist_Class_D_amp_2026-11-10.enet` (EasyEDA Pro, V1.2), 233 components, 138 nets.

## Status
- **Verified:** KiCad's exported netlist matches the EasyEDA netlist exactly (138/138 nets, identical pin sets; 31 NC pins = 31 no-connect flags).
- **Faithful 1:1 copy of V1.2.** The P0 fixes from `hw_review_2026-11-06.md` are **not** applied yet. Apply them as a separate commit.
- Written in KiCad 7 file format; KiCad 10 opens it and upgrades it on save.

## How it is drawn
- 5 sheets = original EasyEDA pages (page taken from each part's EasyEDA Channel ID).
- Every pin carries a label: **global labels** for named nets (cross-sheet), **local labels** `N<page>N<id>` for EasyEDA auto-nets (`$4N1568` → `N4N1568`).
- Parts are grouped around the IC they connect to (power nets ignored for grouping); pure decoupling parts sit in a separate group.
- Symbols are generic boxes generated from the real pin numbers/names (library `NeatAmp.kicad_sym`). Swap them for nicer symbols later with *Change Symbol*; pins match by number.
- Every symbol keeps its fields: Value, Footprint, LCSC, MPN, Manufacturer, JLC Class, Datasheet, Description, original EasyEDA footprint/device name. `in_bom` follows EasyEDA "Add into BOM" (test points excluded).

## Libraries
1. `pip install easyeda2kicad`
2. `./get_lcsc_libs.sh`: fetches symbol + footprint + 3D for all 67 LCSC numbers into `libs/easyeda2kicad.*`.
3. Footprint fields point to `easyeda2kicad:<EasyEDA footprint name>`. easyeda2kicad normally names footprints the same way. Any that differ show up as missing footprints in *Update PCB from Schematic*; fix them with *Tools → Edit Symbol Fields* (filter by the `EasyEDA Footprint` column).
4. Parts without LCSC number:
   - Test points → `TestPoint:TestPoint_Pad_D1.0mm` (KiCad standard)
   - L7/L9/L11/L13 (XGL1712) and L8/L10/L12/L14 (MA5172-AE) → `NeatAmp_custom:*`, which needs footprints created from the Coilcraft datasheets. Both footprints are intentional (alternative inductors to compare); only one per leg is mounted.

## Re-check after editing
```
kicad-cli sch export netlist --format kicadxml -o new.xml NeatAmp.kicad_sch
python3 tools/cmp.py Netlist_Class_D_amp_2026-11-10.enet new.xml
```
(Expect differences only where you deliberately changed the circuit.)

## Regenerate
`python3 tools/gen.py <netlist.enet> <outdir> NeatAmp`
