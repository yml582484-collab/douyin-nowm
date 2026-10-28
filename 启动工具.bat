@echo off
chcp 65001 >nul
title 抖音去水印工具
cd /d "%~dp0"
python app.py
pause
