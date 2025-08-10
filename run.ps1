# 切换到脚本所在目录
Set-Location $PSScriptRoot

# 设置 PYTHONPATH 环境变量
# 注意，根据我们之前的分析，路径应该是 TradingAgents 子目录
$env:PYTHONPATH = Join-Path (Get-Location).Path "TradingAgents"

# 运行 Python 脚本
python autorun.py