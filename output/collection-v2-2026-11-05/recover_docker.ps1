$ErrorActionPreference = 'Stop'
$dockerProcesses = Get-Process -Name 'Docker Desktop','com.docker.backend','com.docker.build' -ErrorAction SilentlyContinue
foreach ($dockerProcess in $dockerProcesses) {
    if ($dockerProcess.Path -like 'C:\Program Files\Docker\Docker\*') {
        Stop-Process -Id $dockerProcess.Id -Force -ErrorAction SilentlyContinue
    }
}
Start-Process -FilePath 'C:\Program Files\Docker\Docker\Docker Desktop.exe' -WindowStyle Hidden
Write-Output 'Docker Desktop restarted; persisted volumes retained.'
