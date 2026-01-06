@echo off
setlocal enabledelayedexpansion

echo ============================================
echo   Certificate Installer - Root Trust Store
echo ============================================
echo.
echo  WARNING: This script installs certificates
echo  into your Trusted Root Certification
echo  Authorities store.
echo.
echo  This is intended for custom self-signed
echo  certificates from TRUSTED sources only.
echo.
echo  *** INSTALLING UNKNOWN CERTIFICATES IS ***
echo  ***       EXTREMELY DANGEROUS!         ***
echo.
echo  A malicious root certificate can allow
echo  attackers to intercept ALL your encrypted
echo  traffic, including passwords, banking,
echo  and personal data.
echo.
echo  Only proceed if you know and trust the
echo  source of these certificates!
echo ============================================
echo.
set /p "proceed=Do you want to continue? (Y/N): "
if /i not "%proceed%"=="Y" (
    echo Aborted.
    pause
    exit /b
)
echo.

set "found=0"

for %%F in (*.cer *.crt *.pem *.der) do (
    set "found=1"
    echo --------------------------------------------
    echo File: %%F
    echo --------------------------------------------

    REM Get certificate details using PowerShell
    powershell -Command ^
        "$cert = New-Object System.Security.Cryptography.X509Certificates.X509Certificate2('%%F'); " ^
        "Write-Host 'Subject (CN):' $cert.Subject; " ^
        "Write-Host 'Issuer:' $cert.Issuer; " ^
        "Write-Host 'Valid From:' $cert.NotBefore; " ^
        "Write-Host 'Valid To:' $cert.NotAfter; " ^
        "Write-Host 'Thumbprint:' $cert.Thumbprint; " ^
        "$san = $cert.Extensions | Where-Object { $_.Oid.FriendlyName -eq 'Subject Alternative Name' }; " ^
        "if ($san) { Write-Host 'SANs:' $san.Format(1) } else { Write-Host 'SANs: (none)' }"

    echo.
    set /p "confirm=Install this certificate to Trusted Root store? (Y/N): "

    if /i "!confirm!"=="Y" (
        echo Installing %%F...
        powershell -Command "Import-Certificate -FilePath '%%F' -CertStoreLocation Cert:\CurrentUser\Root" >nul 2>&1
        if !errorlevel! equ 0 (
            echo [SUCCESS] Certificate installed.
        ) else (
            echo [ERROR] Failed to install certificate. Try running as Administrator.
        )
    ) else (
        echo Skipped %%F
    )
    echo.
)

if "!found!"=="0" (
    echo No certificate files found in current directory.
    echo Supported extensions: .cer, .crt, .pem, .der
)

echo.
echo Done.
pause
