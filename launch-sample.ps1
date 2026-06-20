$ErrorActionPreference = "Stop"

$systemUuid = (Get-CimInstance -ClassName Win32_ComputerSystemProduct).UUID
$biosSerial = (Get-CimInstance -ClassName Win32_BIOS).SerialNumber

if ([string]::IsNullOrWhiteSpace($systemUuid) -or
    [string]::IsNullOrWhiteSpace($biosSerial)) {
    throw "Windows could not read the system UUID or BIOS serial number."
}

$hardwareId = ("{0}{1}" -f $systemUuid.Trim(), $biosSerial.Trim()) -replace "[^A-Za-z0-9]", ""
$encodedHardwareId = [System.Uri]::EscapeDataString($hardwareId.ToUpperInvariant())
$samplePath = Join-Path $PSScriptRoot "sample.html"
$sampleUri = [System.Uri]::new((Resolve-Path $samplePath).Path).AbsoluteUri
$url = "$sampleUri`?hardware_id=$encodedHardwareId"

Start-Process $url
