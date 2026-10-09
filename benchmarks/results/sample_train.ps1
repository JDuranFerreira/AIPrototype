param([string]$Workdir = 'c:\AIAccess\Projects\AIPrototype')
$outLog = Join-Path $Workdir 'benchmarks\results\reasoner_lowram_e6.log'
$errLog = Join-Path $Workdir 'benchmarks\results\reasoner_lowram_e6.err'
$stats  = Join-Path $Workdir 'benchmarks\results\reasoner_lowram_e6.stats'
$p = Start-Process python -ArgumentList 'benchmarks\train_reasoner.py','--no-save' -WorkingDirectory $Workdir -RedirectStandardOutput $outLog -RedirectStandardError $errLog -NoNewWindow -PassThru
$maxWS = 0; $t0 = $null; $c0 = $null; $now = $null; $cpu = $null
while ($true) {
  $proc = Get-Process -Id $p.Id -ErrorAction SilentlyContinue
  if (-not $proc) { break }
  if ($proc.WorkingSet64 -gt $maxWS) { $maxWS = $proc.WorkingSet64 }
  $cpu = $proc.CPU
  if ($null -eq $t0) { $t0 = Get-Date; $c0 = $cpu }
  $now = Get-Date
  Start-Sleep -Milliseconds 800
}
$wall = ($now - $t0).TotalSeconds
$avgCores = ($cpu - $c0) / [math]::Max($wall, 1)
$cores = (Get-CimInstance Win32_ComputerSystem).NumberOfLogicalProcessors
"peak_workingset_MB = $([math]::Round($maxWS/1MB,0))" | Set-Content $stats
"avg_cpu_cores = $([math]::Round($avgCores,2)) of $cores ($([math]::Round(100*$avgCores/$cores,1))% of all cores)" | Add-Content $stats
"wall_seconds = $([math]::Round($wall,0))" | Add-Content $stats
"sampler done"
