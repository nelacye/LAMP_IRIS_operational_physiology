#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
IRIS Radiation Channel Audit

Purpose
-------
Addresses the critique:
"Cosmic rays as a forcing channel are theoretically weak."

This script does not pretend that NMDB count rate is individual absorbed dose.
It explicitly treats NMDB/SOPO as an environmental cosmic-ray variability proxy
and quantifies how much the model depends on the radiation channel.

Inputs:
- NMDB processed or raw txt file under real_data/radiation_proxy/nmdb
- IRIS station run folders with stress_protocol.csv and population_summary.csv where available

Outputs:
- radiation_channel_audit_report.md
- radiation_proxy_summary.csv
- station_radiation_sensitivity_table.csv

Use:
py .\iris_radiation_channel_audit.py --real-data .\real_data --station-runs .\power_run\results_bashmak_strong\station_runs --out .\radiation_channel_audit
"""

from __future__ import annotations
import argparse, json, math, re
from pathlib import Path
import numpy as np
import pandas as pd


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--real-data", required=True)
    p.add_argument("--station-runs", default=None)
    p.add_argument("--out", required=True)
    return p.parse_args()


def read_nmdb(root: Path):
    files = list((root/"radiation_proxy"/"nmdb").glob("*.txt"))
    if not files:
        return pd.DataFrame()
    fp = files[0]
    rows = []
    with fp.open("r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            s=line.strip()
            if not s or s.startswith("#") or "start_date_time" in s:
                continue
            if ";" in s:
                parts=s.split(";")
                if len(parts)>=2:
                    rows.append((parts[0].strip(), parts[1].strip()))
    df=pd.DataFrame(rows, columns=["start_date_time","MCORR_E"])
    df["start_date_time"]=pd.to_datetime(df["start_date_time"], errors="coerce")
    df["MCORR_E"]=pd.to_numeric(df["MCORR_E"], errors="coerce")
    df=df.dropna()
    med=df["MCORR_E"].median(); sd=df["MCORR_E"].std()
    df["relative_to_median"]=(df["MCORR_E"]-med)/med
    df["z_positive"]=np.maximum(0, (df["MCORR_E"]-med)/(sd if sd else 1))
    df["iris_radiation_proxy"]=0.05+0.30*np.clip(df["z_positive"]/3,0,1)
    return df


def station_summaries(station_root: Path):
    rows=[]
    if not station_root or not station_root.exists():
        return pd.DataFrame()
    for d in sorted([x for x in station_root.iterdir() if x.is_dir()]):
        sp=d/"stress_protocol.csv"
        ps=d/"population_summary.csv"
        row={"station":d.name.replace("_"," ")}
        if sp.exists():
            stress=pd.read_csv(sp)
            for col in ["radiation","cold","hypoxia","workload","sleep"]:
                if col in stress.columns:
                    row[f"{col}_mean"]=float(pd.to_numeric(stress[col], errors="coerce").mean())
                    row[f"{col}_max"]=float(pd.to_numeric(stress[col], errors="coerce").max())
                    row[f"{col}_std"]=float(pd.to_numeric(stress[col], errors="coerce").std())
            if "radiation" in stress.columns:
                rad=pd.to_numeric(stress["radiation"], errors="coerce")
                total = 0
                for col in ["cold","hypoxia","workload","sleep","radiation"]:
                    if col in stress.columns:
                        total += pd.to_numeric(stress[col], errors="coerce").abs().sum()
                row["radiation_abs_fraction_of_total_forcing"]=float(rad.abs().sum()/total) if total else math.nan
        if ps.exists():
            pop=pd.read_csv(ps)
            for col in ["min_reserve_margin","peak_reserve_anisotropy","false_stability"]:
                if col in pop.columns:
                    row[f"{col}_mean"]=float(pd.to_numeric(pop[col], errors="coerce").mean())
        rows.append(row)
    return pd.DataFrame(rows)


def main():
    args=parse_args()
    out=Path(args.out); tables=out/"tables"; out.mkdir(parents=True, exist_ok=True); tables.mkdir(exist_ok=True)
    root=Path(args.real_data)
    nm=read_nmdb(root)
    st=station_summaries(Path(args.station_runs)) if args.station_runs else pd.DataFrame()
    nm.to_csv(tables/"radiation_proxy_summary.csv", index=False)
    st.to_csv(tables/"station_radiation_sensitivity_table.csv", index=False)

    report=[]
    report.append("# IRIS radiation-channel audit\n")
    report.append("## Position\n")
    report.append("NMDB/SOPO neutron-monitor data are used as an environmental cosmic-ray variability proxy, not as individual absorbed dose, organ dose, or a direct physiological radiation-stress measurement.\n")
    if not nm.empty:
        report.append("## NMDB proxy summary\n")
        desc=nm["MCORR_E"].describe().to_frame().T
        report.append(desc.to_markdown(index=False))
        report.append("\n## IRIS radiation proxy mapping summary\n")
        desc2=nm["iris_radiation_proxy"].describe().to_frame().T
        report.append(desc2.to_markdown(index=False))
    if not st.empty:
        report.append("\n## Station forcing contribution summary\n")
        cols=[c for c in st.columns if c in ["station","radiation_mean","radiation_max","radiation_std","radiation_abs_fraction_of_total_forcing"]]
        report.append(st[cols].to_markdown(index=False))
    report.append("\n## Required manuscript correction\n")
    report.append("Radiation is retained as an environmental forcing channel only. The paper must not claim dose-response estimation or individual biological radiation injury. A sensitivity analysis should report whether removing or down-weighting this channel materially changes latent-topology results.\n")
    report.append("\n## Stronger phrasing\n")
    report.append("The neutron-monitor channel is used to represent time-varying polar cosmic-ray environment, analogous to an exogenous operational stressor, not to estimate absorbed dose. Its role is therefore tested through sensitivity and ablation rather than treated as a validated cardiovascular radiation pathway.\n")
    (out/"radiation_channel_audit_report.md").write_text("\n".join(report), encoding="utf-8")
    print(json.dumps({"out":str(out),"nmdb_rows":len(nm),"station_rows":len(st)}, indent=2))


if __name__=="__main__":
    main()
