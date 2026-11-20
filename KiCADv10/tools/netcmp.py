"""Compare two KiCad XML netlists (pin sets per net, no-connects, component fields).

Usage: python3 tools/netcmp.py before.xml after.xml
  kicad-cli sch export netlist --format kicadxml -o after.xml NeatAmp.kicad_sch
"""
import sys,xml.etree.ElementTree as ET
def load(f):
    t=ET.parse(f).getroot(); nets={}; nc=set()
    for n in t.find('nets'):
        nodes=frozenset((x.get('ref'),x.get('pin')) for x in n.findall('node') if not x.get('ref').startswith('#'))
        if n.get('name').startswith('unconnected-'): nc|=nodes
        else: nets[nodes]=n.get('name')
    comps={c.get('ref'):{f.get('name'):f.text for f in c.iter('field')}|{'value':c.findtext('value'),'footprint':c.findtext('footprint')} for c in t.find('components')}
    return nets,nc,comps
a,anc,ac=load(sys.argv[1]); b,bnc,bc=load(sys.argv[2])
print('nets base/new',len(a),len(b),' identical sets:',set(a)==set(b))
for k in set(a)-set(b): print(' only base:',a[k],sorted(k))
for k in set(b)-set(a): print(' only new :',b[k],sorted(k))
ren=[(a[k],b[k]) for k in set(a)&set(b) if a[k]!=b[k]]; print('renamed nets:',ren)
print('NC equal',anc==bnc,len(anc),len(bnc))
print('components',len(ac),len(bc), 'same refs', set(ac)==set(bc))
diff=[(r,k,ac[r].get(k),bc[r].get(k)) for r in ac for k in set(ac[r])|set(bc.get(r,{})) if ac[r].get(k)!=bc.get(r,{}).get(k)]
print('field diffs:',len(diff)); [print(' ',d) for d in diff[:20]]
