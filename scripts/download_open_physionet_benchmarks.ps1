param(
    [string]$Destination = "real_data",
    [int]$CinCMaxFiles = 0,
    [switch]$SkipCinC,
    [switch]$SkipVitalDB,
    [switch]$IncludeBigIdeas,
    [switch]$ExtractBigIdeas
)

$ErrorActionPreference = "Stop"

$Root = Resolve-Path (Join-Path $PSScriptRoot "..")
$DestinationPath = Join-Path $Root $Destination
New-Item -ItemType Directory -Force -Path $DestinationPath | Out-Null

function Format-Bytes([long]$Bytes) {
    if ($Bytes -ge 1GB) { return "{0:N2} GB" -f ($Bytes / 1GB) }
    if ($Bytes -ge 1MB) { return "{0:N2} MB" -f ($Bytes / 1MB) }
    if ($Bytes -ge 1KB) { return "{0:N2} KB" -f ($Bytes / 1KB) }
    return "$Bytes B"
}

function Download-File([string]$Url, [string]$OutFile) {
    $OutDir = Split-Path -Parent $OutFile
    New-Item -ItemType Directory -Force -Path $OutDir | Out-Null

    if ((Test-Path $OutFile) -and ((Get-Item $OutFile).Length -gt 0)) {
        Write-Host "Using existing $OutFile ($(Format-Bytes (Get-Item $OutFile).Length))"
        return
    }

    Write-Host "Downloading $Url"
    & curl.exe -L --fail --retry 8 --retry-all-errors --retry-delay 10 --connect-timeout 60 --continue-at - --output $OutFile $Url
    if ($LASTEXITCODE -ne 0) {
        throw "curl failed for $Url"
    }
}

function Download-PhysioNetS3Prefix([string]$Prefix, [string]$OutDir, [int]$MaxFiles = 0) {
    $Args = @(
        (Join-Path $Root "src\external_benchmarks\download_physionet_open_s3.py"),
        "--prefix", $Prefix,
        "--out", $OutDir
    )
    if ($MaxFiles -gt 0) {
        $Args += @("--max-files", "$MaxFiles")
    }
    Write-Host "Downloading PhysioNet open S3 prefix $Prefix -> $OutDir"
    & python @Args
    if ($LASTEXITCODE -ne 0) {
        throw "S3 download failed for $Prefix"
    }
}

function Download-BigIdeasZip([string]$OutFile) {
    $ExpectedBytes = 5015250233
    $ControlFile = "$OutFile.aria2"
    $Complete = (Test-Path $OutFile) -and ((Get-Item $OutFile).Length -eq $ExpectedBytes) -and (-not (Test-Path $ControlFile))
    if ($Complete) {
        Write-Host "Using complete BIG IDEAs ZIP $OutFile ($(Format-Bytes (Get-Item $OutFile).Length))"
        return
    }

    $Aria2 = Get-Command aria2c -ErrorAction SilentlyContinue
    if (-not $Aria2) {
        Download-File -Url "https://physionet.org/content/big-ideas-glycemic-wearable/get-zip/1.1.3/" -OutFile $OutFile
        return
    }

    $OutDir = Split-Path -Parent $OutFile
    $OutName = Split-Path -Leaf $OutFile
    New-Item -ItemType Directory -Force -Path $OutDir | Out-Null
    Write-Host "Downloading/resuming BIG IDEAs ZIP with aria2c -> $OutFile"
    & $Aria2.Source `
        -x 8 `
        -s 8 `
        --continue=true `
        --max-tries=12 `
        --retry-wait=10 `
        --summary-interval=60 `
        --download-result=hide `
        --console-log-level=warn `
        -d $OutDir `
        -o $OutName `
        "https://physionet.org/content/big-ideas-glycemic-wearable/get-zip/1.1.3/"
    if ($LASTEXITCODE -ne 0) {
        throw "BIG IDEAs aria2 download failed or was interrupted"
    }
}

function Expand-Zip([string]$ZipFile, [string]$OutDir) {
    if (Test-Path $OutDir) {
        $existing = Get-ChildItem -Path $OutDir -Recurse -File -ErrorAction SilentlyContinue | Select-Object -First 1
        if ($existing) {
            Write-Host "Using existing extracted directory $OutDir"
            return
        }
    }
    New-Item -ItemType Directory -Force -Path $OutDir | Out-Null
    Write-Host "Extracting $ZipFile -> $OutDir"
    Expand-Archive -Path $ZipFile -DestinationPath $OutDir -Force
}

if (-not $SkipCinC) {
    $CinCTrain = Join-Path $DestinationPath "physionet\challenge-2019\training"
    Download-PhysioNetS3Prefix `
        -Prefix "challenge-2019/1.0.0/training/training_setA/" `
        -OutDir (Join-Path $CinCTrain "training_setA") `
        -MaxFiles $CinCMaxFiles
    Download-PhysioNetS3Prefix `
        -Prefix "challenge-2019/1.0.0/training/training_setB/" `
        -OutDir (Join-Path $CinCTrain "training_setB") `
        -MaxFiles $CinCMaxFiles
}

if (-not $SkipVitalDB) {
    $VitalDir = Join-Path $DestinationPath "vitaldb-arrhythmia-1.0.0"
    Download-PhysioNetS3Prefix `
        -Prefix "vitaldb-arrhythmia/1.0.0/" `
        -OutDir $VitalDir
}

if ($IncludeBigIdeas) {
    $BigZip = Join-Path $DestinationPath "big-ideas-glycemic-wearable-1.1.3.zip"
    Download-BigIdeasZip -OutFile $BigZip
    if ($ExtractBigIdeas) {
        $BigDir = Join-Path $DestinationPath "big-ideas-glycemic-wearable-1.1.3"
        Expand-Zip -ZipFile $BigZip -OutDir $BigDir
    } else {
        Write-Host "BIG IDEAs ZIP downloaded but not extracted. Use -ExtractBigIdeas if you want the 34 GB expanded tree."
    }
}

$Manifest = [ordered]@{
    generated_at = (Get-Date).ToString("s")
    destination = $DestinationPath
    datasets = @(
        [ordered]@{
            name = "PhysioNet/CinC 2019 sepsis"
            url = "https://physionet.org/content/challenge-2019/1.0.0/"
            local_path = (Join-Path $DestinationPath "physionet\challenge-2019")
            note = "Raw training_setA/training_setB .psv files; downloaded from the public PhysioNet S3 mirror."
        },
        [ordered]@{
            name = "VitalDB Arrhythmia"
            url = "https://physionet.org/content/vitaldb-arrhythmia/1.0.0/"
            local_path = (Join-Path $DestinationPath "vitaldb-arrhythmia-1.0.0")
            note = "Open-access arrhythmia annotations and metadata; waveform loading uses VitalDB case IDs."
        },
        [ordered]@{
            name = "BIG IDEAs Lab glycemic wearable"
            url = "https://physionet.org/content/big-ideas-glycemic-wearable/1.1.3/"
            zip_path = (Join-Path $DestinationPath "big-ideas-glycemic-wearable-1.1.3.zip")
            note = "Large open-access wearable/CGM dataset. ZIP is about 4.7 GB; extraction is about 34 GB."
        }
    )
}

$ManifestPath = Join-Path $DestinationPath "downloaded_open_benchmarks_manifest.json"
$Manifest | ConvertTo-Json -Depth 5 | Set-Content -Path $ManifestPath -Encoding UTF8
Write-Host "Wrote manifest $ManifestPath"
