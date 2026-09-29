@echo off
setlocal
cd /d "%~dp0..\.."
py -3 tools\matrix_lab\minimax_matrix_runner.py --cfg tools\matrix_lab\minimax_matrix_runner.cfg %*
