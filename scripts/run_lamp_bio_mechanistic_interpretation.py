#!/usr/bin/env python3
"""Mechanistic interpretation layer for LAMP-Bio.

This analysis links model-relevant marker genes from the GSE175634 pseudo-bulk
rescue test to independent mechanistic evidence. It deliberately separates
computed evidence from direct orthogonal validation:

1. Regulon/module expression in independent GSE201437 RNA-seq.
2. HOMER/g:Profiler-style target-set enrichment over top allowed features.
3. Virtual cistrome / ChIP transfer support from public cardiac/iPSC-CM assays.

The current repository does not contain matched ATAC or ChIP matrices, so ATAC
footprinting and direct ChIP validation are reported as required orthogonal
follow-ups rather than silently approximated.
"""

from __future__ import annotations

import csv
import gzip
import json
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.stats import fisher_exact, pearsonr, spearmanr


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results" / "lamp_bio_mechanistic_interpretation"
FIG_DIR = OUT / "figures"

GSE175634_CELL_TABLE = (
    ROOT
    / "results"
    / "lamp_bio_scrna"
    / "gse175634_counts"
    / "gse175634_scrna_counts_prediction_table.csv"
)
GSE175634_PANEL_CACHE = ROOT / "data" / "processed" / "gse175634" / "panel_counts_first_60000.npz"
GSE201437_COUNTS = ROOT / "data" / "raw" / "gse201437" / "GSE201437_GoPro_GeneCounts.csv.gz"

ALLOWED_FEATURE_PANELS = {
    "calcium_electrophysiology": [
        "RYR2",
        "ATP2A2",
        "PLN",
        "CASQ2",
        "CACNA1C",
        "SCN5A",
        "KCNH2",
        "KCNQ1",
        "KCND3",
        "GJA1",
    ],
    "metabolic": [
        "PPARGC1A",
        "CPT1B",
        "ACADVL",
        "HADHA",
        "NDUFA4",
        "COX5A",
        "COX6A2",
        "SLC25A4",
        "CKMT2",
        "PDK4",
    ],
}

TF_MODULES = {
    "MEF2_contractile_module": [
        "MYH6",
        "MYH7",
        "TNNT2",
        "TNNI3",
        "ACTN2",
        "MYL2",
        "MYL7",
        "TTN",
        "ATP2A2",
        "RYR2",
    ],
    "SRF_sarcomere_module": [
        "ACTN2",
        "TNNT2",
        "TNNI3",
        "MYH6",
        "MYH7",
        "MYL2",
        "MYL7",
        "TTN",
        "MYBPC3",
        "TNNC1",
    ],
    "NKX2_5_cardiac_identity_module": [
        "NKX2-5",
        "GATA4",
        "TBX5",
        "HAND2",
        "ISL1",
        "TNNT2",
        "MYH6",
        "MYH7",
        "NPPA",
        "NPPB",
    ],
    "GATA4_cardiac_program_module": [
        "GATA4",
        "NKX2-5",
        "TBX5",
        "HAND2",
        "TNNT2",
        "MYH6",
        "MYH7",
        "MYL2",
        "NPPA",
        "NPPB",
    ],
    "TBX5_electrophysiology_module": [
        "TBX5",
        "SCN5A",
        "KCNQ1",
        "KCNH2",
        "GJA1",
        "CACNA1C",
        "RYR2",
        "ATP2A2",
        "PLN",
    ],
    "PGC1A_oxidative_metabolism_module": [
        "PPARGC1A",
        "CPT1B",
        "ACADVL",
        "HADHA",
        "NDUFA4",
        "COX5A",
        "COX6A2",
        "SLC25A4",
        "CKMT2",
        "PDK4",
    ],
    "HIF1A_glycolysis_stress_module": [
        "HIF1A",
        "SLC2A1",
        "LDHA",
        "HK2",
        "PDK1",
        "PDK4",
        "VEGFA",
        "BNIP3",
    ],
    "YAP_TEAD_proliferation_module": [
        "TEAD1",
        "TEAD2",
        "YAP1",
        "WWTR1",
        "CTGF",
        "CYR61",
        "ANKRD1",
        "MKI67",
        "TOP2A",
        "PCNA",
    ],
}

TF_DISPLAY = {
    "MEF2_contractile_module": "MEF2",
    "SRF_sarcomere_module": "SRF",
    "NKX2_5_cardiac_identity_module": "NKX2-5",
    "GATA4_cardiac_program_module": "GATA4",
    "TBX5_electrophysiology_module": "TBX5",
    "PGC1A_oxidative_metabolism_module": "PPARGC1A/PGC-1A",
    "HIF1A_glycolysis_stress_module": "HIF1A",
    "YAP_TEAD_proliferation_module": "YAP/TEAD",
}

VIRTUAL_CISTROME_EVIDENCE = {
    "NKX2_5_cardiac_identity_module": [
        {
            "dataset": "GSE133833",
            "assay": "human iPSC-CM NKX2-5 ChIP-seq + RNA-seq + ATAC-seq",
            "match": "direct_human_ipsc_cm",
            "support_score": 1.0,
            "url": "https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE133833",
        },
        {
            "dataset": "GSE77548",
            "assay": "mouse differentiating cardiomyocyte NKX2-5 ChIP-exo footprints",
            "match": "cross_species_cardiac_footprint",
            "support_score": 0.7,
            "url": "https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE77548",
        },
    ],
    "GATA4_cardiac_program_module": [
        {
            "dataset": "GSE77548",
            "assay": "mouse differentiating cardiomyocyte GATA4 ChIP-exo footprints",
            "match": "cross_species_cardiac_footprint",
            "support_score": 0.7,
            "url": "https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE77548",
        },
    ],
    "TBX5_electrophysiology_module": [
        {
            "dataset": "GSE77548",
            "assay": "mouse differentiating cardiomyocyte TBX5 ChIP-exo footprints",
            "match": "cross_species_cardiac_footprint",
            "support_score": 0.7,
            "url": "https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE77548",
        },
    ],
}

DIRECT_VALIDATION_DATASETS = [
    {
        "accession": "GSE133833",
        "organism": "Homo sapiens",
        "cell_type": "iPSC-derived cardiomyocyte",
        "modalities": "RNA-seq; ATAC-seq; NKX2-5 ChIP-seq; H3K27ac ChIP-seq",
        "use": "validate whether RNA regulon/module proxy tracks direct NKX2-5 occupancy in matched iPSC-CM samples",
        "access_note": "GEO metadata/public series; raw controlled-access note must be handled before a full validation run",
        "url": "https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE133833",
    },
    {
        "accession": "GSE77548",
        "organism": "Mus musculus",
        "cell_type": "differentiating cardiac precursor/cardiomyocyte",
        "modalities": "GATA4; NKX2-5; TBX5 ChIP-exo density and footprint files",
        "use": "cross-species virtual cistrome support and footprint-method validation target",
        "access_note": "processed supplementary footprint/density files listed; large raw archive not needed for inventory",
        "url": "https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE77548",
    },
]


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    FIG_DIR.mkdir(parents=True, exist_ok=True)

    if not GSE175634_PANEL_CACHE.exists():
        raise FileNotFoundError(
            f"Missing {GSE175634_PANEL_CACHE}. Run "
            "scripts/run_gse175634_scrna_counts_lamp_bio_audit.py first."
        )

    g175_table, g175_gene_scores = load_gse175634_pseudobulk_gene_scores()
    feature_rows = feature_importance_rows(g175_table, g175_gene_scores)

    g201_z = load_gse201437_zscores()
    correlation_rows = independent_tf_correlation_rows(feature_rows, g201_z)
    enrichment_rows = motif_target_enrichment_rows(feature_rows)
    cistrome_rows = virtual_cistrome_rows()
    dossier_rows = mechanistic_dossier_rows(
        feature_rows,
        correlation_rows,
        enrichment_rows,
        cistrome_rows,
    )

    write_csv(OUT / "gse175634_feature_importance.csv", feature_rows)
    write_csv(OUT / "gse201437_feature_tf_module_correlations.csv", correlation_rows)
    write_csv(OUT / "motif_target_enrichment_proxy.csv", enrichment_rows)
    write_csv(OUT / "virtual_cistrome_evidence.csv", cistrome_rows)
    write_csv(OUT / "direct_validation_dataset_inventory.csv", DIRECT_VALIDATION_DATASETS)
    write_csv(OUT / "mechanistic_interpretation_dossier.csv", dossier_rows)

    inventory = {
        "feature_source": "GSE175634 pseudo-bulk scRNA count-derived marker genes",
        "independent_tf_source": "GSE201437 bulk RNA-seq",
        "tf_activity_definition": "mean z-scored expression of curated TF target/module genes; tested feature removed from module before correlation",
        "evidence_channels": [
            "independent_regulon_expression_proxy",
            "motif_target_enrichment_proxy",
            "virtual_cistrome_transfer",
            "direct_chip_atac_validation_inventory",
        ],
        "n_gse175634_pseudobulk_groups": int(len(g175_table)),
        "n_gse201437_samples": int(g201_z.shape[1]),
        "tf_modules": TF_MODULES,
        "tf_display_names": TF_DISPLAY,
        "allowed_feature_panels": ALLOWED_FEATURE_PANELS,
        "virtual_cistrome_evidence": VIRTUAL_CISTROME_EVIDENCE,
        "direct_validation_datasets": DIRECT_VALIDATION_DATASETS,
        "limitations": [
            "TF activity is a module-expression proxy, not direct TF binding or phospho/activity measurement.",
            "GSE201437 has only 14 bulk RNA-seq samples, so correlations are mechanistic hints, not definitive evidence.",
            "Motif evidence is a lightweight target-set enrichment proxy over curated modules, not a genome/promoter sequence scan.",
            "Virtual cistrome evidence records public assay availability and tissue/cell-type match; it does not claim promoter-level binding for a feature gene.",
            "ATAC footprinting and direct ChIP/RNA validation require importing matched peak/count matrices such as GSE133833 or GSE77548.",
            "This layer supports hypothesis prioritization; it does not turn a fragile LAMP result into a stable validation.",
        ],
    }
    (OUT / "mechanistic_interpretation_inventory.json").write_text(
        json.dumps(inventory, indent=2),
        encoding="utf-8",
    )

    plot_top_bridges(dossier_rows, FIG_DIR / "feature_tf_mechanistic_bridges.png")
    plot_feature_importance(feature_rows, FIG_DIR / "gse175634_feature_importance.png")
    write_report(
        OUT / "mechanistic_interpretation_report.md",
        dossier_rows,
        feature_rows,
        enrichment_rows,
        cistrome_rows,
    )
    print(OUT / "mechanistic_interpretation_report.md")
    return 0


def load_gse175634_pseudobulk_gene_scores() -> tuple[pd.DataFrame, dict[str, pd.Series]]:
    cell = pd.read_csv(GSE175634_CELL_TABLE)
    cache = np.load(GSE175634_PANEL_CACHE)
    library_size = cache["library_size"].astype(float)
    if len(library_size) != len(cell):
        raise ValueError(
            f"Cache length {len(library_size)} does not match cell table length {len(cell)}"
        )

    genes = sorted({gene for genes in ALLOWED_FEATURE_PANELS.values() for gene in genes})
    gene_scores: dict[str, pd.Series] = {}
    for gene in genes:
        if gene not in cache.files:
            continue
        values = cache[gene].astype(float)
        cpm = values / np.where(library_size <= 0, np.nan, library_size) * 10_000.0
        cell[gene] = zscore(np.log1p(np.nan_to_num(cpm, nan=0.0)))

    agg_spec: dict[str, Any] = {
        "structural_panel_score": "mean",
        "label_structural_maturity_high": "mean",
        "cell_id": "count",
        "individual": first_mode,
        "diffday": first_mode,
        "diffday_num": "mean",
    }
    agg_spec.update({gene: "mean" for gene in genes if gene in cell.columns})
    pb = cell.groupby("sample", as_index=False).agg(agg_spec).rename(
        columns={"cell_id": "n_cells"}
    )
    pb["label_structural_maturity_high"] = (
        pb["structural_panel_score"] >= pb["structural_panel_score"].quantile(0.70)
    ).astype(int)

    for gene in genes:
        if gene in pb.columns:
            gene_scores[gene] = pb[gene]
    return pb, gene_scores


def feature_importance_rows(
    table: pd.DataFrame,
    gene_scores: dict[str, pd.Series],
) -> list[dict[str, Any]]:
    labels = table["label_structural_maturity_high"].astype(int).tolist()
    rows: list[dict[str, Any]] = []
    for panel, genes in ALLOWED_FEATURE_PANELS.items():
        for gene in genes:
            if gene not in gene_scores:
                continue
            scores = gene_scores[gene].astype(float)
            auc = auc_score(labels, scores.tolist())
            high = scores[table["label_structural_maturity_high"] == 1]
            low = scores[table["label_structural_maturity_high"] == 0]
            rows.append(
                {
                    "feature_gene": gene,
                    "panel": panel,
                    "source_dataset": "GSE175634",
                    "source_resolution": "sample pseudo-bulk scRNA",
                    "pseudo_bulk_auc": auc,
                    "high_minus_low_delta": float(high.mean() - low.mean()),
                    "abs_high_minus_low_delta": float(abs(high.mean() - low.mean())),
                    "n_groups": int(len(table)),
                    "n_positive_groups": int(sum(labels)),
                }
            )
    return sorted(
        rows,
        key=lambda row: (
            float(row["pseudo_bulk_auc"] if row["pseudo_bulk_auc"] is not None else 0.0),
            float(row["abs_high_minus_low_delta"]),
        ),
        reverse=True,
    )


def load_gse201437_zscores() -> pd.DataFrame:
    with gzip.open(GSE201437_COUNTS, "rt", encoding="utf-8") as handle:
        frame = pd.read_csv(handle)
    sample_cols = [
        col
        for col in frame.columns
        if col.startswith(("HCNP_", "HCRP_", "LCNP_", "LCRP_"))
    ]
    counts = frame.set_index("gene_name")[sample_cols].astype(float)
    cpm = counts.divide(counts.sum(axis=0).replace(0, np.nan), axis=1) * 1_000_000.0
    log_cpm = np.log1p(cpm.fillna(0.0))
    return zscore_rows(log_cpm)


def independent_tf_correlation_rows(
    feature_rows: list[dict[str, Any]],
    g201_z: pd.DataFrame,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for feature in feature_rows:
        gene = str(feature["feature_gene"])
        if gene not in g201_z.index:
            continue
        feature_expr = g201_z.loc[gene].astype(float)
        for module_name, module_genes in TF_MODULES.items():
            usable_genes = [item for item in module_genes if item != gene and item in g201_z.index]
            if len(usable_genes) < 3:
                continue
            module_activity = g201_z.loc[usable_genes].mean(axis=0)
            pearson = pearsonr(feature_expr, module_activity)
            spearman = spearmanr(feature_expr, module_activity)
            pearson_r, pearson_p = scipy_result(pearson)
            spearman_r, spearman_p = scipy_result(spearman)
            rows.append(
                {
                    "feature_gene": gene,
                    "feature_panel": feature["panel"],
                    "independent_dataset": "GSE201437",
                    "tf_module": module_name,
                    "tf": TF_DISPLAY.get(module_name, module_name.replace("_module", "")),
                    "module_genes_used": ";".join(usable_genes),
                    "n_module_genes_used": len(usable_genes),
                    "n_samples": int(len(feature_expr)),
                    "pearson_r": float(pearson_r),
                    "pearson_p": float(pearson_p),
                    "spearman_r": float(spearman_r),
                    "spearman_p": float(spearman_p),
                    "regulon_expression_support": bool(abs(float(spearman_r)) >= 0.60 and float(spearman_p) < 0.05),
                }
            )
    return sorted(rows, key=lambda row: abs(float(row["spearman_r"])), reverse=True)


def motif_target_enrichment_rows(feature_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Lightweight HOMER/g:Profiler-style target-set enrichment proxy.

    The repository artifact stays self-contained: it tests whether top allowed
    feature genes are over-represented in curated TF target/module sets. This is
    not a promoter sequence scan and is labelled as a proxy throughout the
    report.
    """

    all_features = {str(row["feature_gene"]) for row in feature_rows}
    module_genes = {gene for genes in TF_MODULES.values() for gene in genes}
    universe = sorted(all_features | module_genes)
    top_features = {
        str(row["feature_gene"])
        for row in feature_rows
        if float(row["pseudo_bulk_auc"] or 0.0) >= 0.60
    }
    if len(top_features) < 3:
        sorted_features = sorted(
            feature_rows,
            key=lambda row: float(row["pseudo_bulk_auc"] or 0.0),
            reverse=True,
        )
        top_features = {str(row["feature_gene"]) for row in sorted_features[: max(3, len(sorted_features) // 4)]}

    rows: list[dict[str, Any]] = []
    for module_name, module_genes_list in TF_MODULES.items():
        module_set = set(module_genes_list)
        a = len(top_features & module_set)
        b = len(top_features - module_set)
        c = len((set(universe) - top_features) & module_set)
        d = len((set(universe) - top_features) - module_set)
        odds, pval = fisher_exact([[a, b], [c, d]], alternative="greater")
        rows.append(
            {
                "tf_module": module_name,
                "tf": TF_DISPLAY.get(module_name, module_name.replace("_module", "")),
                "method": "motif_target_enrichment_proxy",
                "top_feature_genes": ";".join(sorted(top_features)),
                "module_genes": ";".join(module_genes_list),
                "overlap_genes": ";".join(sorted(top_features & module_set)),
                "n_top_features": len(top_features),
                "n_universe_genes": len(universe),
                "n_overlap": a,
                "odds_ratio": float(odds) if np.isfinite(odds) else "inf",
                "fisher_p": float(pval),
                "motif_target_support": bool(a >= 1 and (float(pval) < 0.10 or a / max(1, len(top_features)) >= 0.20)),
                "caveat": "Curated target-set enrichment proxy, not promoter sequence motif scanning.",
            }
        )
    return sorted(rows, key=lambda row: (bool(row["motif_target_support"]), -float(row["fisher_p"])), reverse=True)


def virtual_cistrome_rows() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for module_name in TF_MODULES:
        evidence = VIRTUAL_CISTROME_EVIDENCE.get(module_name, [])
        if not evidence:
            rows.append(
                {
                    "tf_module": module_name,
                    "tf": TF_DISPLAY.get(module_name, module_name.replace("_module", "")),
                    "method": "virtual_cistrome_transfer",
                    "dataset": "not_found_in_current_inventory",
                    "assay": "none",
                    "match": "missing",
                    "support_score": 0.0,
                    "url": "",
                    "virtual_cistrome_support": False,
                    "caveat": "No direct cardiac/iPSC-CM cistrome support was encoded for this module.",
                }
            )
            continue
        for item in evidence:
            rows.append(
                {
                    "tf_module": module_name,
                    "tf": TF_DISPLAY.get(module_name, module_name.replace("_module", "")),
                    "method": "virtual_cistrome_transfer",
                    "dataset": item["dataset"],
                    "assay": item["assay"],
                    "match": item["match"],
                    "support_score": item["support_score"],
                    "url": item["url"],
                    "virtual_cistrome_support": bool(float(item["support_score"]) >= 0.70),
                    "caveat": "Assay-level transfer support; promoter/peak overlap has not yet been imported.",
                }
            )
    return sorted(rows, key=lambda row: float(row["support_score"]), reverse=True)


def mechanistic_dossier_rows(
    feature_rows: list[dict[str, Any]],
    correlation_rows: list[dict[str, Any]],
    enrichment_rows: list[dict[str, Any]],
    cistrome_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    correlations = pd.DataFrame(correlation_rows)
    enrichments = pd.DataFrame(enrichment_rows)
    cistromes = pd.DataFrame(cistrome_rows)
    rows: list[dict[str, Any]] = []
    for feature in feature_rows:
        gene = str(feature["feature_gene"])
        sub = correlations[correlations["feature_gene"] == gene].copy()
        if sub.empty:
            continue
        sub["abs_spearman"] = sub["spearman_r"].astype(float).abs()
        top_rows = sub.sort_values(["abs_spearman", "pearson_r"], ascending=[False, False]).head(3)
        for _, top in top_rows.iterrows():
            auc = float(feature["pseudo_bulk_auc"] or 0.0)
            rho = float(top["spearman_r"])
            pval = float(top["spearman_p"])
            module = str(top["tf_module"])
            enrichment = matching_enrichment(enrichments, module)
            cistrome = matching_cistrome(cistromes, module)
            support_count = evidence_support_count(rho, pval, enrichment, cistrome)
            status = mechanistic_status(auc, rho, pval, enrichment, cistrome)
            rows.append(
                {
                    "feature_gene": gene,
                    "feature_panel": feature["panel"],
                    "gse175634_pseudobulk_auc": auc,
                    "gse175634_high_minus_low_delta": feature["high_minus_low_delta"],
                    "independent_dataset": "GSE201437",
                    "tf": top["tf"],
                    "top_tf_module": module,
                    "top_tf_module_spearman_r": rho,
                    "top_tf_module_spearman_p": pval,
                    "top_tf_module_pearson_r": float(top["pearson_r"]),
                    "module_genes_used": top["module_genes_used"],
                    "regulon_expression_support": bool(abs(rho) >= 0.60 and pval < 0.05),
                    "motif_target_support": bool(enrichment.get("motif_target_support", False)),
                    "motif_target_overlap_genes": enrichment.get("overlap_genes", ""),
                    "motif_target_fisher_p": enrichment.get("fisher_p", ""),
                    "virtual_cistrome_support": bool(cistrome.get("virtual_cistrome_support", False)),
                    "virtual_cistrome_dataset": cistrome.get("dataset", ""),
                    "virtual_cistrome_match": cistrome.get("match", ""),
                    "virtual_cistrome_support_score": cistrome.get("support_score", ""),
                    "direct_chip_or_atac_validation": direct_validation_status(module),
                    "mechanistic_support_count": support_count,
                    "mechanistic_status": status,
                    "interpretation": interpretation_sentence(gene, feature, top, status, enrichment, cistrome),
                }
            )
    return sorted(
        rows,
        key=lambda row: (
            status_rank(str(row["mechanistic_status"])),
            int(row["mechanistic_support_count"]),
            abs(float(row["top_tf_module_spearman_r"])),
            float(row["gse175634_pseudobulk_auc"]),
        ),
        reverse=True,
    )


def mechanistic_status(
    auc: float,
    rho: float,
    pval: float,
    enrichment: dict[str, Any],
    cistrome: dict[str, Any],
) -> str:
    support_count = evidence_support_count(rho, pval, enrichment, cistrome)
    if auc >= 0.60 and support_count == 3:
        return "three_channel_mechanistic_bridge"
    if auc >= 0.60 and support_count == 2:
        return "two_channel_mechanistic_bridge"
    if auc >= 0.60 and support_count == 1:
        return "single_channel_mechanistic_hint"
    if abs(rho) >= 0.60 and pval < 0.05:
        return "tf_link_without_strong_lamp_feature"
    return "not_supported_yet"


def evidence_support_count(
    rho: float,
    pval: float,
    enrichment: dict[str, Any],
    cistrome: dict[str, Any],
) -> int:
    count = 0
    if abs(rho) >= 0.60 and pval < 0.05:
        count += 1
    if bool(enrichment.get("motif_target_support", False)):
        count += 1
    if bool(cistrome.get("virtual_cistrome_support", False)):
        count += 1
    return count


def matching_enrichment(enrichments: pd.DataFrame, module: str) -> dict[str, Any]:
    if enrichments.empty:
        return {}
    sub = enrichments[enrichments["tf_module"] == module]
    if sub.empty:
        return {}
    return sub.iloc[0].to_dict()


def matching_cistrome(cistromes: pd.DataFrame, module: str) -> dict[str, Any]:
    if cistromes.empty:
        return {}
    sub = cistromes[cistromes["tf_module"] == module].copy()
    if sub.empty:
        return {}
    sub["support_score"] = sub["support_score"].astype(float)
    return sub.sort_values("support_score", ascending=False).iloc[0].to_dict()


def direct_validation_status(module: str) -> str:
    if module == "NKX2_5_cardiac_identity_module":
        return "available_not_yet_run: GSE133833 matched human iPSC-CM RNA-seq/ATAC/NKX2-5 ChIP-seq"
    if module in {"GATA4_cardiac_program_module", "TBX5_electrophysiology_module"}:
        return "available_not_yet_run: GSE77548 cardiac ChIP-exo footprints; cross-species validation"
    return "not_available_in_current_inventory"


def interpretation_sentence(
    gene: str,
    feature: dict[str, Any],
    top: pd.Series,
    status: str,
    enrichment: dict[str, Any],
    cistrome: dict[str, Any],
) -> str:
    motif = "yes" if bool(enrichment.get("motif_target_support", False)) else "no"
    cistrome_support = "yes" if bool(cistrome.get("virtual_cistrome_support", False)) else "no"
    return (
        f"{gene} has GSE175634 pseudo-bulk AUC {float(feature['pseudo_bulk_auc']):.3f} "
        f"for the structural endpoint and correlates with {top['tf_module']} in "
        f"independent GSE201437 RNA-seq (Spearman r={float(top['spearman_r']):.3f}, "
        f"p={float(top['spearman_p']):.3g}); motif-target support={motif}; "
        f"virtual-cistrome support={cistrome_support}; status={status}."
    )


def plot_top_bridges(rows: list[dict[str, Any]], path: Path) -> None:
    top = rows[:12]
    labels = [f"{row['feature_gene']}\n{row['tf']}" for row in top]
    x = np.arange(len(top))
    aucs = [float(row["gse175634_pseudobulk_auc"]) for row in top]
    rhos = [float(row["top_tf_module_spearman_r"]) for row in top]
    support = [float(row["mechanistic_support_count"]) / 3.0 for row in top]
    fig, ax = plt.subplots(figsize=(12, 5.2))
    ax.bar(x - 0.18, aucs, width=0.36, label="GSE175634 feature AUC", color="#222222")
    ax.bar(x + 0.18, rhos, width=0.36, label="GSE201437 regulon Spearman r", color="#888888")
    ax.scatter(x, support, marker="s", s=42, color="white", edgecolor="black", label="mechanistic channels / 3")
    ax.axhline(0.60, color="black", linestyle="--", linewidth=1)
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=35, ha="right", fontsize=8)
    ax.set_ylim(-0.1, 1.05)
    ax.set_title("Multi-evidence mechanistic bridge candidates")
    ax.legend(frameon=False)
    plt.tight_layout()
    plt.savefig(path, dpi=180)
    plt.close()


def plot_feature_importance(rows: list[dict[str, Any]], path: Path) -> None:
    frame = pd.DataFrame(rows).sort_values("pseudo_bulk_auc", ascending=False)
    colors = ["#333333" if panel == "calcium_electrophysiology" else "#888888" for panel in frame["panel"]]
    fig, ax = plt.subplots(figsize=(10, 4.5))
    ax.bar(frame["feature_gene"], frame["pseudo_bulk_auc"].astype(float), color=colors, edgecolor="black")
    ax.axhline(0.60, color="black", linestyle="--", linewidth=1)
    ax.set_ylim(0, 1.0)
    ax.set_ylabel("Pseudo-bulk AUC")
    ax.set_title("GSE175634 allowed feature-gene importance")
    ax.tick_params(axis="x", rotation=45)
    plt.tight_layout()
    plt.savefig(path, dpi=180)
    plt.close()


def write_report(
    path: Path,
    dossier_rows: list[dict[str, Any]],
    feature_rows: list[dict[str, Any]],
    enrichment_rows: list[dict[str, Any]],
    cistrome_rows: list[dict[str, Any]],
) -> None:
    candidate_rows = [
        row
        for row in dossier_rows
        if row["mechanistic_status"]
        in {
            "three_channel_mechanistic_bridge",
            "two_channel_mechanistic_bridge",
            "single_channel_mechanistic_hint",
        }
    ]
    lines = [
        "# LAMP-Bio Mechanistic Interpretation Layer",
        "",
        "This layer moves beyond feature importance. It asks whether allowed",
        "GSE175634 pseudo-bulk feature genes that help separate structural maturity",
        "also have mechanistic support in independent or orthogonal evidence channels.",
        "",
        "The current computed evidence channels are:",
        "",
        "1. independent regulon/module expression in `GSE201437` RNA-seq;",
        "2. motif/target-set enrichment proxy over top allowed feature genes;",
        "3. virtual cistrome transfer support from public cardiac/iPSC-CM ChIP or footprint datasets.",
        "",
        "Important caveat: TF activity here still does not mean direct TF binding,",
        "nuclear localization, phosphorylation, or perturbation. The regulon channel",
        "uses a curated module-expression proxy, and the tested feature gene is",
        "removed from each module before correlation. Motif enrichment is a",
        "lightweight target-set proxy, not a full promoter scan.",
        "",
        "## Candidate Bridges",
        "",
        "| Feature | Panel | TF | Feature AUC | Regulon r | Regulon p | Motif | Cistrome | Mechanistic evidence | Status |",
        "| --- | --- | --- | ---: | ---: | ---: | --- | --- | ---: | --- |",
    ]
    for row in candidate_rows[:12]:
        lines.append(
            "| {feature_gene} | {feature_panel} | {tf} | {auc:.3f} | {rho:.3f} | {p:.3g} | {motif} | {cistrome} | {support_count}/3 | {status} |".format(
                feature_gene=row["feature_gene"],
                feature_panel=row["feature_panel"],
                tf=row["tf"],
                auc=float(row["gse175634_pseudobulk_auc"]),
                rho=float(row["top_tf_module_spearman_r"]),
                p=float(row["top_tf_module_spearman_p"]),
                motif="yes" if row["motif_target_support"] else "no",
                cistrome="yes" if row["virtual_cistrome_support"] else "no",
                support_count=int(row["mechanistic_support_count"]),
                status=row["mechanistic_status"],
            )
        )
    if not candidate_rows:
        lines.append("| None | - | - | - | - | - | - | - | 0/3 | no bridge candidates under current thresholds |")

    top_feature = max(feature_rows, key=lambda row: float(row["pseudo_bulk_auc"] or 0.0))
    supported_enrichments = [row for row in enrichment_rows if row.get("motif_target_support")]
    supported_cistromes = [row for row in cistrome_rows if row.get("virtual_cistrome_support")]
    lines.extend(
        [
            "",
            "## Direct Validation Inventory",
            "",
            "| Accession | Organism | Cell type | Modalities | LAMP use | Access note |",
            "| --- | --- | --- | --- | --- | --- |",
        ]
    )
    for row in DIRECT_VALIDATION_DATASETS:
        lines.append(
            "| [{accession}]({url}) | {organism} | {cell_type} | {modalities} | {use} | {access_note} |".format(**row)
        )

    lines.extend(
        [
            "",
            "These datasets are not used as final biological proof in this artifact.",
            "`GSE133833` is the strongest next validation target because it contains",
            "human iPSC-CM RNA-seq, ATAC-seq, and NKX2-5 ChIP-seq in one design.",
            "`GSE77548` supplies cardiac GATA4/NKX2-5/TBX5 ChIP-exo footprints but",
            "is mouse and therefore cross-species support.",
            "",
            "## Reading",
            "",
            f"- Top allowed GSE175634 feature by pseudo-bulk AUC: `{top_feature['feature_gene']}` "
            f"({float(top_feature['pseudo_bulk_auc']):.3f}).",
            f"- Motif/target-set proxy supports {len(supported_enrichments)} TF modules.",
            f"- Virtual cistrome inventory supports {len(supported_cistromes)} TF modules.",
            "- Mechanistic bridge candidates should be treated as hypotheses for",
            "  follow-up perturbation or orthogonal TF-activity measurement.",
            "- This layer does not rescue a failed LAMP audit by itself; it explains",
            "  where a fragile rescued signal may be biologically anchored.",
            "- Stronger next version: import GSE133833 peaks/counts and test whether",
            "  the RNA regulon proxy tracks direct NKX2-5 ChIP/ATAC occupancy.",
            "",
            "## Output Files",
            "",
            f"- Feature importance: `{relpath(OUT / 'gse175634_feature_importance.csv')}`",
            f"- All feature/TF correlations: `{relpath(OUT / 'gse201437_feature_tf_module_correlations.csv')}`",
            f"- Motif target enrichment proxy: `{relpath(OUT / 'motif_target_enrichment_proxy.csv')}`",
            f"- Virtual cistrome evidence: `{relpath(OUT / 'virtual_cistrome_evidence.csv')}`",
            f"- Direct validation inventory: `{relpath(OUT / 'direct_validation_dataset_inventory.csv')}`",
            f"- Dossier: `{relpath(OUT / 'mechanistic_interpretation_dossier.csv')}`",
            f"- Figure: `{relpath(FIG_DIR / 'feature_tf_mechanistic_bridges.png')}`",
            f"- Figure: `{relpath(FIG_DIR / 'gse175634_feature_importance.png')}`",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def auc_score(labels: list[int], scores: list[float]) -> float | None:
    n_pos = sum(labels)
    n_neg = len(labels) - n_pos
    if n_pos == 0 or n_neg == 0:
        return None
    ordered = sorted(enumerate(scores), key=lambda item: item[1])
    ranks = [0.0] * len(scores)
    i = 0
    while i < len(ordered):
        j = i + 1
        while j < len(ordered) and ordered[j][1] == ordered[i][1]:
            j += 1
        avg = (i + 1 + j) / 2.0
        for k in range(i, j):
            ranks[ordered[k][0]] = avg
        i = j
    pos_rank_sum = sum(rank for rank, label in zip(ranks, labels) if label == 1)
    return float((pos_rank_sum - n_pos * (n_pos + 1) / 2.0) / (n_pos * n_neg))


def zscore(values: np.ndarray | pd.Series) -> np.ndarray:
    arr = np.asarray(values, dtype=float)
    sd = np.nanstd(arr, ddof=1)
    if not np.isfinite(sd) or sd == 0:
        return np.zeros_like(arr)
    return (arr - np.nanmean(arr)) / sd


def zscore_rows(frame: pd.DataFrame) -> pd.DataFrame:
    mean = frame.mean(axis=1)
    sd = frame.std(axis=1).replace(0, np.nan)
    return frame.sub(mean, axis=0).divide(sd, axis=0).fillna(0.0)


def first_mode(series: pd.Series) -> Any:
    mode = series.mode(dropna=True)
    if len(mode):
        return mode.iloc[0]
    return series.iloc[0]


def status_rank(status: str) -> int:
    ranks = {
        "three_channel_mechanistic_bridge": 5,
        "two_channel_mechanistic_bridge": 4,
        "single_channel_mechanistic_hint": 3,
        "tf_link_without_strong_lamp_feature": 2,
        "not_supported_yet": 1,
    }
    return ranks.get(status, 0)


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        if not rows:
            handle.write("")
            return
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def relpath(path: Path) -> str:
    return str(path.resolve().relative_to(ROOT.resolve())).replace("\\", "/")


def scipy_result(result: Any) -> tuple[float, float]:
    if hasattr(result, "statistic") and hasattr(result, "pvalue"):
        return float(result.statistic), float(result.pvalue)
    return float(result[0]), float(result[1])


if __name__ == "__main__":
    raise SystemExit(main())
