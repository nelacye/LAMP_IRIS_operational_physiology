#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Locked external LAMP evaluation wrapper for PhysioNet/CinC 2019 sepsis.
Requires external_lamp_sepsis_audit_v3.py in Downloads.
"""
import argparse, json, subprocess, sys
from pathlib import Path
import pandas as pd


def run(script, root, out, max_patients, n_null, horizons):
    cmd=[sys.executable, str(script), '--data-root', str(root), '--out', str(out), '--max-patients', str(max_patients), '--n-null', str(n_null), '--horizons', horizons]
    print('RUN:', ' '.join(cmd))
    subprocess.run(cmd, check=True)


def read(out):
    p=Path(out)/'tables'/'sepsis_lamp_audit_by_horizon.csv'
    if not p.exists():
        raise FileNotFoundError(p)
    return pd.read_csv(p)


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--audit-script', default='external_lamp_sepsis_audit_v3.py')
    ap.add_argument('--design-root', required=True)
    ap.add_argument('--holdout-root', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--max-patients-design', type=int, default=5000)
    ap.add_argument('--max-patients-holdout', type=int, default=0)
    ap.add_argument('--n-null', type=int, default=1000)
    ap.add_argument('--horizons', default='6,12,18')
    a=ap.parse_args()
    out=Path(a.out); out.mkdir(parents=True, exist_ok=True)
    d_out=out/'design'; h_out=out/'locked_holdout'
    run(a.audit_script, a.design_root, d_out, a.max_patients_design, a.n_null, a.horizons)
    run(a.audit_script, a.holdout_root, h_out, a.max_patients_holdout, a.n_null, a.horizons)
    d=read(d_out); h=read(h_out)
    d.insert(0,'cohort','design'); h.insert(0,'cohort','locked_holdout')
    combo=pd.concat([d,h], ignore_index=True)
    combo.to_csv(out/'sepsis_locked_lamp_comparison.csv', index=False)
    cols=['valid_early_warning_auc','future_physiology_sentinel_auc','oracle_label_sentinel_auc','noise_auc','score_permutation_auc','matched_observed_state_delta']
    rows=[]
    for hz in sorted(combo.horizon_h.unique()):
        dd=combo[(combo.cohort=='design') & (combo.horizon_h==hz)]
        hh=combo[(combo.cohort=='locked_holdout') & (combo.horizon_h==hz)]
        if dd.empty or hh.empty: continue
        r={'horizon_h':hz}
        for c in cols:
            if c in combo.columns:
                r[c+'_design']=float(dd[c].iloc[0]); r[c+'_holdout']=float(hh[c].iloc[0]); r[c+'_holdout_minus_design']=float(hh[c].iloc[0]-dd[c].iloc[0])
        rows.append(r)
    summ=pd.DataFrame(rows); summ.to_csv(out/'sepsis_locked_lamp_summary.csv', index=False)
    report='# Locked external LAMP evaluation: sepsis benchmark\n\n'
    report+='## Purpose\n\nSame LAMP design applied to a design cohort and a locked holdout cohort without changing horizons, scores, sentinels, matching variables or null controls.\n\n'
    report+='## Summary\n\n'+(summ.to_markdown(index=False) if not summ.empty else 'No matched horizons found.')+'\n\n'
    report+='## Manuscript wording\n\n> To move beyond single-cohort audit behavior, we applied the locked sepsis LAMP configuration to a held-out cohort without modifying horizons, features, sentinels, matching variables or null controls. This tested audit portability under a fixed analysis design rather than post hoc benchmark tuning.\n'
    (out/'sepsis_locked_lamp_report.md').write_text(report, encoding='utf-8')
    print(json.dumps({'out':str(out),'summary':str(out/'sepsis_locked_lamp_summary.csv'),'report':str(out/'sepsis_locked_lamp_report.md')}, indent=2))

if __name__=='__main__': main()
