param(
  [string]$OutRoot = "real_data",
  [switch]$Mimic,
  [switch]$Eicu,
  [switch]$EicuDemo
)

$ErrorActionPreference = "Stop"

function Require-Curl {
  $curl = Get-Command curl.exe -ErrorAction SilentlyContinue
  if (-not $curl) {
    throw "curl.exe not found. Install curl or run from a Windows build that includes it."
  }
}

function Download-File {
  param(
    [string]$Url,
    [string]$OutFile,
    [switch]$Credentialed
  )
  New-Item -ItemType Directory -Force -Path (Split-Path $OutFile -Parent) | Out-Null
  $args = @("-L", "--fail", "--retry", "3", "--continue-at", "-", "--output", $OutFile)
  if ($Credentialed) {
    $netrc = Join-Path $HOME ".netrc"
    if (-not (Test-Path $netrc)) {
      throw "Missing $netrc. Create it with: machine physionet.org login YOUR_USERNAME password YOUR_PASSWORD"
    }
    $args += @("--netrc-file", $netrc)
  }
  $args += $Url
  & curl.exe @args
}

function Download-PhysioNetTree {
  param(
    [string]$BaseUrl,
    [string]$Dest,
    [switch]$Credentialed
  )
  $records = Join-Path $Dest "RECORDS"
  Download-File -Url ($BaseUrl + "RECORDS") -OutFile $records -Credentialed:$Credentialed
  $files = Get-Content $records | Where-Object { $_ -and -not $_.StartsWith("#") }
  foreach ($file in $files) {
    Download-File -Url ($BaseUrl + $file) -OutFile (Join-Path $Dest $file) -Credentialed:$Credentialed
  }
  Download-File -Url ($BaseUrl + "SHA256SUMS.txt") -OutFile (Join-Path $Dest "SHA256SUMS.txt") -Credentialed:$Credentialed
}

Require-Curl
if (-not $Mimic -and -not $Eicu -and -not $EicuDemo) {
  $Mimic = $true
  $Eicu = $true
}

if ($Mimic) {
  Download-PhysioNetTree `
    -BaseUrl "https://physionet.org/files/mimiciv/3.1/" `
    -Dest (Join-Path $OutRoot "mimiciv-3.1") `
    -Credentialed
}

if ($Eicu) {
  Download-PhysioNetTree `
    -BaseUrl "https://physionet.org/files/eicu-crd/2.0/" `
    -Dest (Join-Path $OutRoot "eicu-crd-2.0") `
    -Credentialed
}

if ($EicuDemo) {
  Download-PhysioNetTree `
    -BaseUrl "https://physionet.org/files/eicu-crd-demo/2.0.1/" `
    -Dest (Join-Path $OutRoot "eicu-crd-demo") `
}
