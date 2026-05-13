# make_lamp_audit_separation_panel.py
# -*- coding: utf-8 -*-

from pathlib import Path
import math
import pandas as pd
import matplotlib.pyplot as plt


def auc_ci_hanley_mcneil(auc: float, n_pos: int, n_neg: int, z: float = 1.96):
    """
    Approximate 95% CI for AUC using Hanley & McNeil-style variance.
    Good enough for a manuscript figure scaffold.
    """
    auc = float(max(0.0, min(1.0, auc)))
    n_pos = int(n_pos)
    n_neg = int(n_neg)

    if n_pos <= 0 or n_neg <= 0:
        return auc, auc

    # handle degenerate edges
    if auc <= 0.0:
        return 0.0, 0.0
    if auc >= 1.0:
        return 1.0, 1.0

    q1 = auc / (2.0 - auc)
    q2 = 2.0 * auc * auc / (1.0 + auc)

    var = (
        auc * (1.0 - auc)
        + (n_pos - 1) * (q1 - auc * auc)
        + (n_neg - 1) * (q2 - auc * auc)
    ) / (n_pos * n_neg)

    var = max(var, 0.0)
    se = math.sqrt(var)

    lo = max(0.0, auc - z * se)
    hi = min(1.0, auc + z * se)
    return lo, hi


def build_example_data() -> pd.DataFrame:
    """
    Uses the numbers you already reported in the conversation.
    You can edit/extend this table later.
    """

    rows = [
        # ---------------------------
        # IRIS / Neumayer layer
        # n = 25, positives = 9, negatives = 16
        # ---------------------------
        {
            "dataset": "IRIS / Neumayer III",
            "label": "HR-only comparator",
            "auc": 0.638889,
            "n_pos": 9,
            "n_neg": 16,
            "audit_state": "Observed-state / conventional",
            "order": 1,
        },
        {
            "dataset": "IRIS / Neumayer III",
            "label": "Regularized HRV model",
            "auc": 0.847222,
            "n_pos": 9,
            "n_neg": 16,
            "audit_state": "Observed-state / conventional",
            "order": 2,
        },
        {
            "dataset": "IRIS / Neumayer III",
            "label": "IRIS balanced score",
            "auc": 0.923611,
            "n_pos": 9,
            "n_neg": 16,
            "audit_state": "Latent audited signal",
            "order": 3,
        },

        # ---------------------------
        # PhysioNet/CinC 2019 sepsis
        # 6h horizon from your locked/5k audit
        # n_patients = 4869, positives = 280, negatives = 4589
        # ---------------------------
        {
            "dataset": "PhysioNet Sepsis",
            "label": "Noise control",
            "auc": 0.516082,
            "n_pos": 280,
            "n_neg": 4589,
            "audit_state": "Null / negative controls",
            "order": 1,
        },
        {
            "dataset": "PhysioNet Sepsis",
            "label": "Score permutation",
            "auc": 0.474066,
            "n_pos": 280,
            "n_neg": 4589,
            "audit_state": "Null / negative controls",
            "order": 2,
        },
        {
            "dataset": "PhysioNet Sepsis",
            "label": "Valid early-warning score",
            "auc": 0.641621,
            "n_pos": 280,
            "n_neg": 4589,
            "audit_state": "Latent audited signal",
            "order": 3,
        },
        {
            "dataset": "PhysioNet Sepsis",
            "label": "Future-physiology sentinel",
            "auc": 0.630712,
            "n_pos": 280,
            "n_neg": 4589,
            "audit_state": "Sentinel / contamination ceiling",
            "order": 4,
        },
        {
            "dataset": "PhysioNet Sepsis",
            "label": "Oracle-label sentinel",
            "auc": 1.000000,
            "n_pos": 280,
            "n_neg": 4589,
            "audit_state": "Sentinel / contamination ceiling",
            "order": 5,
        },
    ]

    df = pd.DataFrame(rows)
    ci = df.apply(lambda r: auc_ci_hanley_mcneil(r["auc"], r["n_pos"], r["n_neg"]), axis=1)
    df["ci_low"] = [x[0] for x in ci]
    df["ci_high"] = [x[1] for x in ci]
    return df


def plot_panel(ax, sub: pd.DataFrame, title: str):
    sub = sub.sort_values("order").reset_index(drop=True)
    y = range(len(sub))

    state_to_marker = {
        "Null / negative controls": "o",
        "Observed-state / conventional": "s",
        "Latent audited signal": "D",
        "Sentinel / contamination ceiling": "^",
    }

    # background audit zones
    ax.axvspan(0.00, 0.58, alpha=0.10)
    ax.axvspan(0.58, 0.80, alpha=0.06)
    ax.axvspan(0.80, 1.00, alpha=0.10)

    # reference lines
    ax.axvline(0.50, linestyle="--", linewidth=1)
    ax.axvline(0.80, linestyle=":", linewidth=1)

    for i, row in sub.iterrows():
        x = row["auc"]
        lo = row["ci_low"]
        hi = row["ci_high"]
        marker = state_to_marker.get(row["audit_state"], "o")

        ax.hlines(i, lo, hi, linewidth=2)
        ax.plot(x, i, marker=marker, markersize=8, linestyle="None")

        ax.text(
            min(0.995, hi + 0.015),
            i,
            f"{x:.3f}",
            va="center",
            ha="left",
            fontsize=9,
        )

    ax.set_yticks(list(y))
    ax.set_yticklabels(sub["label"], fontsize=10)
    ax.set_xlim(0.0, 1.02)
    ax.set_xlabel("AUC", fontsize=11)
    ax.set_title(title, fontsize=12, pad=10)
    ax.invert_yaxis()

    # zone labels
    ax.text(0.29, -0.9, "Null / weak", ha="center", va="bottom", fontsize=9)
    ax.text(0.69, -0.9, "Valid signal", ha="center", va="bottom", fontsize=9)
    ax.text(0.90, -0.9, "Leakage / ceiling", ha="center", va="bottom", fontsize=9)


def save_source_table(df: pd.DataFrame, outdir: Path):
    outdir.mkdir(parents=True, exist_ok=True)
    df.to_csv(outdir / "lamp_audit_separation_source_data.csv", index=False)


def main():
    outdir = Path("lamp_audit_figure")
    outdir.mkdir(parents=True, exist_ok=True)

    df = build_example_data()
    save_source_table(df, outdir)

    fig, axes = plt.subplots(
        1, 2,
        figsize=(13.8, 6.8),
        sharex=True,
        constrained_layout=True
    )

    iris_df = df[df["dataset"] == "IRIS / Neumayer III"].copy()
    sepsis_df = df[df["dataset"] == "PhysioNet Sepsis"].copy()

    plot_panel(axes[0], iris_df, "IRIS / Neumayer III")
    plot_panel(axes[1], sepsis_df, "PhysioNet/CinC 2019 Sepsis")

    fig.suptitle(
        "Audit Separation Panel: LAMP distinguishes null controls, valid signal and contamination sentinels",
        fontsize=14,
        y=1.02,
    )

    # simple legend assembled manually
    from matplotlib.lines import Line2D
    legend_handles = [
        Line2D([0], [0], marker='o', linestyle='None', markersize=8, label='Null / negative controls'),
        Line2D([0], [0], marker='s', linestyle='None', markersize=8, label='Observed-state / conventional'),
        Line2D([0], [0], marker='D', linestyle='None', markersize=8, label='Latent audited signal'),
        Line2D([0], [0], marker='^', linestyle='None', markersize=8, label='Sentinel / contamination ceiling'),
    ]
    axes[1].legend(
        handles=legend_handles,
        loc="lower right",
        frameon=True,
        fontsize=9,
    )

    png_path = outdir / "Figure_LAMP_Audit_Separation_Panel.png"
    pdf_path = outdir / "Figure_LAMP_Audit_Separation_Panel.pdf"

    fig.savefig(png_path, dpi=300, bbox_inches="tight")
    fig.savefig(pdf_path, bbox_inches="tight")
    plt.close(fig)

    print({
        "figure_png": str(png_path),
        "figure_pdf": str(pdf_path),
        "source_data_csv": str(outdir / "lamp_audit_separation_source_data.csv"),
    })


if __name__ == "__main__":
    main()