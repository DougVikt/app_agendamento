param([switch]$cd)
$root = Split-Path $PSCommandPath
Set-Location $root

if ($cd) {
    # CD: restart server
    Get-Process -Name python -ErrorAction SilentlyContinue | Stop-Process -Force
    Start-Sleep 2
    Remove-Item ".agenda.test.*" -Force -ErrorAction SilentlyContinue
    Write-Host "Server stopped. Run 'python app.py' to restart." -ForegroundColor Cyan
    exit
}

Write-Host "=== CI: Sistema de Agendamento ===" -ForegroundColor Cyan

# Step 1: Syntax check
Write-Host "`n[1/4] Syntax check..." -ForegroundColor Yellow
python -c "import py_compile; py_compile.compile('app.py', doraise=True)" 2>&1
if ($LASTEXITCODE -ne 0) { Write-Host "FAIL: Syntax error" -ForegroundColor Red; exit 1 }
Write-Host "  OK" -ForegroundColor Green

# Step 2: Start server with test DB
Write-Host "[2/4] Starting server..." -ForegroundColor Yellow
Remove-Item ".agenda.ci.*" -Force -ErrorAction SilentlyContinue
$env:AGENDA_DB = Join-Path $root ".agenda.ci.db"
$job = Start-Job { param($d,$db) $env:AGENDA_DB = $db; Set-Location $d; python app.py } -ArgumentList $root, $env:AGENDA_DB
Start-Sleep -Seconds 5

# Step 3: Run tests
Write-Host "[3/4] Running API tests..." -ForegroundColor Yellow
$failed = 0
$tests = @()

# 3a: Create colaborador
try {
    $r = Invoke-WebRequest "http://127.0.0.1:5000/api/colaborador" -Method POST -ContentType "application/json" -Body '{"nome":"Teste CI"}' -UseBasicParsing
    if ($r.StatusCode -eq 201) { $tests += "Criar colaborador: OK" } else { $tests += "Criar colaborador: FAIL ($($r.StatusCode))"; $failed++ }
} catch { $tests += "Criar colaborador: FAIL ($_)"; $failed++ }

# 3b: Create fixed horario
$data = (Get-Date).AddDays(7).ToString("yyyy-MM-dd")
try {
    $body = '{"colaborador_id":1,"data":"' + $data + '","hora_inicio":"08:00","hora_fim":"12:00","intervalo":30}'
    $r = Invoke-WebRequest "http://127.0.0.1:5000/api/horarios" -Method POST -ContentType "application/json" -Body $body -UseBasicParsing
    if ($r.StatusCode -eq 201) { $tests += "Criar horario fixo: OK" } else { $tests += "Criar horario fixo: FAIL ($($r.StatusCode))"; $failed++ }
} catch { $tests += "Criar horario fixo: FAIL ($_)"; $failed++ }

# 3c: Create recurring horario
try {
    $body = '{"colaborador_id":1,"data":"","hora_inicio":"14:00","hora_fim":"17:00","intervalo":60,"recorrente":1,"dia_semana":2}'
    $r = Invoke-WebRequest "http://127.0.0.1:5000/api/horarios" -Method POST -ContentType "application/json" -Body $body -UseBasicParsing
    if ($r.StatusCode -eq 201) { $tests += "Criar horario recorrente: OK" } else { $tests += "Criar horario recorrente: FAIL ($($r.StatusCode))"; $failed++ }
} catch { $tests += "Criar horario recorrente: FAIL ($_)"; $failed++ }

# 3d: List datas
try {
    $r = Invoke-WebRequest "http://127.0.0.1:5000/api/datas/1" -UseBasicParsing
    $j = $r.Content | ConvertFrom-Json
    if ($j.Count -gt 0) { $tests += "Listar datas ($($j.Count)): OK" } else { $tests += "Listar datas: FAIL (0 dates)"; $failed++ }
} catch { $tests += "Listar datas: FAIL ($_)"; $failed++ }

# 3e: Create agendamento with telefone + observacoes
$telObsBody = '{"colaborador_id":1,"data":"' + $data + '","hora_inicio":"08:00","tipo":"Reforco","cliente":"Teste","cpf":"123","telefone":"1199999","observacoes":"Obs de teste"}'
try {
    $r = Invoke-WebRequest "http://127.0.0.1:5000/api/agendamentos" -Method POST -ContentType "application/json" -Body $telObsBody -UseBasicParsing
    if ($r.StatusCode -eq 201) { $tests += "Agendar c/ telefone+obs: OK" } else { $tests += "Agendar c/ telefone+obs: FAIL ($($r.StatusCode))"; $failed++ }
} catch { $tests += "Agendar c/ telefone+obs: FAIL ($_)"; $failed++ }

# 3f: Cancel agendamento
try {
    $r = Invoke-WebRequest "http://127.0.0.1:5000/api/agendamentos/1/status" -Method PATCH -ContentType "application/json" -Body '{"status":"Cancelado"}' -UseBasicParsing
    if ($r.StatusCode -eq 200) { $tests += "Cancelar agendamento: OK" } else { $tests += "Cancelar agendamento: FAIL ($($r.StatusCode))"; $failed++ }
} catch { $tests += "Cancelar agendamento: FAIL ($_)"; $failed++ }

# 3g: Rename colaborador
try {
    $r = Invoke-WebRequest "http://127.0.0.1:5000/api/colaborador/1" -Method PATCH -ContentType "application/json" -Body '{"nome":"Teste CI Editado"}' -UseBasicParsing
    if ($r.StatusCode -eq 200) { $tests += "Renomear colaborador: OK" } else { $tests += "Renomear colaborador: FAIL ($($r.StatusCode))"; $failed++ }
} catch { $tests += "Renomear colaborador: FAIL ($_)"; $failed++ }

# 3h: Login endpoints
try {
    $r = Invoke-WebRequest "http://127.0.0.1:5000/inicio_atendimento" -Method POST -UseBasicParsing -MaximumRedirection 0
    if ($r.StatusCode -eq 302) { $tests += "Login atendimento: OK" } else { $tests += "Login atendimento: FAIL ($($r.StatusCode))"; $failed++ }
} catch { if ($_.Exception.Response.StatusCode -eq 302) { $tests += "Login atendimento: OK" } else { $tests += "Login atendimento: FAIL"; $failed++ } }

try {
    $r = Invoke-WebRequest "http://127.0.0.1:5000/inicio_colaborador" -Method POST -Body "nome=Teste CI" -UseBasicParsing -MaximumRedirection 0
    if ($r.StatusCode -eq 302) { $tests += "Login colaborador: OK" } else { $tests += "Login colaborador: FAIL ($($r.StatusCode))"; $failed++ }
} catch { if ($_.Exception.Response.StatusCode -eq 302) { $tests += "Login colaborador: OK" } else { $tests += "Login colaborador: FAIL"; $failed++ } }

# 3i: Page rendering
try {
    $r = Invoke-WebRequest "http://127.0.0.1:5000/" -UseBasicParsing
    if ($r.StatusCode -eq 200) { $tests += "Pagina inicial: OK" } else { $tests += "Pagina inicial: FAIL"; $failed++ }
} catch { $tests += "Pagina inicial: FAIL ($_)"; $failed++ }
try {
    $r = Invoke-WebRequest "http://127.0.0.1:5000/admin" -UseBasicParsing
    if ($r.StatusCode -eq 200) { $tests += "Pagina admin: OK" } else { $tests += "Pagina admin: FAIL"; $failed++ }
} catch { $tests += "Pagina admin: FAIL ($_)"; $failed++ }
try {
    $r = Invoke-WebRequest "http://127.0.0.1:5000/logout" -UseBasicParsing -MaximumRedirection 0
    if ($r.StatusCode -eq 302) { $tests += "Logout redirect: OK" } else { $tests += "Logout redirect: FAIL"; $failed++ }
} catch { if ($_.Exception.Response.StatusCode -eq 302) { $tests += "Logout redirect: OK" } else { $tests += "Logout redirect: FAIL"; $failed++ } }
try {
    $r = Invoke-WebRequest "http://127.0.0.1:5000/historico" -UseBasicParsing
    if ($r.StatusCode -eq 200) { $tests += "Pagina historico: OK" } else { $tests += "Pagina historico: FAIL"; $failed++ }
} catch { $tests += "Pagina historico: FAIL ($_)"; $failed++ }

# 3j: Admin login
try {
    $r = Invoke-WebRequest "http://127.0.0.1:5000/admin/login" -Method POST -Body "usuario=admin&senha=admin" -UseBasicParsing -MaximumRedirection 0
    $cookies = $r.Headers['Set-Cookie']
    if ($r.StatusCode -eq 302 -and $cookies) { $tests += "Admin login: OK" } else { $tests += "Admin login: FAIL ($($r.StatusCode))"; $failed++ }
} catch { if ($_.Exception.Response.StatusCode -eq 302) { $tests += "Admin login: OK" } else { $tests += "Admin login: FAIL"; $failed++ } }

# 3k: Admin logout
try {
    $r = Invoke-WebRequest "http://127.0.0.1:5000/admin/logout" -UseBasicParsing -MaximumRedirection 0
    if ($r.StatusCode -eq 302) { $tests += "Admin logout: OK" } else { $tests += "Admin logout: FAIL ($($r.StatusCode))"; $failed++ }
} catch { if ($_.Exception.Response.StatusCode -eq 302) { $tests += "Admin logout: OK" } else { $tests += "Admin logout: FAIL"; $failed++ } }

# 3l: Stats API
try {
    $r = Invoke-WebRequest "http://127.0.0.1:5000/api/stats" -UseBasicParsing
    $j = $r.Content | ConvertFrom-Json
    if ($j.total -ge 0 -and $j.por_status -ne $null) { $tests += "API stats: OK" } else { $tests += "API stats: FAIL (resposta invalida)"; $failed++ }
} catch { $tests += "API stats: FAIL ($_)"; $failed++ }

# 3m: Backup API
try {
    $r = Invoke-WebRequest "http://127.0.0.1:5000/api/backup" -Method POST -UseBasicParsing
    $j = $r.Content | ConvertFrom-Json
    if ($j.ok -eq $true) { $tests += "API backup: OK" } else { $tests += "API backup: FAIL"; $failed++ }
} catch { $tests += "API backup: FAIL ($_)"; $failed++ }

# 3n: Change credentials (first login to get session cookie)
try {
    $session = Invoke-WebRequest "http://127.0.0.1:5000/admin/login" -Method POST -Body "usuario=admin&senha=admin" -UseBasicParsing -SessionVariable sess
    $r = Invoke-WebRequest "http://127.0.0.1:5000/api/admin/change-credentials" -Method POST -ContentType "application/json" -Body '{"usuario_atual":"admin","senha_atual":"admin","novo_usuario":"admin","nova_senha":"admin"}' -WebSession $sess -UseBasicParsing
    $j = $r.Content | ConvertFrom-Json
    if ($j.ok -eq $true) { $tests += "API change-credentials: OK" } else { $tests += "API change-credentials: FAIL"; $failed++ }
} catch { $tests += "API change-credentials: FAIL ($_)"; $failed++ }

# Print results
Write-Host "`n[4/4] Results:" -ForegroundColor Yellow
$tests | ForEach-Object { Write-Host "  $_" }

if ($failed -eq 0) {
    Write-Host "`n=== CI PASSED ($($tests.Count)/$($tests.Count)) ===" -ForegroundColor Green
} else {
    Write-Host "`n=== CI FAILED ($failed failures) ===" -ForegroundColor Red
}

# Cleanup
Stop-Job $job -ErrorAction SilentlyContinue
Remove-Job $job -ErrorAction SilentlyContinue
Get-Process -Name python -ErrorAction SilentlyContinue | Stop-Process -Force
Remove-Item ".agenda.ci.*" -Force -ErrorAction SilentlyContinue
Remove-Item ".agenda.test.*" -Force -ErrorAction SilentlyContinue
Remove-Item "$env:TEMP\agenda_test*" -Force -ErrorAction SilentlyContinue

if ($failed -gt 0) { exit 1 }
