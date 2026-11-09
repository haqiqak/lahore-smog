# Builds the Lahore Smog Tableau workbook from the cleaned Prep output.
# Run from the repo root (needs: pip install cwtwb lxml):
#   python workbook/build/build_workbook.py
#   python workbook/build/finish_workbook.py workbook/build/lahore_smog.twb
#   python workbook/build/package.py workbook/build/lahore_smog.twb workbook/lahore_smog_dashboard.twbx
import sys
from cwtwb import TWBEditor

import os, cwtwb
TEMPLATE = os.path.join(os.path.dirname(cwtwb.__file__), 'references', 'empty_template.twb')
CSV = 'data/processed/lahore_smog_clean.csv'
OUT = sys.argv[1] if len(sys.argv) > 1 else 'workbook/build/lahore_smog.twb'

e = TWBEditor(TEMPLATE)
F = lambda name, dt, role, ft: {"name": name, "datatype": dt, "role": role, "field_type": ft}
e.set_csv_connection(CSV, fields=[
    F("Stagnation Flag", "string", "dimension", "nominal"),
    F("AQI Category", "string", "dimension", "nominal"),
    F("Smog Season", "string", "dimension", "ordinal"),
    F("Season", "string", "dimension", "nominal"),
    F("PM25", "real", "measure", "quantitative"),
    F("Date Time", "datetime", "dimension", "ordinal"),
    F("Hour of Day", "integer", "dimension", "ordinal"),
    F("Temperature (C)", "real", "measure", "quantitative"),
    F("Humidity (%)", "integer", "measure", "quantitative"),
    F("Rain (mm)", "real", "measure", "quantitative"),
    F("Wind Speed (km/h)", "real", "measure", "quantitative"),
    F("Wind Direction (deg)", "integer", "measure", "quantitative"),
    F("Boundary Layer Height (m)", "integer", "measure", "quantitative"),
    F("WHO Multiple", "real", "measure", "quantitative"),
    F("Data Status", "string", "dimension", "nominal"),
])

# ---------- Parameters ----------
e.add_parameter("Threshold (ug/m3)", datatype="string", default_value='"35"', domain_type="list",
                allowed_values=['15', '35', '55.4', '125.4', '225.4'],
                allowed_aliases={'15': "15 - WHO 24-hour guideline", '35': "35 - Pakistan NEQS 24-hour limit",
                                 '55.4': "55.4 - EPA: Unhealthy above this", '125.4': "125.4 - EPA: Very Unhealthy above this",
                                 '225.4': "225.4 - EPA: Hazardous above this"})
e.add_parameter("Moving Average (days)", datatype="integer", default_value="30", domain_type="list",
                allowed_values=["7", "14", "30", "60"])
e.add_parameter("Stagnant Wind Below (km/h)", datatype="real", default_value="5", domain_type="range",
                min_value="1", max_value="15", granularity="1")
e.add_parameter("Stagnant Mixing Height Below (m)", datatype="integer", default_value="300", domain_type="range",
                min_value="50", max_value="1000", granularity="50")

# ---------- Calculated fields ----------
e.add_calculated_field("Valid Hour", "IF NOT ISNULL([PM25]) THEN 1 END", datatype="integer")
e.add_calculated_field("Day", "DATETRUNC('day', [Date Time])", datatype="date", role="dimension", field_type="ordinal")
e.add_calculated_field("Daily Valid Hours", "{FIXED DATETRUNC('day', [Date Time]) : COUNT([PM25])}", datatype="integer")
e.add_calculated_field("Daily Mean PM25", "{FIXED DATETRUNC('day', [Date Time]) : AVG([PM25])}", datatype="real")
e.add_calculated_field("Complete Day", "// a day counts only with at least 18 of 24 hours measured (75%)\n"
                       "IF [Daily Valid Hours] >= 18 THEN DATETRUNC('day', [Date Time]) END",
                       datatype="date", role="dimension", field_type="ordinal")
e.add_calculated_field("Day Above Threshold",
                       "IF [Daily Valid Hours] >= 18 AND [Daily Mean PM25] > FLOAT([Threshold (ug/m3)]) THEN DATETRUNC('day', [Date Time]) END",
                       datatype="date", role="dimension", field_type="ordinal")
e.add_calculated_field("% Days Above Threshold", "COUNTD([Day Above Threshold]) / COUNTD([Complete Day])",
                       datatype="real", default_format="p0%")
e.add_calculated_field("Average PM2.5", "AVG([PM25])", datatype="real", default_format="n#,##0")
e.add_calculated_field("Times WHO Limit", "AVG([PM25]) / 15", datatype="real", default_format='n0.0"x"')
e.add_calculated_field("Hazardous Hours", "SUM(IF [PM25] > 225.4 THEN 1 ELSE 0 END)", datatype="integer", default_format="n#,##0")
e.add_calculated_field("Data Coverage", "COUNT([PM25]) / COUNT([Date Time])", datatype="real", default_format="p0%")
e.add_calculated_field("Share of Hours", "SUM([Valid Hour]) / TOTAL(SUM([Valid Hour]))", datatype="real",
                       default_format="p0%", table_calc="Pane (down)" if False else None)
e.add_calculated_field("PM2.5 Moving Average",
                       "WINDOW_AVG(AVG([PM25]), -([Moving Average (days)] - 1), 0)", datatype="real",
                       default_format="n#,##0")
e.add_calculated_field("AQI Level", "CASE [AQI Category] WHEN 'Good' THEN 1 WHEN 'Moderate' THEN 2 "
                       "WHEN 'Unhealthy for Sensitive Groups' THEN 3 WHEN 'Unhealthy' THEN 4 "
                       "WHEN 'Very Unhealthy' THEN 5 WHEN 'Hazardous' THEN 6 END", datatype="integer")
e.add_calculated_field("Air Condition",
                       "// Parameter-driven version of the Prep Stagnation Flag\n"
                       "IF ISNULL([Boundary Layer Height (m)]) THEN 'Unknown (no mixing-height data)'\n"
                       "ELSEIF [Wind Speed (km/h)] < [Stagnant Wind Below (km/h)] AND [Boundary Layer Height (m)] < [Stagnant Mixing Height Below (m)] THEN 'Stagnant'\n"
                       "ELSE 'Ventilated' END", datatype="string", role="dimension", field_type="nominal")
e.add_calculated_field("Season Coverage", "{FIXED [Smog Season] : COUNT([PM25]) / COUNT([Date Time])}", datatype="real", default_format="p0%")
e.add_calculated_field("Winter Coverage", "IF [Season Coverage] >= 0.75 THEN '75% or more of hours' "
                       "ELSE 'Under 75% of hours' END", datatype="string", role="dimension", field_type="nominal")
e.add_calculated_field("Month", "DATENAME('month', [Date Time])", datatype="string", role="dimension", field_type="ordinal")
e.add_calculated_field("Month (short)", "LEFT(DATENAME('month', [Date Time]), 3)", datatype="string", role="dimension", field_type="ordinal")

e.add_calculated_field("Complete Day Flag", "[Daily Valid Hours] >= 18", datatype="boolean", role="dimension", field_type="nominal")
e.add_calculated_field("Threshold Line", "FLOAT([Threshold (ug/m3)])", datatype="real")
e.add_calculated_field("WHO Guideline", "15", datatype="real")
e.add_calculated_field("Hours Measured", "SUM([Valid Hour])", datatype="integer", default_format="n#,##0")

SMOG = {"column": "Season", "values": ["Smog (Oct-Jan)"]}
EPA = {"Good": "#00A65A", "Moderate": "#E8C300", "Unhealthy for Sensitive Groups": "#F07F09",
       "Unhealthy": "#E0201B", "Very Unhealthy": "#8E3F97", "Hazardous": "#6E0020"}

# 1. KPI tiles (one big number per sheet)
KPI = [("KPI Average", "Average PM2.5", "Average PM2.5 (\u00b5g/m\u00b3)"),
       ("KPI WHO", "Times WHO Limit", "times the WHO 24-hour guideline"),
       ("KPI Days Above", "% Days Above Threshold", "of days above the selected limit"),
       ("KPI Hazardous", "Hazardous Hours", "Hazardous hours (PM2.5 > 225)"),
       ("KPI Coverage", "Data Coverage", "of hours actually measured")]
for sheet, field, caption in KPI:
    e.add_worksheet(sheet)
    e.configure_chart(sheet, mark_type="Text", label=field, filters=[{"column": "Season"}])
    e.configure_custom_label(sheet, [
        {"field": field, "fontsize": "24", "bold": True, "fontcolor": "#B03A2E", "fontalignment": "1"},
        {"text": "\n" + caption, "fontsize": "9", "fontcolor": "#5F6B76", "fontalignment": "1"}])

# 2. Daily trend with moving average (trend analysis)
e.add_worksheet("Daily Trend")
e.configure_layered_chart(
    "Daily Trend", columns=["DAYTRUNC(Date Time)"], rows=["AVG(PM25)", "PM2.5 Moving Average"],
    panes=[{"mark_type": "Line"},
           {"mark_type": "Line", "axis": "AVG(PM25)", "mark_style": {"mark_color": "#C9CDD2"}},
           {"mark_type": "Line", "axis": "PM2.5 Moving Average", "mark_style": {"mark_color": "#B03A2E"}}],
    synchronized=True,
    table_calc_overrides={"PM2.5 Moving Average": [{"ordering_field": "DAYTRUNC(Date Time)", "ordering_type": "Field"}]})

# 3. Smog clock heatmap (hour x month)
e.add_worksheet("Smog Clock")
e.configure_chart("Smog Clock", mark_type="Square", columns=["Month (short)"], rows=["Hour of Day"],
                  color="AVG(PM25)", tooltip=["Hours Measured"])
e.configure_worksheet_style("Smog Clock", hide_col_field_labels=True, color_style={"field": "AVG(PM25)",
                  "colors": ["#FFF4E0", "#F7C873", "#E8743B", "#B03A2E", "#4A1416"]})

# 4. AQI mix by month (composition / comparison)
e.add_worksheet("AQI Mix by Month")
e.configure_chart("AQI Mix by Month", mark_type="Bar", columns=["Month (short)"], rows=["Share of Hours"],
                  color="AQI Category", color_map=EPA, tooltip=["Hours Measured"], text_format={"Share of Hours": "p0%"},
                  filters=[{"column": "Data Status", "values": ["Valid", "Suspect spike"]}, {"column": "Season"}],
                  table_calc_overrides={"Share of Hours": [{"ordering_field": "AQI Category", "ordering_type": "Field"}]})

e.configure_worksheet_style("AQI Mix by Month", hide_col_field_labels=True)

# 5. Relationship: mixing height vs PM2.5, one dot per smog-season day
e.add_worksheet("Mixing Height vs PM2.5")
e.configure_layered_chart(
    "Mixing Height vs PM2.5", columns=["AVG(Boundary Layer Height (m))"], rows=["AVG(PM25)"],
    panes=[{"mark_type": "Circle", "detail": "DAYTRUNC(Date Time)", "color": "Month",
            "tooltip": ["AVG(Wind Speed (km/h))"], "trendline": {"fit": "log", "exclude_color": True}}],
    filters=[SMOG, {"column": "Complete Day Flag", "values": ["true"]}])

# 6. Stagnant vs ventilated (comparison, parameter-driven)
e.add_worksheet("Stagnant vs Ventilated")
e.configure_chart("Stagnant vs Ventilated", mark_type="Bar", rows=["Air Condition"], columns=["AVG(PM25)"],
                  color="Air Condition", label="AVG(PM25)", tooltip=["Hours Measured"],
                  color_map={"Stagnant": "#B03A2E", "Ventilated": "#7A8B99"}, text_format={"AVG(PM25)": "n#,##0"},
                  filters=[SMOG, {"column": "Air Condition", "values": ["Stagnant", "Ventilated"]}])
e.configure_worksheet_style("Stagnant vs Ventilated", hide_row_field_labels=True)

# 7. Smog seasons: distribution of daily means (box plot added in post-processing)
e.add_worksheet("Smog Seasons")
e.configure_chart("Smog Seasons", mark_type="Circle", columns=["Smog Season"], rows=["AVG(PM25)"],
                  detail="DAYTRUNC(Date Time)", color="Winter Coverage",
                  color_map={"75% or more of hours": "#B03A2E", "Under 75% of hours": "#BFC5CC"},
                  filters=[{"column": "Complete Day Flag", "values": ["true"]},
                           {"column": "Smog Season", "values": ["2019-20", "2020-21", "2021-22", "2022-23", "2023-24", "2024-25"]}])

OVERVIEW = [k[0] for k in KPI] + ["AQI Mix by Month"]  # the heatmap always shows all 12 months
e.link_worksheet_filters("Season", OVERVIEW)

# Reference lines
e.add_reference_line("Daily Trend", axis_field="AVG(PM25)", value_field="AVG(Threshold Line)", formula="average",
                     label_type="custom", label="Selected limit", pane_index=1)
e.add_reference_line("Smog Seasons", axis_field="AVG(PM25)", value_field="AVG(Threshold Line)", formula="average",
                     label_type="none")

# Titles that state the finding
TITLES = {
 "Daily Trend": "Every winter PM2.5 climbs from October and peaks in Dec-Jan",
 "Smog Clock": "Oct-Jan: midnight ~1.6x dirtier than 3-5 PM",
 "AQI Mix by Month": "Nov-Jan: 97% of hours are Unhealthy or worse",
 "Mixing Height vs PM2.5": "A shallow mixing layer traps smog (one dot = one smog-season day)",
 "Stagnant vs Ventilated": "Still, low-mixing air is dirtier",
 "Smog Seasons": "The two most recent, well-measured winters were the worst (daily means; line = selected limit)",
}
for k, v in TITLES.items():
    e.set_worksheet_rich_title(k, [{"text": v, "fontsize": "12", "bold": True, "fontcolor": "#2B2B2B"}])
for sheet, *_ in KPI:
    e.set_worksheet_title(sheet, "")

# Dashboards
import json
SRC = ("Data: U.S. State Department / EPA AirNow monitor at the U.S. Consulate Lahore, via OpenAQ (public domain); weather: Open-Meteo (ERA5, CC BY 4.0). Hourly, 23 May 2019 to 4 Mar 2025.")
d1 = {"type": "container", "direction": "vertical", "children": [
  {"type": "text", "text": "Lahore's Fifth Season: six years of hourly PM2.5", "font_size": "18", "bold": True, "fixed_size": 36},
  {"type": "container", "direction": "horizontal", "fixed_size": 92, "children": [
      {"type": "worksheet", "name": k[0], "show_title": False} for k in KPI]},
  {"type": "container", "direction": "horizontal", "fixed_size": 215, "children": [
      {"type": "worksheet", "name": "Daily Trend", "weight": 5, "fit": "entire"},
      {"type": "container", "direction": "vertical", "fixed_size": 200, "children": [
          {"type": "filter", "worksheet": "AQI Mix by Month", "field": "Season", "mode": "checkdropdown", "fixed_size": 56},
          {"type": "paramctrl", "parameter": "Threshold (ug/m3)", "mode": "compact", "fixed_size": 56},
          {"type": "paramctrl", "parameter": "Moving Average (days)", "mode": "compact", "fixed_size": 56},
          {"type": "empty"}]}]},
  {"type": "container", "direction": "horizontal", "weight": 1, "children": [
      {"type": "worksheet", "name": "AQI Mix by Month", "fixed_size": 470, "fit": "entire"},
      {"type": "color", "worksheet": "AQI Mix by Month", "field": "AQI Category", "fixed_size": 280},
      {"type": "container", "direction": "vertical", "weight": 5, "children": [
          {"type": "worksheet", "name": "Smog Clock", "fit": "entire"},
          {"type": "color", "worksheet": "Smog Clock", "field": "AVG(PM25)", "fixed_size": 48}]}]},
  {"type": "text", "text": SRC, "font_size": "8", "font_color": "#5F6B76", "fixed_size": 24}]}
d2 = {"type": "container", "direction": "vertical", "children": [
  {"type": "text", "text": "Why it gets so bad: weather traps the smog (smog season, Oct-Jan)", "font_size": "18", "bold": True, "fixed_size": 36},
  {"type": "container", "direction": "horizontal", "weight": 1, "children": [
      {"type": "worksheet", "name": "Mixing Height vs PM2.5", "weight": 5, "fit": "entire"},
      {"type": "color", "worksheet": "Mixing Height vs PM2.5", "field": "Month", "fixed_size": 100},
      {"type": "container", "direction": "vertical", "weight": 3, "children": [
          {"type": "worksheet", "name": "Stagnant vs Ventilated", "fit": "entire"},
          {"type": "paramctrl", "parameter": "Stagnant Wind Below (km/h)", "fixed_size": 56},
          {"type": "paramctrl", "parameter": "Stagnant Mixing Height Below (m)", "fixed_size": 56}]}]},
  {"type": "container", "direction": "horizontal", "weight": 1, "children": [
      {"type": "worksheet", "name": "Smog Seasons", "weight": 5, "fit": "entire"},
      {"type": "color", "worksheet": "Smog Seasons", "field": "Winter Coverage", "fixed_size": 200}]},
  {"type": "text", "text": "Click a winter in the bottom chart to filter the charts above. Hours with no mixing-height data (Jan-Jun 2024) are left out of the two weather charts.", "font_size": "8", "font_color": "#5F6B76", "fixed_size": 20},
  {"type": "text", "text": SRC, "font_size": "8", "font_color": "#5F6B76", "fixed_size": 22}]}
json.dump(d1, open('workbook/build/d1.json', 'w')); json.dump(d2, open('workbook/build/d2.json', 'w'))
e.add_dashboard("When and How Bad", width=1280, height=800, layout='workbook/build/d1.json')
e.add_dashboard("Why: Weather", width=1280, height=800, layout='workbook/build/d2.json')

# Actions
e.add_dashboard_action("When and How Bad", "highlight", source_sheet="Smog Clock", target_sheet="AQI Mix by Month",
                       fields=["Month (short)"], event_type="on-hover", caption="Highlight month")
e.add_dashboard_action("When and How Bad", "highlight", source_sheet="AQI Mix by Month", target_sheet="Smog Clock",
                       fields=["Month (short)"], event_type="on-hover", caption="Highlight month (back)")
e.add_dashboard_action("Why: Weather", "filter", source_sheet="Smog Seasons", target_sheets=["Mixing Height vs PM2.5", "Stagnant vs Ventilated"],
                       fields=["Smog Season"], event_type="on-select", caption="Filter by smog season")

e.save(OUT, validate=False)
print('saved', OUT)
