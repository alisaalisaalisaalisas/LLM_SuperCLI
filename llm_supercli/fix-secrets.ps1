# Script to fix constants.py during git rebase
# This script removes hardcoded secrets from constants.py

$file = "llm_supercli/llm_supercli/constants.py"

if (Test-Path $file) {
    $content = Get-Content $file -Raw
    
    # Replace any hardcoded values with empty strings and comments
    $content = $content -replace 'GOOGLE_CLIENT_ID: Final\[str\] = ".*"', 'GOOGLE_CLIENT_ID: Final[str] = ""  # Set via GOOGLE_CLIENT_ID env var or config.json'
    $content = $content -replace 'GOOGLE_CLIENT_SECRET: Final\[str\] = ".*"', 'GOOGLE_CLIENT_SECRET: Final[str] = ""  # Set via GOOGLE_CLIENT_SECRET env var or config.json'
    $content = $content -replace 'GITHUB_CLIENT_ID: Final\[str\] = ".*"', 'GITHUB_CLIENT_ID: Final[str] = ""  # Set via GITHUB_CLIENT_ID env var or config.json'
    $content = $content -replace 'GITHUB_CLIENT_SECRET: Final\[str\] = ".*"', 'GITHUB_CLIENT_SECRET: Final[str] = ""  # Set via GITHUB_CLIENT_SECRET env var or config.json'
    
    Set-Content $file -Value $content -NoNewline
    
    git add $file
}
