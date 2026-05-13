#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Summarize external LAMP benchmark outputs into one comparative table."""
import argparse, json
from pathlib import Path
import pandas as pd


def rd(p):
    try: return pd.read_csv(p)
    except Exception: return pd.DataFrame()


def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--root', required=True); ap.add_argument('--out', required=True); a=ap.parse_args()
    root=Path(a.root); out=Path(a.out); out.mkdir(parents=True, exist_ok=True)
    rows=[]
    for p in root.rglob('sepsis_lamp_audit_by_horizon.csv'):
        df=rd(p)
        for _,r in df.iterrows():
            rows.append({'benchmark':'PhysioNet/CinC 2019 sepsis','task_type':'ICU early warning','split_or_horizon':str(r.get('horizon_h'))+'h','valid_metric':r.get('valid_early_warning_auc'),'future_physiology_sentinel':r.get('future_physiology_sentinel_auc', r.get('leaky_future_sentinel_auc')),'oracle_sentinel':r.get('oracle_label_sentinel_auc', r.get('leaky_future_sentinel_auc')),'noise':r.get('noise_auc'),'permutation':r.get('score_permutation_auc'),'matched_delta':r.get('matched_observed_state_delta'),'source':str(p)})
    for p in root.rglob('wesad_lamp_audit.csv'):
        df=rd(p)
        for _,r in df.iterrows():
            rows.append({'benchmark':'WESAD','task_type':'wearable stress state','split_or_horizon':r.get('split'),'valid_metric':r.get('valid_auc'),'future_physiology_sentinel':'','oracle_sentinel':r.get('oracle_label_sentinel_auc'),'noise':r.get('noise_auc'),'permutation':r.get('score_permutation_auc'),'matched_delta':r.get('matched_visible_state_delta'),'source':str(p)})
    tab=pd.DataFrame(rows)
    tab.to_csv(out/'lamp_external_benchmark_panel.csv', index=False)
    report='# LAMP external benchmark panel summary\n\n## Comparative audit table\n\n'
    report += tab.to_markdown(index=False) if not tab.empty else 'No benchmark outputs found.'
    report += '\n\n## Manuscript wording\n\n> LAMP was evaluated across a heterogeneous external benchmark panel spanning ICU early warning and wearable stress-state inference. Across tasks, the audit was used not to maximize performance but to classify the evidentiary status of apparent performance: valid early signal, label-adjacent leakage, subject/session dependence, visible-state reducibility or calibration-sensitive behavior.\n'
    (out/'lamp_external_benchmark_panel_report.md').write_text(report, encoding='utf-8')
    print(json.dumps({'out':str(out),'table':str(out/'lamp_external_benchmark_panel.csv'),'report':str(out/'lamp_external_benchmark_panel_report.md'),'rows':len(tab)}, indent=2))

if __name__=='__main__': main()
