param(
  [string]$OutRoot = "real_data\bidsleep-dataset-1.0.0",
  [string]$SubjectPattern = "",
  [string[]]$FileNames = @(),
  [int]$MaxFiles = 0
)

$ErrorActionPreference = "Stop"
$BaseUrl = "https://physionet.org/files/bidsleep-dataset/1.0.0/"
$shaPath = Join-Path $OutRoot "SHA256SUMS.txt"
New-Item -ItemType Directory -Force -Path $OutRoot | Out-Null

if (-not (Test-Path $shaPath)) {
  & curl.exe -L --fail --retry 3 -o $shaPath ($BaseUrl + "SHA256SUMS.txt")
}

$records = Get-Content $shaPath | ForEach-Object {
  $parts = $_ -split "\s+", 2
  if ($parts.Count -eq 2) { $parts[1] }
} | Where-Object { $_ }

if ($SubjectPattern) {
  $records = $records | Where-Object { $_ -like "$SubjectPattern/*" }
}
if ($FileNames.Count -gt 0) {
  $records = $records | Where-Object {
    $leaf = Split-Path $_ -Leaf
    $FileNames -contains $leaf
  }
}
if ($MaxFiles -gt 0) {
  $records = $records | Select-Object -First $MaxFiles
}

foreach ($rel in $records) {
  $dest = Join-Path $OutRoot $rel
  if (Test-Path $dest) {
    continue
  }
  New-Item -ItemType Directory -Force -Path (Split-Path $dest -Parent) | Out-Null
  & curl.exe -L --fail --retry 3 --continue-at - -o $dest ($BaseUrl + $rel)
}

Write-Output "Downloaded $($records.Count) files to $OutRoot"
