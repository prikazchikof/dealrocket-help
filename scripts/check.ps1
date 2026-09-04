$ErrorActionPreference = 'Stop'

$repoRoot = Split-Path -Parent $PSScriptRoot
$venvPath = Join-Path $repoRoot '.venv'
$pythonPath = Join-Path $venvPath 'Scripts\python.exe'
$mkdocsPath = Join-Path $venvPath 'Scripts\mkdocs.exe'

function Invoke-Checked {
    param(
        [Parameter(Mandatory = $true)]
        [scriptblock]$Command
    )

    & $Command
    if ($LASTEXITCODE -ne 0) {
        throw "Command failed with exit code $LASTEXITCODE"
    }
}

if (-not (Test-Path -LiteralPath $pythonPath)) {
    python -m venv $venvPath
}

Invoke-Checked { & $pythonPath -m pip install --disable-pip-version-check -r (Join-Path $repoRoot 'requirements.txt') }
Invoke-Checked { & $pythonPath (Join-Path $repoRoot 'scripts\validate_content.py') }
Invoke-Checked { & $pythonPath -m unittest discover -s (Join-Path $repoRoot 'tests') -v }
Invoke-Checked { & $mkdocsPath build --strict --config-file (Join-Path $repoRoot 'mkdocs.yml') }
Invoke-Checked { & $pythonPath (Join-Path $repoRoot 'scripts\check_search.py') (Join-Path $repoRoot 'site\search\search_index.json') }

Write-Host 'Verification passed: content safety, corpus, tests, strict site build, and search smoke.'
