$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
python "$ScriptDir/scripts/install_kit.py" @args
exit $LASTEXITCODE

