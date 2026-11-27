import json,sys,collections,xml.etree.ElementTree as ET
d=json.load(open(sys.argv[1])); t=ET.parse(sys.argv[2]).getroot()
src=collections.defaultdict(set); nc_src=set()
for v in d['components'].values():
    r=v['props']['Designator']
    for k,x in v['pinInfoMap'].items():
        (nc_src.add((r,k)) if not x['net'] else src[x['net']].add((r,k)))
kic={}; nc_k=set()
for n in t.find('nets'):
    nodes={(x.get('ref'),x.get('pin')) for x in n.findall('node') if not x.get('ref').startswith('#')}
    if n.get('name').startswith('unconnected-'): nc_k|=nodes
    else: kic[n.get('name')]=frozenset(nodes)
S={frozenset(v) for v in src.values()}; K=set(kic.values())
print('src nets',len(S),'kicad nets',len(K))
print('missing in kicad:',[sorted(x) for x in S-K][:5]); print('extra in kicad:',[sorted(x) for x in K-S][:5])
print('NC src',len(nc_src),'NC kicad',len(nc_k),'NC equal',nc_src==nc_k)
comps={c.get('ref') for c in t.find('components')}; print('components',len(comps))
