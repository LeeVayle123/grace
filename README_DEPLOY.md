But de ce dossier

Ce dépôt contient une application Flask. Render signale une erreur `TemplateNotFound: accueil.html` lorsqu'un dossier `templates/` ou `static/` n'est pas présent dans le dépôt distant.

Étapes recommandées pour déployer depuis votre machine locale :

1) Vérifier/installer Git
   - Windows: https://git-scm.com/download/win

2) Vérifier les fichiers suivis
   - `git status`
   - `git ls-files templates | wc -l` (ou `git ls-files templates`)

3) Ajouter, committer et pousser (exécuter depuis la racine du projet)

```powershell
# si pas encore de repo
git init
# ajouter les templates et les statics
git add templates static app.py render.yaml
git commit -m "Add templates and static assets (ensure accueil.html present)"
# configurer le remote si nécessaire
git remote add origin <your-repo-url>
# pousser
git push -u origin main
```

4) Alternative: Uploader l'archive ZIP sur Render
   - Le fichier `grace-main-deploy.zip` a été généré dans le dossier du projet; vous pouvez le télécharger via l'interface Render (Create new service → Deploy from archive).

5) Débogage côté Render
   - Vérifiez les logs de build et d'exécution dans le dashboard Render.

Si vous voulez, exécutez le script `deploy-check.ps1` localement (ou je peux l'exécuter ici si Git est disponible et si vous fournissez l'URL remote).