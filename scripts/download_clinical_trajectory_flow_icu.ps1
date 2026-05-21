param(
  [string]$OutRoot = "real_data\clinical-trajectory-flow-icu-1.0.0"
)

$ErrorActionPreference = "Stop"
$BaseUrl = "https://physionet.org/files/clinical-trajectory-flow-icu/1.0.0/"
$Files = @(
  "eICU_sepsis_physionet.csv",
  "eICU_cardiacArrest_physionet.csv",
  "MIMIC_gib_physionet.csv",
  "LICENSE.txt",
  "SHA256SUMS.txt"
)

$netrc = Join-Path $HOME ".netrc"
if (-not (Test-Path $netrc)) {
  throw "Missing $netrc. Clinical Trajectory Flow ICU is PhysioNet credentialed access. Create .netrc after completing CITI/DUA: machine physionet.org login YOUR_USERNAME password YOUR_PASSWORD"
}

New-Item -ItemType Directory -Force -Path $OutRoot | Out-Null
foreach ($file in $Files) {
  $dest = Join-Path $OutRoot $file
  if (Test-Path $dest) { continue }
  & curl.exe -L --fail --retry 3 --netrc-file $netrc --continue-at - -o $dest ($BaseUrl + $file)
}

$shaFile = Join-Path $OutRoot "SHA256SUMS.txt"
if (Test-Path $shaFile) {
  Get-Content $shaFile | ForEach-Object {
    if ($_ -match "^\s*([0-9a-fA-F]{64})\s+\*?(.+?)\s*$") {
      $expected = $Matches[1].ToLowerInvariant()
      $name = $Matches[2].Trim()
      $path = Join-Path $OutRoot $name
      if (Test-Path $path) {
        $actual = (Get-FileHash -Algorithm SHA256 -Path $path).Hash.ToLowerInvariant()
        if ($actual -ne $expected) {
          throw "SHA256 mismatch for $name. Expected $expected but got $actual"
        }
      }
    }
  }
}

Write-Output "Downloaded Clinical Trajectory Flow ICU files to $OutRoot"
