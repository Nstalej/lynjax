#!/usr/bin/env bash
set -euo pipefail

have() {
  if command -v "$1" >/dev/null 2>&1; then
    printf 'OK     %s -> %s\n' "$1" "$(command -v "$1")"
  else
    printf 'MISSING %s\n' "$1"
  fi
}

section() {
  printf '\n== %s ==\n' "$1"
}

section "Lynjax host probe read-only"
date '+%Y-%m-%d %H:%M:%S %Z' 2>/dev/null || true
printf 'Shell: %s\n' "${SHELL:-unknown}"
printf 'PWD: %s\n' "$(pwd)"

section "Command availability"
for cmd in python python3 node npm docker curl git wsl.exe VBoxManage vagrant multipass qemu-system-x86_64 gns3server winget.exe; do
  have "$cmd"
done

section "Versions"
python --version 2>/dev/null || true
python3 --version 2>/dev/null || true
node --version 2>/dev/null || true
npm --version 2>/dev/null || true
docker --version 2>/dev/null || true
docker compose version 2>/dev/null || true
git --version 2>/dev/null || true

section "WSL status"
if command -v wsl.exe >/dev/null 2>&1; then
  wsl.exe --status 2>/dev/null || true
  wsl.exe --list --verbose 2>/dev/null || true
else
  echo "wsl.exe not found from this shell."
fi

section "System summary"
uname -a 2>/dev/null || true

if command -v powershell.exe >/dev/null 2>&1; then
  powershell.exe -NoProfile -ExecutionPolicy Bypass -Command '
    $os = Get-CimInstance Win32_OperatingSystem;
    $cs = Get-CimInstance Win32_ComputerSystem;
    $cpu = Get-CimInstance Win32_Processor | Select-Object -First 1;
    Write-Host "Windows:" $os.Caption $os.Version;
    Write-Host "Computer:" $cs.Manufacturer $cs.Model;
    Write-Host "RAM_GB:" ([math]::Round($cs.TotalPhysicalMemory / 1GB, 2));
    Write-Host "CPU:" $cpu.Name;
    Write-Host "VirtualizationFirmwareEnabled:" $cpu.VirtualizationFirmwareEnabled;
    Write-Host "Admin:" ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator);
    Get-CimInstance Win32_LogicalDisk -Filter "DriveType=3" | ForEach-Object { Write-Host ("Disk " + $_.DeviceID + " free_GB=" + [math]::Round($_.FreeSpace / 1GB, 2)) }
  ' 2>/dev/null || true
else
  echo "powershell.exe not available; Windows CIM summary skipped."
fi

section "Notes"
echo "This probe is read-only. It does not install packages, enable Windows features, modify Docker, or change virtualization settings."
echo "Use WSL2/Ubuntu VM/CI for Docker Compose lab execution when possible."
