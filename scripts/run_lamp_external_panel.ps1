param(
    [string]$PanelRoot = ".\lamp_panel",
    [string]$SepsisDataRoot = ".\real_data\physionet\challenge-2019",
    [string]$WesadRoot = ".\real_data\WESAD",
    [int]$NNull = 1000
)
$ErrorActionPreference = "Stop"
New-Item -ItemType Directory -Force $PanelRoot | Out-Null

Write-Host "=== Sepsis v3 external audit, 5k ==="
py .\external_lamp_sepsis_audit_v3.py `
  --data-root $SepsisDataRoot `
  --out (Join-Path $PanelRoot "sepsis_v3_5k") `
  --max-patients 5000 `
  --n-null $NNull

if (Test-Path $WesadRoot) {
  Write-Host "=== WESAD audit ==="
  py .\lamp_wesad_audit.py `
    --data-root $WesadRoot `
    --out (Join-Path $PanelRoot "wesad") `
    --n-null $NNull
} else {
  Write-Host "Skipping WESAD: $WesadRoot not found"
}

Write-Host "=== Summarizing panel ==="
py .\lamp_panel_summarize.py --root $PanelRoot --out .\lamp_panel_summary
Write-Host "Completed. Open: .\lamp_panel_summary\lamp_external_benchmark_panel_report.md"
