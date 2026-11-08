# Packages lahore_smog.twb + the clean CSV into a .twbx, with a relative data path.
import sys, zipfile, re
from lxml import etree
twb, out = sys.argv[1], sys.argv[2]
tree = etree.parse(twb)
root = tree.getroot()
for c in root.xpath('//comment()'):
    if c.getparent() is not None: c.getparent().remove(c)
for conn in root.iter('connection'):
    if conn.get('class') == 'textscan':
        conn.set('directory', 'Data/processed')
root.set('locale', 'en_US')
for el in root.iter():
    if el.get('locale'): el.set('locale', 'en_US')
for ws in root.xpath("//worksheets/worksheet[@name='Sheet 1']"): ws.getparent().remove(ws)
for w in root.xpath("//windows/window[@name='Sheet 1']"): w.getparent().remove(w)
xml = etree.tostring(root, xml_declaration=True, encoding="utf-8")
name = out.rsplit('/', 1)[-1].replace('.twbx', '.twb')
with zipfile.ZipFile(out, 'w', zipfile.ZIP_DEFLATED) as z:
    z.writestr(name, xml)
    z.write('data/processed/lahore_smog_clean.csv', 'Data/processed/lahore_smog_clean.csv')
print('packaged', out)
