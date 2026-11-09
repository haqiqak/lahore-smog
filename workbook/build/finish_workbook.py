# Second pass on the generated .twb with lxml: settings cwtwb cannot express directly.
import sys
from lxml import etree
path = sys.argv[1]
tree = etree.parse(path); root = tree.getroot()
ds_name = root.find('.//datasources/datasource[@caption="lahore_smog_clean"]').get('name')

def ws(name):
    return root.find(f'.//worksheets/worksheet[@name="{name}"]')

# 1. AQI categories in severity order (legend and stacking), Good first ... Hazardous last
ORDER = ["Good", "Moderate", "Unhealthy for Sensitive Groups", "Unhealthy", "Very Unhealthy", "Hazardous"]
view = ws("AQI Mix by Month").find('table/view')
for old in view.findall('sort'):
    view.remove(old)
ms = etree.Element('sort', {'class': 'manual', 'column': f'[{ds_name}].[none:AQI Category:nk]', 'direction': 'ASC'})
d = etree.SubElement(ms, 'dictionary')
for v in ORDER:
    etree.SubElement(d, 'bucket').text = f'"{v}"'
anchor = view.find('slices') if view.find('slices') is not None else view.find('aggregation')
anchor.addprevious(ms)

# 2. Box plot on Smog Seasons (exact XML Tableau writes for Analytics > Box Plot, cell scope)
pane = ws("Smog Seasons").find('table/panes/pane')
pm = f'[{ds_name}].[avg:PM25:qk]'
n = len(pane.findall('reference-line'))
bp = etree.Element('reference-line', {'axis-column': pm, 'boxplot-mark-exclusion': 'false', 'boxplot-whisker-type': 'standard',
     'enable-instant-analytics': 'true', 'formula': 'average', 'id': f'refline{n}', 'label-type': 'none', 'probability': '95',
     'scope': 'per-cell', 'symmetric': 'false', 'value-column': pm, 'z-order': str(n + 1)})
after = pane.findall('reference-line')
(after[-1] if after else pane.find('encodings')).addnext(bp)

# 3. Small, semi-transparent dots so the box plot and dense clusters stay readable
def mark_style(sheet, size, alpha):
    for p in ws(sheet).findall('table/panes/pane'):
        st = p.find('style')
        if st is None:
            st = etree.SubElement(p, 'style')
        rule = st.find("style-rule[@element='mark']")
        if rule is None:
            rule = etree.SubElement(st, 'style-rule', element='mark')
        for a, v in (('size', size), ('mark-transparency', alpha)):
            for o in rule.findall(f"format[@attr='{a}']"): rule.remove(o)
            etree.SubElement(rule, 'format', attr=a, value=v)
mark_style("Smog Seasons", "0.3", "90")
mark_style("Mixing Height vs PM2.5", "0.45", "170")

# 4. Daily Trend: hide the duplicate (synchronised) moving-average axis and give the axis a readable title
w = ws("Daily Trend"); rows = w.find('table/rows').text
import re
inst = re.findall(r'\[[^\]]+\]\.\[[^\]]+\]', rows)
st = w.find('table/style')
if st is None:
    st = etree.SubElement(w.find('table'), 'style')
rule = st.find("style-rule[@element='axis']")
if rule is None:
    rule = etree.SubElement(st, 'style-rule', element='axis')
etree.SubElement(rule, 'format', {'attr': 'title', 'class': '0', 'field': inst[0], 'scope': 'rows', 'value': 'PM2.5 (\u00b5g/m\u00b3)'})
etree.SubElement(rule, 'format', {'attr': 'display', 'class': '0', 'field': inst[1], 'scope': 'rows', 'value': 'false'})

# 5. Parameter display: Tableau stores the current value's alias on the parameter column
pds = root.find('.//datasources/datasource[@name="Parameters"]')
if pds.find('aliases') is None:
    pds.insert(0, etree.Element('aliases', enabled='yes'))
for col in pds.findall('column'):
    cur = col.get('value')
    for m in col.findall('members/member'):
        if m.get('value') == cur and m.get('alias'):
            col.set('alias', m.get('alias'))

# 6. Readable axis titles
def axis_title(sheet, shelf, title, index=0):
    w = ws(sheet); txt = w.find(f'table/{shelf}').text or ''
    inst = re.findall(r'\[[^\]]+\]\.\[[^\]]+\]', txt)
    st = w.find('table/style')
    if st is None:
        st = etree.SubElement(w.find('table'), 'style')
    rule = st.find("style-rule[@element='axis']")
    if rule is None:
        rule = etree.SubElement(st, 'style-rule', element='axis')
    etree.SubElement(rule, 'format', {'attr': 'title', 'class': '0', 'field': inst[index], 'scope': shelf, 'value': title})
PM = 'PM2.5 (\u00b5g/m\u00b3)'
axis_title("Mixing Height vs PM2.5", "rows", PM)
axis_title("Mixing Height vs PM2.5", "cols", "Mixing height (boundary layer, m)")
axis_title("Stagnant vs Ventilated", "cols", "Average " + PM)
axis_title("Smog Seasons", "rows", "Daily mean " + PM)

# 7. Shared Season filter exactly as Tableau writes it ("Apply to Worksheets > Selected", all members kept)
U = '{http://www.tableausoftware.com/xml/user}'
for flt in root.iter('filter'):
    if flt.get('filter-group') and 'Season:nk' in (flt.get('column') or ''):
        flt.set('filter-group', '3')
        gf = flt.find('groupfilter')
        if gf is not None:
            gf.set(U + 'ui-enumeration', 'all')
            if gf.get(U + 'ui-domain'): del gf.attrib[U + 'ui-domain']

# 8. Readable names for legends and headers (captions only; formulas keep the original field names)
src = root.find(f'.//datasources/datasource[@name="{ds_name}"]')
for name, caption, dtype, role, typ in (('[PM25]', 'PM2.5 (\u00b5g/m\u00b3)', 'real', 'measure', 'quantitative'),
                                        ('[Hour of Day]', 'Hour', 'integer', 'dimension', 'ordinal')):
    cols = [c for c in root.iter('column') if c.get('name') == name]  # data source + each sheet's copy
    if not any(c.getparent() is src for c in cols):
        c = etree.Element('column', {'datatype': dtype, 'name': name, 'role': role, 'type': typ})
        src.find('column').addprevious(c); cols.append(c)
    for c in cols:
        c.set('caption', caption)

def style_rule(sheet, element):
    w = ws(sheet); st = w.find('table/style')
    if st is None: st = etree.SubElement(w.find('table'), 'style')
    rule = st.find(f"style-rule[@element='{element}']")
    if rule is None: rule = etree.SubElement(st, 'style-rule', element=element)
    return rule

# 9. Scatter legend: months in smog-season order (Oct, Nov, Dec, Jan)
w = ws("Mixing Height vs PM2.5")
month_col = w.find('table/panes/pane/encodings/color').get('column')
view = w.find('table/view')
ms = etree.Element('sort', {'class': 'manual', 'column': month_col, 'direction': 'ASC'})
d = etree.SubElement(ms, 'dictionary')
for v in ["October", "November", "December", "January"]:
    etree.SubElement(d, 'bucket').text = f'"{v}"'
(view.find('slices') if view.find('slices') is not None else view.find('aggregation')).addprevious(ms)

# 10. Hide the "n nulls" badges: the gaps are real and are explained in the footer
for sheet in ("Daily Trend", "Mixing Height vs PM2.5"):
    etree.SubElement(style_rule(sheet, 'axis'), 'format', {'attr': 'show-null-value-warning', 'class': '0',
                     'field': f'[{ds_name}].[avg:PM25:qk]', 'scope': 'rows', 'value': 'false'})
    etree.SubElement(style_rule(sheet, 'worksheet'), 'format', {'attr': 'show-null-value-warning', 'value': 'false'})

# 11. "Selected limit" label at the right end, clear of the axis and the data
for sheet, vertical in (("Daily Trend", "bottom"),):
    rule = style_rule(sheet, 'refline')
    etree.SubElement(rule, 'format', {'attr': 'text-align', 'value': 'right'})
    etree.SubElement(rule, 'format', {'attr': 'vertical-align', 'value': vertical})

# 12. Daily Trend x-axis title
day_col = re.findall(r'\[[^\]]+\]\.\[[^\]]+\]', ws("Daily Trend").find('table/cols').text)[0]
etree.SubElement(style_rule("Daily Trend", 'axis'), 'format', {'attr': 'title', 'class': '0', 'field': day_col, 'scope': 'cols', 'value': 'Date'})

# 13. Short month names (Jan ... Dec) in calendar order on both monthly charts, so the headers fit
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
for sheet in ("Smog Clock", "AQI Mix by Month"):
    w = ws(sheet)
    col = re.findall(r'\[[^\]]+\]\.\[[^\]]+\]', w.find('table/cols').text)[0]
    view = w.find('table/view')
    ms = etree.Element('sort', {'class': 'manual', 'column': col, 'direction': 'ASC'})
    d = etree.SubElement(ms, 'dictionary')
    for v in MONTHS:
        etree.SubElement(d, 'bucket').text = f'"{v}"'
    first = view.find('sort')
    (first if first is not None else (view.find('slices') if view.find('slices') is not None else view.find('aggregation'))).addprevious(ms)

# 14. Only the two dashboards show as tabs (needed for Tableau Public)
dash_sheets = {z.get('name') for d in root.iter('dashboard') for z in d.iter('zone') if z.get('name')}
for win in root.iter('window'):
    if win.get('class') == 'worksheet' and win.get('name') in dash_sheets:
        win.set('hidden', 'true')

tree.write(path, xml_declaration=True, encoding='utf-8')
print('finished', path)
