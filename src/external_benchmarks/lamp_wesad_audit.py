#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""External LAMP audit for WESAD wearable stress/affect detection.
Searches recursively for WESAD subject .pkl files.
Task: stress (label 2) vs baseline/amusement (labels 1/3).
Not SOTA. This is an audit-behavior baseline.
"""
import argparse, json, math, pickle, random
from pathlib import Path
import numpy as np
import pandas as pd


def auc_rank(score,y):
    score=np.asarray(score,float); y=np.asarray(y,int); ok=np.isfinite(score)&np.isfinite(y); score=score[ok]; y=y[ok]
    if len(score)<4 or len(np.unique(y))<2: return math.nan
    pos=y==1; neg=y==0; npos=int(pos.sum()); nneg=int(neg.sum()); order=np.argsort(score); ranks=np.empty(len(score)); ss=score[order]; i=0
    while i<len(score):
        j=i+1
        while j<len(score) and ss[j]==ss[i]: j+=1
        ranks[order[i:j]]=(i+1+j)/2.0; i=j
    return float((ranks[pos].sum()-npos*(npos+1)/2.0)/(npos*nneg))

def p_greater(obs,null):
    vals=np.asarray([x for x in null if np.isfinite(x)],float)
    return math.nan if len(vals)==0 or not np.isfinite(obs) else float((1+np.sum(vals>=obs))/(len(vals)+1))

def load(path):
    with open(path,'rb') as f: return pickle.load(f, encoding='latin1')

def sig(data,name):
    s=data.get('signal',{})
    for loc in ['chest','wrist']:
        if loc in s and name in s[loc]:
            x=np.asarray(s[loc][name])
            if x.ndim==2 and x.shape[1]==1: x=x[:,0]
            return x.astype(float)
    return None

def summ(x):
    x=np.asarray(x,float); x=x[np.isfinite(x)]
    if len(x)==0: return (math.nan,math.nan,math.nan)
    return float(np.mean(x)), float(np.std(x)), float(np.quantile(x,.75)-np.quantile(x,.25))

def subject_rows(path, win=7000, stride=7000, maxwin=500):
    d=load(path); labels=np.asarray(d.get('label',[])); n=len(labels)
    if n==0: return []
    eda=sig(d,'EDA'); temp=sig(d,'Temp'); resp=sig(d,'Resp'); ecg=sig(d,'ECG'); acc=sig(d,'ACC')
    rows=[]; subj=path.stem
    for start in range(0, max(0,n-win), stride):
        end=start+win; lab=labels[start:end]
        vals,cnts=np.unique(lab, return_counts=True); maj=int(vals[np.argmax(cnts)])
        if maj not in [1,2,3]: continue
        row={'subject':subj,'source_file':str(path),'start':start,'end':end,'majority_label':maj,'label_stress':1 if maj==2 else 0}
        for name,arr in [('EDA',eda),('Temp',temp),('Resp',resp),('ECG',ecg)]:
            if arr is None: m=s=i=math.nan
            else: m,s,i=summ(arr[start:min(end,len(arr))])
            row[f'{name}_mean']=m; row[f'{name}_std']=s; row[f'{name}_iqr']=i
        if acc is not None:
            aa=np.asarray(acc)
            if aa.ndim==2:
                seg=aa[start:min(end,aa.shape[0]),:]; mag=np.sqrt(np.sum(seg.astype(float)**2,axis=1))
            else: mag=aa[start:min(end,len(aa))]
            m,s,i=summ(mag)
        else: m=s=i=math.nan
        row['ACCmag_mean']=m; row['ACCmag_std']=s; row['ACCmag_iqr']=i
        row['oracle_label_sentinel_score']=float(row['label_stress'])
        rows.append(row)
        if len(rows)>=maxwin: break
    return rows

def z(v):
    v=pd.to_numeric(v, errors='coerce'); sd=v.std(); sd=sd if np.isfinite(sd) and sd>0 else 1.0
    return ((v-v.mean())/sd).fillna(0.0)

def score(df):
    w=df.copy()
    for c in ['EDA_mean','EDA_std','Resp_std','ACCmag_std','Temp_mean']:
        if c not in w: w[c]=np.nan
        w['z_'+c]=z(w[c])
    w['valid_wearable_stress_score']=w.z_EDA_mean + .5*w.z_EDA_std + .5*w.z_Resp_std + .25*w.z_ACCmag_std - .25*w.z_Temp_mean
    return w

def qbin(s,q=3):
    s=pd.to_numeric(s,errors='coerce')
    try: return pd.qcut(s.rank(method='first'),q=q,labels=False,duplicates='drop')
    except Exception: return pd.Series([np.nan]*len(s), index=s.index)

def matched_delta(df):
    w=df.copy(); cols=[c for c in ['ACCmag_std','Temp_mean','EDA_mean'] if c in w.columns]
    if len(cols)<2: return math.nan,pd.DataFrame()
    bins=[]
    for c in cols:
        b='bin_'+c; w[b]=qbin(w[c]); bins.append(b)
    w['score_group']=pd.qcut(pd.to_numeric(w.valid_wearable_stress_score,errors='coerce').rank(method='first'),q=2,labels=['low','high'],duplicates='drop')
    rows=[]
    for keys,g in w.groupby(bins,dropna=False):
        if len(g)<8 or set(g.score_group.dropna().astype(str))!={'low','high'}: continue
        lo=g[g.score_group.astype(str)=='low']; hi=g[g.score_group.astype(str)=='high']
        if len(lo)<3 or len(hi)<3: continue
        yl=lo.label_stress.mean(); yh=hi.label_stress.mean()
        rows.append({'bin_key':str(keys),'n':len(g),'stress_rate_low':yl,'stress_rate_high':yh,'delta_high_minus_low':yh-yl})
    out=pd.DataFrame(rows)
    return (math.nan,out) if out.empty else (float(np.average(out.delta_high_minus_low, weights=out.n)), out)

def audit(df, name, subjects, rng, n_null):
    t=df[df.subject.isin(subjects)].copy(); y=t.label_stress.astype(int).to_numpy(); sc=pd.to_numeric(t.valid_wearable_stress_score,errors='coerce').to_numpy(); oracle=t.oracle_label_sentinel_score.to_numpy(float)
    obs=auc_rank(sc,y); null=[auc_rank(sc,rng.permutation(y)) for _ in range(n_null)]; md,bins=matched_delta(t)
    return {'split':name,'n_windows':len(t),'n_subjects':len(set(t.subject)),'n_stress':int((y==1).sum()),'stress_rate':float((y==1).mean()) if len(y) else math.nan,'valid_auc':obs,'oracle_label_sentinel_auc':auc_rank(oracle,y),'noise_auc':auc_rank(rng.normal(size=len(t)),y),'score_permutation_auc':auc_rank(rng.permutation(sc),y),'label_permutation_p':p_greater(obs,null),'matched_visible_state_delta':md}, bins

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--data-root',required=True); ap.add_argument('--out',required=True); ap.add_argument('--max-subjects',type=int,default=0); ap.add_argument('--n-null',type=int,default=1000); ap.add_argument('--seed',type=int,default=42); ap.add_argument('--window-samples',type=int,default=7000); ap.add_argument('--stride-samples',type=int,default=7000); a=ap.parse_args()
    out=Path(a.out); tables=out/'tables'; tables.mkdir(parents=True, exist_ok=True); rng=np.random.default_rng(a.seed)
    files=sorted(Path(a.data_root).rglob('*.pkl'))
    if a.max_subjects and len(files)>a.max_subjects: files=files[:a.max_subjects]
    if not files: raise FileNotFoundError(f'No WESAD .pkl files found under {a.data_root}')
    rows=[]
    for f in files:
        try: rows.extend(subject_rows(f,a.window_samples,a.stride_samples))
        except Exception as e: print('ERROR',f,e)
    df=score(pd.DataFrame(rows))
    if df.empty: raise RuntimeError('No WESAD windows extracted')
    df.to_csv(tables/'wesad_window_features.csv', index=False)
    subjects=sorted(df.subject.unique())
    if len(subjects)<4: raise RuntimeError('Need at least 4 subjects')
    rr=random.Random(a.seed); shuffled=subjects[:]; rr.shuffle(shuffled); cut=max(1,int(.70*len(shuffled))); holdout=shuffled[cut:]
    # random window reference uses all subjects in random last 30%, deliberately less strict
    audit_rows=[]; bins_all=[]
    for name,subs in [('subject_heldout', holdout), ('all_subject_reference', subjects)]:
        res,bins=audit(df,name,subs,rng,a.n_null); audit_rows.append(res)
        if not bins.empty: bins.insert(0,'split',name); bins_all.append(bins)
    aud=pd.DataFrame(audit_rows); aud.to_csv(tables/'wesad_lamp_audit.csv', index=False)
    if bins_all: pd.concat(bins_all,ignore_index=True).to_csv(tables/'wesad_matched_bins.csv', index=False)
    diag={'n_files':len(files),'n_windows':len(df),'subjects':subjects,'holdout_subjects':holdout}; (tables/'wesad_diagnostics.json').write_text(json.dumps(diag,indent=2),encoding='utf-8')
    report='# External LAMP audit: WESAD wearable stress benchmark\n\n## Audit summary\n\n'+aud.to_markdown(index=False)+'\n\n## Manuscript wording\n\n> WESAD was used as a wearable physiology benchmark for latent affect/stress inference. LAMP compared subject-held-out performance with an all-subject reference, evaluated permutation and noise controls, added an oracle label sentinel and tested whether the wearable stress score retained signal after matching on visible motion, temperature and electrodermal proxies.\n'
    (out/'wesad_lamp_report.md').write_text(report, encoding='utf-8')
    print(json.dumps({'out':str(out),'audit':str(tables/'wesad_lamp_audit.csv'),'report':str(out/'wesad_lamp_report.md')}, indent=2))
if __name__=='__main__': main()
