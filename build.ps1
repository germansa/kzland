<#
.SYNOPSIS
    Compila el servidor cargando el entorno de MSVC y vcpkg automaticamente.

.DESCRIPTION
    Envuelve los presets de CMakePresets.json para no tener que abrir una
    Developer PowerShell ni exportar VCPKG_ROOT a mano.

    La primera ejecucion (o cualquiera con -Configure) corre el configure de
    CMake, que resuelve las dependencias de vcpkg y tarda bastante.

.PARAMETER Config
    Release (por defecto) o Debug.

.PARAMETER Configure
    Fuerza el configure de CMake antes de compilar. Necesario tras cambiar
    CMakeLists.txt, vcpkg.json o los presets.

.PARAMETER Run
    Arranca el servidor al terminar la compilacion.

.PARAMETER Clean
    Borra el directorio build/ y reconfigura desde cero.

.EXAMPLE
    .\build.ps1
    Compila en Release.

.EXAMPLE
    .\build.ps1 -Config Debug -Run
    Compila en Debug y arranca el servidor.
#>
[CmdletBinding()]
param(
    [ValidateSet('Release', 'Debug')]
    [string]$Config = 'Release',

    [switch]$Configure,
    [switch]$Run,
    [switch]$Clean
)

$ErrorActionPreference = 'Stop'
$root = $PSScriptRoot
$buildDir = Join-Path $root 'build'

function Write-Step($message) {
    Write-Host ">> $message" -ForegroundColor Cyan
}

# --- Requisitos ---
$vswhere = Join-Path ${env:ProgramFiles(x86)} 'Microsoft Visual Studio\Installer\vswhere.exe'
if (-not (Test-Path $vswhere)) {
    throw "No se encontro vswhere.exe. Instala Visual Studio Build Tools 2022 con el workload de C++."
}

$vsPath = & $vswhere -products * -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -latest -format value -property installationPath
if (-not $vsPath) {
    throw "No hay una instalacion de Visual Studio con las herramientas de C++ (VC.Tools.x86.x64)."
}

if (-not $env:VCPKG_ROOT) {
    $env:VCPKG_ROOT = [Environment]::GetEnvironmentVariable('VCPKG_ROOT', 'User')
}
if (-not $env:VCPKG_ROOT -or -not (Test-Path $env:VCPKG_ROOT)) {
    throw "VCPKG_ROOT no esta definido o apunta a una ruta inexistente. Se espera el clon de vcpkg (ej. C:\vcpkg)."
}

# --- Entorno MSVC ---
# Enter-VsDevShell deja el compilador, el linker y el SDK en el PATH de esta sesion.
# Su script interno llama a vswhere sin ruta absoluta, asi que primero lo dejamos alcanzable.
$vswhereDir = Split-Path $vswhere -Parent
if ($env:Path -notlike "*$vswhereDir*") { $env:Path = "$env:Path;$vswhereDir" }

Write-Step "Cargando entorno MSVC ($vsPath)"
Import-Module (Join-Path $vsPath 'Common7\Tools\Microsoft.VisualStudio.DevShell.dll')
Enter-VsDevShell -VsInstallPath $vsPath -SkipAutomaticLocation -DevCmdArguments '-arch=x64 -host_arch=x64' | Out-Null

Set-Location $root

# --- Configure ---
if ($Clean -and (Test-Path $buildDir)) {
    Write-Step "Borrando $buildDir"
    Remove-Item $buildDir -Recurse -Force
}

if ($Configure -or $Clean -or -not (Test-Path (Join-Path $buildDir 'CMakeCache.txt'))) {
    Write-Step "Configurando (resuelve dependencias de vcpkg, puede tardar)"
    cmake --preset vcpkg
    if ($LASTEXITCODE -ne 0) { throw "El configure de CMake fallo con codigo $LASTEXITCODE." }
}

# --- Build ---
Write-Step "Compilando ($Config)"
cmake --build --preset vcpkg --config $Config
if ($LASTEXITCODE -ne 0) { throw "La compilacion fallo con codigo $LASTEXITCODE." }

$exe = Join-Path $buildDir "$Config\tfs.exe"
if (-not (Test-Path $exe)) { throw "La compilacion termino pero no se encontro $exe." }

Write-Host ""
Write-Host "OK: $exe" -ForegroundColor Green

# --- Run ---
# El servidor busca data/ y config.lua relativos al directorio actual,
# por eso se ejecuta desde la raiz del proyecto y no desde build/.
if ($Run) {
    Write-Step "Arrancando el servidor (Ctrl+C para detenerlo)"
    & $exe
}
