import pandas as pd, numpy as np, json
d = pd.read_pickle('analysis/clean_rebuild.pkl'); v = d[d.status != 'Missing'].copy()
out = {}
out['hours_total'] = len(d); out['hours_valid'] = int(len(v)); out['coverage_pct'] = round(100*len(v)/len(d), 1)
out['mean_all'] = round(v.PM25.mean(), 1); out['median_all'] = round(v.PM25.median(), 1)
# AQI categories (hourly)
bins=[0,9,35.4,55.4,125.4,225.4,1e9]; lab=['Good','Moderate','USG','Unhealthy','Very Unhealthy','Hazardous']
v['aqi']=pd.cut(v.PM25,bins,labels=lab)
out['aqi_share_pct']=(100*v.aqi.value_counts(normalize=True)).round(1).reindex(lab).to_dict()
out['unhealthy_or_worse_pct']=round(100*(v.PM25>55.4).mean(),1)
# daily means with >=18 valid hours
v['date']=v.t.dt.date; g=v.groupby('date').PM25.agg(['mean','count']); day=g[g['count']>=18]['mean']
out['valid_days']=int(len(day)); out['days_over_WHO24_pct']=round(100*(day>15).mean(),1); out['days_over_PakNEQS35_pct']=round(100*(day>35).mean(),1)
out['max_day']=[str(day.idxmax()), round(day.max(),1)]
# monthly profile
mo=v.groupby(v.t.dt.month).PM25.mean().round(0); out['month_mean']=mo.to_dict()
out['dec_vs_aug_ratio']=round(mo[12]/mo[8],1)
# diurnal by season
di=v.pivot_table(index=v.t.dt.hour,columns='season',values='PM25',aggfunc='mean').round(0)
out['diurnal_smog']=di['Smog'].to_dict(); out['diurnal_monsoon']=di['Monsoon'].to_dict()
s=di['Smog']; out['smog_peak_hour']=int(s.idxmax()); out['smog_min_hour']=int(s.idxmin()); out['smog_peak_to_min']=round(s.max()/s.min(),2)
school=s.loc[8:14]; out['smog_school_hours']=school.to_dict()
# smog season trend (only seasons with good coverage)
sm=d[d.smog_season.notna()]
tr=sm.groupby('smog_season').agg(cov=('PM25',lambda x: round(100*x.notna().mean(),1)), mean=('PM25','mean'), median=('PM25','median'),
   haz_hours=('PM25',lambda x:int((x>225.4).sum())), haz_share=('PM25',lambda x: round(100*(x[x.notna()]>225.4).mean(),1)), vu_or_worse=('PM25',lambda x: round(100*(x[x.notna()]>125.4).mean(),1)))
tr['mean']=tr['mean'].round(0); tr['median']=tr['median'].round(0); out['smog_trend']=tr.to_dict(orient='index')
# stagnation within smog season only
ss=v[(v.season=='Smog')&(v.stag!='Unknown')]
st=ss.groupby('stag').PM25.agg(['mean','median','count']).round(0); out['stag_smog']=st.to_dict(orient='index')
out['stag_smog_ratio']=round(st.loc['Stagnant','mean']/st.loc['Ventilated','mean'],2)
out['stag_share_of_hazardous_smog']=round(100*(ss[ss.PM25>225.4].stag=='Stagnant').mean(),1); out['stag_share_of_hours_smog']=round(100*(ss.stag=='Stagnant').mean(),1)
# BLH quintiles in smog season
ss=ss.assign(q=pd.qcut(ss.blh,5,labels=['Q1 lowest','Q2','Q3','Q4','Q5 highest']))
out['blh_quintile_smog']=ss.groupby('q',observed=True).agg(blh=('blh','median'),pm=('PM25','mean')).round(0).to_dict(orient='index')
# spearman correlations in smog season, daily
sd=v[v.season=='Smog'].groupby('date').agg(pm=('PM25','mean'),n=('PM25','size'),blh=('blh','mean'),ws=('ws','mean'),t=('temp','mean'),rh=('rh','mean'),rain=('rain','sum'))
sd=sd[sd.n>=18]; out['spearman_daily_smog']=sd[['pm','blh','ws','t','rh','rain']].corr('spearman')['pm'].round(2).drop('pm').to_dict()
# rain washout: daily PM on day after a rainy day (>=5mm) vs after dry day, outside monsoon? use all non-monsoon months
dd=v.groupby('date').agg(pm=('PM25','mean'),n=('PM25','size')); rain=d.groupby(d.t.dt.date).rain.sum(); seas=d.groupby(d.t.dt.date).season.first()
dd=dd[dd.n>=18].join(rain.shift(1).rename('rain_prev')).join(seas.rename('season'))
nm=dd[dd.season!='Monsoon']; out['after_rain_vs_dry_nonmonsoon']={'after_rain_mean':round(nm[nm.rain_prev>=5].pm.mean(),0),'after_dry_mean':round(nm[nm.rain_prev==0].pm.mean(),0),'n_rain_days':int((nm.rain_prev>=5).sum())}
# weekday vs weekend within smog season (Pakistan weekend = Sunday; Sat partly)
ws_=v[v.season=='Smog'].copy(); ws_['dow']=ws_.t.dt.day_name(); out['dow_smog']=ws_.groupby('dow').PM25.mean().round(0).to_dict()
# regression: log PM on weather + hour + month (smog season)
import numpy.linalg as la
r=v[(v.season=='Smog')&v.blh.notna()].copy(); y=np.log(r.PM25)
Xw=pd.DataFrame({'log_blh':np.log(r.blh),'ws':r.ws,'temp':r.temp,'rh':r.rh})
Xc=pd.get_dummies(r.t.dt.month.astype(str),prefix='m',drop_first=True).astype(float)
def r2(X):
    X=np.column_stack([np.ones(len(X)),X]); b=la.lstsq(X,y,rcond=None)[0]; e=y-X@b; return 1-e.var()/y.var(), b
out['r2_month_only']=round(r2(Xc.values)[0],3); r2w,b=r2(pd.concat([Xw,Xc],axis=1).values); out['r2_month_plus_weather']=round(r2w,3)
out['coef_log_blh']=round(b[1],3); out['coef_ws_per_kmh']=round(b[2],3)
out['spikes']=int((d.status=='Suspect spike').sum()); out['missing_hours']=int((d.status=='Missing').sum())
json.dump(out,open('analysis/numbers.json','w'),indent=1,default=str); print(json.dumps(out,indent=1,default=str))

# Rain washout, compared within the same calendar month (avoids the "rain falls in cleaner months" bias)
dd = v.groupby('date').agg(pm=('PM25', 'mean'), n=('PM25', 'size')); dd = dd[dd.n >= 18]; dd.index = pd.to_datetime(dd.index)
rain = d.groupby(d.t.dt.normalize()).rain.sum()
dd['rain_prev'] = rain.shift(1).reindex(dd.index); dd['m'] = dd.index.month
rows = []
for mth, gp in dd[dd.m.isin([10, 11, 12, 1, 2, 3])].groupby('m'):
    a, b = gp[gp.rain_prev >= 5].pm, gp[gp.rain_prev == 0].pm
    if len(a) >= 2: rows.append((len(a), a.mean() / b.mean()))
w_ = sum(r[0] for r in rows)
out['rain_next_day_ratio_month_matched'] = round(sum(r[0] * r[1] for r in rows) / w_, 2); out['rain_days_used'] = int(w_)
# Seasons with good coverage only (>= 75% of hours measured)
good = {k: v_ for k, v_ in out['smog_trend'].items() if v_['cov'] >= 75}
out['smog_trend_well_measured'] = good
json.dump(out, open('analysis/numbers.json', 'w'), indent=1, default=str)
print('rain ratio', out['rain_next_day_ratio_month_matched'], 'well-measured seasons', list(good))
