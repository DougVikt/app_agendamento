@echo off
title Instalar Acesso - Sistema de Agendamento
set /p ip="Digite o IP ou nome do servidor (ex: 192.168.1.100): "
set /p porta="Digite a porta (ENTER para 5000): "
if "%porta%"=="" set porta=5000

set url=http://%ip%:%porta%
set desktop=%USERPROFILE%\Desktop
set atalho=%desktop%\Agendamento.url

echo [InternetShortcut] > "%atalho%"
echo URL=%url% >> "%atalho%"
echo IconFile=C:\Windows\System32\imageres.dll >> "%atalho%"
echo IconIndex=27 >> "%atalho%"

echo.
echo Atalho criado: %atalho%
echo URL: %url%
echo.
pause
