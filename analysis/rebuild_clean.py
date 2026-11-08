# Independent re-implementation of the Prep flow rules, used to double-check the Prep output.
import pandas as pd, glob
p = pd.concat(pd.read_csv(f) for f in glob.glob('data/raw/openaq_8664/*.csv'))
p['t'] = pd.to_datetime(p.datetime.str[:19])
stuck = (p.datetime.str[:19] >= '2024-05-31T07:00:00') & (p.datetime.str[:19] <= '2024-06-05T14:00:00')
p['PM25'] = p.value.where((p.value > 0) & ~stuck)
w = pd.read_csv('data/raw/weather/lahore_weather_hourly.csv', skiprows=3)
w.columns = ['t', 'temp', 'rh', 'rain', 'ws', 'wd', 'blh']; w['t'] = pd.to_datetime(w.t)
d = w.merge(p[['t', 'PM25']], on='t', how='left').sort_values('t').reset_index(drop=True)
prev, nxt = d.PM25.shift(1), d.PM25.shift(-1)
d['status'] = 'Valid'
d.loc[(d.PM25 - prev > 300) & (d.PM25 - nxt > 300), 'status'] = 'Suspect spike'
d.loc[d.PM25.isna(), 'status'] = 'Missing'
m = d.t.dt.month
d['season'] = pd.cut(m, [0, 1, 3, 6, 9, 12], labels=['Smog', 'Spring', 'Pre-monsoon', 'Monsoon', 'Smog2']).astype(str).replace('Smog2', 'Smog')
y = d.t.dt.year
d['smog_season'] = None
d.loc[m >= 10, 'smog_season'] = y.astype(str) + '-' + (y + 1).astype(str).str[-2:]
d.loc[m == 1, 'smog_season'] = (y - 1).astype(str) + '-' + y.astype(str).str[-2:]
d['stag'] = 'Ventilated'; d.loc[(d.ws < 5) & (d.blh < 300), 'stag'] = 'Stagnant'; d.loc[d.blh.isna(), 'stag'] = 'Unknown'
d.to_pickle('analysis/clean_rebuild.pkl')
print(len(d), d.status.value_counts().to_dict(), round(d.PM25.mean(), 1))
