$ErrorActionPreference = "Stop"
Write-Host "Checking Macleen's 2-Year Cash Flow update..." -ForegroundColor Cyan

$checks = @(
    @{ Name = "Cash-flow route"; Path = ".\app.py"; Pattern = "@app.route\('/admin/cash-flow'\)" },
    @{ Name = "Cash-flow alias"; Path = ".\app.py"; Pattern = "@app.route\('/admin/cashflow'\)" },
    @{ Name = "Cash-flow model"; Path = ".\app.py"; Pattern = "class CashFlowPlan" },
    @{ Name = "60% COGS rule"; Path = ".\app.py"; Pattern = "CASH_FLOW_COGS_RATE = 0.60" },
    @{ Name = "Admin Cash Flow button"; Path = ".\templates\admin.html"; Pattern = "2-Year Cash Flow" },
    @{ Name = "Bi-weekly frequency backend"; Path = ".\app.py"; Pattern = "BIWEEKLY" },
    @{ Name = "Bi-weekly frequency UI"; Path = ".\templates\cash_flow_portal.html"; Pattern = "Bi-weekly \(Every 2 Weeks\)" }
)

$failed = $false
foreach ($check in $checks) {
    if (-not (Test-Path $check.Path)) {
        Write-Host "FAIL: $($check.Path) is missing" -ForegroundColor Red
        $failed = $true
        continue
    }
    if (Select-String -Path $check.Path -Pattern $check.Pattern -Quiet) {
        Write-Host "OK: $($check.Name)" -ForegroundColor Green
    } else {
        Write-Host "FAIL: $($check.Name)" -ForegroundColor Red
        $failed = $true
    }
}

if (-not (Test-Path ".\templates\cash_flow_portal.html")) {
    Write-Host "FAIL: templates\cash_flow_portal.html is missing" -ForegroundColor Red
    $failed = $true
} else {
    Write-Host "OK: Cash-flow portal template" -ForegroundColor Green
}

if ($failed) {
    Write-Host "`nThis folder does NOT contain the complete cash-flow update." -ForegroundColor Red
    exit 1
}

Write-Host "`nREADY: this project folder contains the complete cash-flow update." -ForegroundColor Green
Write-Host "After pushing this exact folder, /admin/cash-flow and /admin/cashflow should both exist." -ForegroundColor Green
