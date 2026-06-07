#!/usr/bin/env bash
set -euo pipefail

printf '== Lynjax host sandbox probe ==\n'
printf 'Date: '
date
printf 'Shell: %s\n' "${SHELL:-unknown}"
printf '\n== Tool availability ==\n'
for cmd in docker wsl.exe VBoxManage vagrant multipass qemu-system-x86_64 gns3server winget.exe; do
  printf '%-24s' "$cmd"
  if command -v "$cmd" >/dev/null 2>&1; then
    command -v "$cmd"
  else
    echo 'not found'
  fi
done

printf '\n== WSL status ==\n'
wsl.exe --status 2>&1 || true
printf '\n== WSL distributions ==\n'
wsl.exe --list --verbose 2>&1 || true

printf '\n== Windows / hardware summary ==\n'
powershell.exe -NoProfile -ExecutionPolicy Bypass -Command '
$os = Get-CimInstance Win32_OperatingSystem | Select-Object Caption,Version,BuildNumber,OSArchitecture
$cs = Get-CimInstance Win32_ComputerSystem | Select-Object Manufacturer,Model,TotalPhysicalMemory,HypervisorPresent
$cpu = Get-CimInstance Win32_Processor | Select-Object Name,NumberOfCores,NumberOfLogicalProcessors,VirtualizationFirmwareEnabled,VMMonitorModeExtensions,SecondLevelAddressTranslationExtensions
$principal = [Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()
$admin = [pscustomobject]@{IsAdmin=$principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator); User=[Security.Principal.WindowsIdentity]::GetCurrent().Name}
$disk = Get-PSDrive -PSProvider FileSystem | Select-Object Name,Free,Used
[pscustomobject]@{OS=$os; Computer=$cs; CPU=$cpu; User=$admin; Disk=$disk} | ConvertTo-Json -Depth 4
' 2>&1 || true

printf '\n== Notes ==\n'
printf 'This script is read-only. It does not install or enable Windows features.\n'
printf 'Windows optional feature inspection may require an elevated PowerShell session.\n'
