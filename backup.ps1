param(
    [string]$Caminho = (Split-Path $PSCommandPath),
    [string]$Destino = "$env:USERPROFILE\Desktop"
)

$db = Join-Path $Caminho ".agenda.db"
if (!(Test-Path $db)) { Write-Host "Banco nao encontrado: $db" -ForegroundColor Red; exit 1 }

$data = Get-Date -Format "yyyy-MM-dd"
$nome = "agenda-$data.db"
$dest = Join-Path $Destino $nome

Copy-Item $db $dest -Force
Write-Host "Backup concluido: $dest" -ForegroundColor Green

# para automatizar em caso de servidor interno , colocar em agendador de tarefa