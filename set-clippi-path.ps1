[CmdletBinding()]
param(
  # Full path to the selected event folder (e.g. C:\Users\You\project-flippi\Event\Tech-Chase-17)
  [Parameter(Mandatory = $true)]
  [string] $SelectedEvent,

  # Relative path to the data file inside the event (default matches your structure)
  [Parameter(Mandatory = $false)]
  [string] $FileRelativePath = "data\combodata.jsonl"
)

$ErrorActionPreference = 'Stop'

# Constants (match your project layout)
$Root       = Join-Path $env:USERPROFILE 'project-flippi'
$ActiveDir  = Join-Path $Root '_ActiveClippiComboData'
$ActiveFile = Join-Path $ActiveDir 'combodata.jsonl'

try {
  # Validate SelectedEvent
  if (-not (Test-Path -LiteralPath $SelectedEvent -PathType Container)) {
    Write-Error "Selected event folder does not exist: $SelectedEvent"
    exit 1
  }

  # Resolve target file in the event (now using data\combodata.jsonl by default)
  $TargetFile = Join-Path -Path $SelectedEvent -ChildPath $FileRelativePath
  if (-not (Test-Path -LiteralPath $TargetFile -PathType Leaf)) {
    Write-Error "Target file not found in selected event: $TargetFile"
    exit 1
  }

  # Ensure active dir exists
  if (-not (Test-Path -LiteralPath $ActiveDir -PathType Container)) {
    New-Item -ItemType Directory -Path $ActiveDir -Force | Out-Null
  }

  # Remove any existing file/link at ActiveFile (only this path is touched)
  if (Test-Path -LiteralPath $ActiveFile -PathType Any) {
    Remove-Item -LiteralPath $ActiveFile -Force
  }

  # Always create a symbolic link
  New-Item -ItemType SymbolicLink -Path $ActiveFile -Target $TargetFile -Force | Out-Null

  Write-Host "Symlink created:" -ForegroundColor Green
  Write-Host "  Active   => $ActiveFile"
  Write-Host "  Target   => $TargetFile"
  Write-Host "In Project Clippi, set your data path ONCE to:" -ForegroundColor Yellow
  Write-Host "  $ActiveFile"

  exit 0
}
catch {
  Write-Error $_.Exception.Message
  exit 1
}
