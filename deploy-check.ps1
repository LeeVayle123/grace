param(
    [string]$RemoteUrl
)

Write-Host "Deploy check script — vérifie Git et prépare le push" -ForegroundColor Cyan

# Vérifier si git est installé
try {
    git --version > $null 2>&1
} catch {
    Write-Host "Git n'est pas installé sur cette machine. Installez Git et exécutez manuellement les commandes dans README_DEPLOY.md." -ForegroundColor Yellow
    exit 0
}

# Vérifier si on est dans un dépôt git
$insideRepo = & git rev-parse --is-inside-work-tree 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "Initialisation d'un dépôt git local..." -ForegroundColor Green
    git init
}

# Ajouter et committer
git add templates static app.py render.yaml || exit 1
if ((git status --porcelain) -ne '') {
    git commit -m "Add templates and static assets, ensure accueil.html present" || exit 1
} else {
    Write-Host "Aucun changement à committer." -ForegroundColor Yellow
}

if ($RemoteUrl) {
    git remote remove origin 2>$null | Out-Null
    git remote add origin $RemoteUrl
    git push -u origin HEAD
} else {
    Write-Host "Aucune URL distante fournie. Pour pousser, exécutez:`n  git remote add origin <url>`n  git push -u origin main`