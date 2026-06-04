# iPSC-CM Maturation Biological Contract

LAMP-Bio uses a biological contract so an iPSC-CM maturation audit is not just a
generic suspiciousness calculator. The contract asks what kind of maturation
claim is being made, which biological axis defines the endpoint, which disjoint
axis is allowed as evidence, and which experimental-structure fields must be
treated as sentinels.

The executable contract is in
`configs/ipsc_cm_maturation_contract.yaml`.

## Biological Axes

| Axis | Interpretation | Example Markers / Features | Contract Role |
|---|---|---|---|
| Structural maturation | Sarcomeric organization, contractile apparatus, adult-like myofibrillar architecture | `TNNI3`, `MYL2`, `MYH7/MYH6`, `ACTN2`, `TNNT2`, `MYBPC3` | Endpoint or evidence, but the exact same panel cannot be both endpoint and score. |
| Calcium-handling / electrophysiology | Calcium cycling, ion-channel maturation, AP/conduction readiness, calcium/MEA/patch proxies | `RYR2`, `ATP2A2`, `PLN`, `CASQ2`, `CACNA1C`, `KCNH2`, `KCNQ1`, `SCN5A` | Strong disjoint probe axis when endpoint is structural or metabolic. |
| Metabolic maturation | Shift toward oxidative phosphorylation, mitochondrial biogenesis, fatty-acid metabolism | `PPARGC1A`, `CPT1B`, `ACADVL`, `NDUF*`, `COX*`, `TFAM` | Disjoint or supportive probe; metabolic media are protocol sentinels unless explicitly modeled. |
| Cell-cycle exit | Reduced proliferative state | `MKI67`, `TOP2A`, `PCNA`, `CCNB1/2`, `CDK1` | Supportive only; not sufficient because it can reflect stress, density, sorting, or viability. |
| Intervention/protocol structure | Experimental structure, not maturation evidence | day, timepoint, calcium condition, pacing condition, 2D/3D, plate, batch, donor/line, dose, medium, replicate, sequencing lane | Forbidden axis and sentinel source. |

## Claim Contract

Every iPSC-CM claim should declare:

- Claim form: for example, `Early X predicts later Y` or `Condition A induces maturation state Y`.
- Endpoint axis: structural, electrophysiology/calcium, metabolic, cell-cycle, or composite.
- Allowed evidence axis: disjoint from the endpoint axis.
- Forbidden axis: day, protocol, intervention code, endpoint markers, batch, donor, plate, dose/drug identity when not the claim target.
- Required sentinels: protocol, timepoint, endpoint-marker/oracle, donor/batch, score-direction sanity.

## Biological Diagnosis Levels

| Diagnosis | Meaning |
|---|---|
| `valid_biological_signal_stable` | PASS plus stable bootstrap, leave-group-out, alternative-panel checks, and no protocol-sentinel dominance. |
| `valid_biological_signal_fragile` | PASS exists, but bootstrap, leave-group-out, threshold, panel, donor, or protocol-heldout evidence is weak or missing. |
| `protocol_confounded_signal` | The signal is not cleanly separable from protocol, intervention, batch, donor, dose, or drug structure. |
| `endpoint_adjacent_contamination` | The score reuses endpoint markers, labels, post-endpoint features, or violates temporal/forbidden endpoint isolation. |
| `not_biologically_interpretable` | Numerical performance exists, but no declared disjoint biological axis supports the interpretation. |

## Current GSE201437 Diagnosis

Using the controlled GSE201437 sanity setup:

| Model | Biological Diagnosis | Interpretation |
|---|---|---|
| Clean calcium/electrophysiology probe | `valid_biological_signal_fragile` | A disjoint calcium/electrophysiology probe supports a plausible structural maturation signal, but bootstrap PASS rate is about 0.503 and donor-held-out stability is not evaluable. |
| High-calcium shortcut | `protocol_confounded_signal` | High AUC comes from intervention metadata, not allowed biological evidence. |
| Explicit oracle leakage | `endpoint_adjacent_contamination` | The score directly uses the endpoint label and fails temporal/forbidden isolation. |

Run:

```bash
python scripts/run_ipsc_cm_bio_contract_diagnosis.py
```
