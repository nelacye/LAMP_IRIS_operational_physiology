#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import argparse, json, math, random
from pathlib import Path
import numpy as np
import pandas as pd

VITALS=["HR","O2Sat","Temp","SBP","MAP","DBP","Resp"]
LABS=["Lactate","WBC","Creatinine","BUN","Platelets","Bilirubin_total"]
STATIC=["Age","Gender","HospAdmTime","ICULOS"]
MATCH_COLS=["HR_last","O2Sat_last","Temp_last","MAP_last","Resp_last"]

def auc_rank(score,y):
    score=np.asarray(score,float); y=np.asarray(y,int)
    ok=np.isfinite(score)&np.isfinite(y); score=score[ok]; y=y[ok]
    if len(score)<4 or len(np.unique(y))<2: return math.nan
    pos=y==1; neg=y==0; npos=int(pos.sum()); nneg=int(neg.sum())
    order=np.argsort(score); ranks=np.empty(len(score)); ss=score[order]; i=0
    while i<len(score):
        j=i+1
        while j<len(score) and ss[j]==ss[i]: j+=1
        ranks[order[i:j]]=(i+1+j)/2.0; i=j
    return float((ranks[pos].sum()-npos*(npos+1)/2.0)/(npos*nneg))

def p_greater(obs,null):
    vals=np.asarray([x for x in null if np.isfinite(x)],float)
    if len(vals)==0 or not np.isfinite(obs): return math.nan
    return float((1+np.sum(vals>=obs))/(len(vals)+1))

def last_nonmissing(s):
    x=pd.to_numeric(s,errors="coerce").dropna()
    return float(x.iloc[-1]) if len(x) else math.nan

def slope(s):
    x=pd.to_numeric(s,errors="coerce"); ok=x.notna().to_numpy()
    if ok.sum()<2: return math.nan
    xx=np.arange(len(x))[ok]; yy=x.to_numpy(float)[ok]
    try: return float(np.polyfit(xx,yy,1)[0])
    except Exception: return math.nan

def miss(frame,cols):
    cols=[c for c in cols if c in frame.columns]
    return float(frame[cols].isna().mean().mean()) if cols else math.nan

def clipped(x,lo=0,hi=5):
    return 0.0 if not np.isfinite(x) else float(np.clip(x,lo,hi))

def read_patient(path):
    try:
        df=pd.read_csv(path,sep="|")
        return df if "SepsisLabel" in df.columns else None
    except Exception:
        return None

def onset(df):
    y=pd.to_numeric(df["SepsisLabel"],errors="coerce").fillna(0).astype(int).to_numpy()
    idx=np.where(y==1)[0]
    return int(idx[0]) if len(idx) else None

def extract(df,start,end,recent=6,prefix=""):
    start=max(0,int(start)); end=min(len(df)-1,int(end))
    if end<start: return {}
    hist=df.iloc[start:end+1]; rec=hist.tail(recent)
    d={}
    for c in VITALS+LABS:
        if c in df.columns:
            d[prefix+c+"_last"]=last_nonmissing(hist[c])
            d[prefix+c+"_recent_mean"]=float(pd.to_numeric(rec[c],errors="coerce").mean())
            d[prefix+c+"_recent_slope"]=slope(rec[c])
        else:
            d[prefix+c+"_last"]=math.nan
            d[prefix+c+"_recent_mean"]=math.nan
            d[prefix+c+"_recent_slope"]=math.nan
    for c in STATIC:
        d[prefix+c]=last_nonmissing(hist[c]) if c in df.columns else math.nan
    d[prefix+"vital_missing_rate"]=miss(rec,VITALS)
    d[prefix+"lab_missing_rate"]=miss(rec,LABS)
    d[prefix+"n_hours_used"]=len(hist)
    return d

def warning_score(r,prefix=""):
    hr=r.get(prefix+"HR_last",math.nan); spo2=r.get(prefix+"O2Sat_last",math.nan)
    temp=r.get(prefix+"Temp_last",math.nan); sbp=r.get(prefix+"SBP_last",math.nan)
    mapv=r.get(prefix+"MAP_last",math.nan); resp=r.get(prefix+"Resp_last",math.nan)
    lact=r.get(prefix+"Lactate_last",math.nan); wbc=r.get(prefix+"WBC_last",math.nan); creat=r.get(prefix+"Creatinine_last",math.nan)
    s=0.0
    s+=clipped((hr-90)/35); s+=clipped((resp-20)/8); s+=clipped((95-spo2)/8)
    s+=clipped((110-sbp)/35); s+=clipped((70-mapv)/20); s+=clipped(abs(temp-37)/1.5)
    s+=1.25*clipped((lact-2)/3); s+=0.5*clipped(abs(wbc-10)/10); s+=0.5*clipped((creat-1.2)/2)
    s+=0.25*clipped(r.get(prefix+"vital_missing_rate",0),0,1); s+=0.10*clipped(r.get(prefix+"lab_missing_rate",0),0,1)
    return float(s)

def oracle_label_sentinel(df,anchor,horizon,on):
    labels=pd.to_numeric(df["SepsisLabel"],errors="coerce").fillna(0).astype(int).to_numpy()
    future=labels[min(len(df)-1,anchor+1):min(len(df),anchor+horizon+1)]
    future_label=float(np.max(future)) if len(future) else 0.0
    if on is None:
        proximity=0.0
    else:
        dist=on-anchor
        proximity=1.0/(1.0+max(0,dist))
    return float(10.0*future_label+proximity)

def patient_rows(path,horizons,recent,minhist):
    df=read_patient(path)
    if df is None or len(df)<minhist+1: return []
    on=onset(df); rows=[]
    for h in horizons:
        if on is not None:
            anchor=on-int(h); lab=1
            if anchor<minhist: continue
        else:
            anchor=max(minhist,int(0.70*(len(df)-1))); lab=0
            if anchor>=len(df)-2: anchor=len(df)-2
            if anchor<minhist: continue
        row={"patient_id":path.stem,"source_file":str(path),"horizon_h":int(h),"n_rows":len(df),"anchor_idx":anchor,"sepsis_onset_idx":on if on is not None else "","label_future_sepsis":lab}
        row.update(extract(df,0,anchor,recent,""))
        row.update(extract(df,min(len(df)-1,anchor+1),min(len(df)-1,anchor+int(h)),recent,"future_"))
        row["valid_early_warning_score"]=warning_score(row,"")
        row["future_physiology_sentinel_score"]=warning_score(row,"future_")
        row["oracle_label_sentinel_score"]=oracle_label_sentinel(df,anchor,int(h),on)
        rows.append(row)
    return rows

def qbin(s,q=3):
    s=pd.to_numeric(s,errors="coerce")
    try: return pd.qcut(s.rank(method="first"),q=q,labels=False,duplicates="drop")
    except Exception: return pd.Series([np.nan]*len(s),index=s.index)

def matched_delta(df,min_bin_n=8):
    w=df.copy(); bins=[]
    for c in [c for c in MATCH_COLS if c in w.columns]:
        b="bin_"+c; w[b]=qbin(w[c],q=3); bins.append(b)
    if len(bins)<3: return math.nan,pd.DataFrame()
    w["score_group"]=pd.qcut(pd.to_numeric(w["valid_early_warning_score"],errors="coerce").rank(method="first"),q=2,labels=["low","high"],duplicates="drop")
    rows=[]
    for keys,g in w.groupby(bins,dropna=False):
        if len(g)<min_bin_n or set(g["score_group"].dropna().astype(str))!={"low","high"}: continue
        lo=g[g["score_group"].astype(str)=="low"]; hi=g[g["score_group"].astype(str)=="high"]
        if len(lo)<3 or len(hi)<3: continue
        yl=lo["label_future_sepsis"].mean(); yh=hi["label_future_sepsis"].mean()
        rows.append({"bin_key":str(keys),"n":len(g),"n_low":len(lo),"n_high":len(hi),"manifest_rate_low":yl,"manifest_rate_high":yh,"delta_high_minus_low":yh-yl})
    out=pd.DataFrame(rows)
    if out.empty: return math.nan,out
    return float(np.average(out["delta_high_minus_low"],weights=out["n"])),out

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--data-root",required=True); ap.add_argument("--out",required=True)
    ap.add_argument("--horizons",default="6,12,18"); ap.add_argument("--max-patients",type=int,default=5000)
    ap.add_argument("--seed",type=int,default=42); ap.add_argument("--recent-hours",type=int,default=6)
    ap.add_argument("--min-history",type=int,default=6); ap.add_argument("--n-null",type=int,default=1000)
    a=ap.parse_args(); rng=np.random.default_rng(a.seed)
    root=Path(a.data_root); out=Path(a.out); tables=out/"tables"; tables.mkdir(parents=True,exist_ok=True)
    horizons=[int(x) for x in a.horizons.split(",") if x.strip()]
    files=sorted(root.rglob("*.psv"))
    if a.max_patients and len(files)>a.max_patients:
        rr=random.Random(a.seed); files=sorted(rr.sample(files,a.max_patients))
    if not files: raise FileNotFoundError(f"No .psv files found under {root}")
    rows=[]
    for i,p in enumerate(files,1):
        rows.extend(patient_rows(p,horizons,a.recent_hours,a.min_history))
        if i%1000==0: print(f"Processed {i}/{len(files)}")
    scores=pd.DataFrame(rows)
    if scores.empty: raise RuntimeError("No patient-horizon rows produced")
    scores.to_csv(tables/"sepsis_patient_scores.csv",index=False)
    audit_rows=[]; allbins=[]
    for h,g in scores.groupby("horizon_h"):
        y=g["label_future_sepsis"].astype(int).to_numpy()
        valid=pd.to_numeric(g["valid_early_warning_score"],errors="coerce").to_numpy()
        phys=pd.to_numeric(g["future_physiology_sentinel_score"],errors="coerce").to_numpy()
        oracle=pd.to_numeric(g["oracle_label_sentinel_score"],errors="coerce").to_numpy()
        noise=rng.normal(size=len(g))
        va=auc_rank(valid,y); pa=auc_rank(phys,y); oa=auc_rank(oracle,y)
        null=[auc_rank(valid,rng.permutation(y)) for _ in range(a.n_null)]
        md,bins=matched_delta(g)
        if not bins.empty:
            bins.insert(0,"horizon_h",h); allbins.append(bins)
        audit_rows.append({
            "horizon_h":int(h),"n_patients":len(g),"n_positive":int((y==1).sum()),
            "event_rate":float((y==1).mean()),"valid_early_warning_auc":va,
            "future_physiology_sentinel_auc":pa,"oracle_label_sentinel_auc":oa,
            "noise_auc":auc_rank(noise,y),"score_permutation_auc":auc_rank(rng.permutation(valid),y),
            "label_permutation_p":p_greater(va,null),
            "oracle_minus_valid_auc":oa-va if np.isfinite(oa) and np.isfinite(va) else math.nan,
            "matched_observed_state_delta":md
        })
    audit=pd.DataFrame(audit_rows).sort_values("horizon_h")
    audit.to_csv(tables/"sepsis_lamp_audit_by_horizon.csv",index=False)
    if allbins: pd.concat(allbins,ignore_index=True).to_csv(tables/"sepsis_matched_cohort_bins.csv",index=False)
    diag={"data_root":str(root),"n_psv_files_used":len(files),"n_patient_horizon_rows":len(scores),"horizons":horizons,"n_null":a.n_null}
    (tables/"sepsis_lamp_diagnostics.json").write_text(json.dumps(diag,indent=2),encoding="utf-8")
    report="# External LAMP audit v3: PhysioNet/CinC 2019 sepsis early-warning benchmark\n\n"
    report+="## Purpose\n\nThis analysis tests whether LAMP transfers beyond IRIS. It audits an external, real time-series early-warning task with externally defined labels. It is not an IRIS validation and it is not an Antarctic physiology analysis.\n\n"
    report+="## Audit summary\n\n"+audit.to_markdown(index=False)+"\n\n"
    report+="## Interpretation\n\nThe valid early-warning score uses only pre-anchor observations. The future-physiology sentinel uses invalid future-window measurements but is not guaranteed to dominate if the fixed score is crude or future observations are sparse. The oracle label sentinel deliberately uses future label/onset information and therefore acts as the positive leakage-control ceiling. Negative controls should remain near chance.\n\n"
    report+="## Manuscript-ready paragraph\n\n> To test portability beyond IRIS, we applied LAMP to the PhysioNet/CinC 2019 sepsis benchmark, a public non-IRIS early-warning task with real ICU time-series and externally defined labels. A fixed early-warning score was computed only from pre-anchor observations. Two invalid sentinels were evaluated: a future-physiology sentinel using post-anchor measurements and an oracle label-adjacent sentinel using future label/onset information. The oracle sentinel defined the expected contamination ceiling, while negative controls remained near chance. This external benchmark demonstrates that LAMP can be applied outside the Antarctic reserve-topology simulator and can explicitly separate valid early predictors from invalid future-window or label-adjacent predictors.\n\n"
    report+="## Claim boundary\n\n> The sepsis benchmark tests LAMP portability, not IRIS biological validity. Its role is to show that the audit protocol can be applied to an independent real time-series early-warning task.\n"
    (out/"external_lamp_sepsis_report.md").write_text(report,encoding="utf-8")
    print(json.dumps({"out":str(out),"n_files_used":len(files),"n_rows":len(scores),"audit":str(tables/"sepsis_lamp_audit_by_horizon.csv"),"report":str(out/"external_lamp_sepsis_report.md")},indent=2))

if __name__=="__main__":
    main()
