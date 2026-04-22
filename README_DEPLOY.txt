Quick deploy checklist

1) If you have Git locally and want to push changes to your repo (recommended):

   Open PowerShell in the project root and run:

   .\commit_and_push.ps1 -RemoteUrl "https://github.com/yourname/yourrepo.git"

   Or run the manual commands:

   git init # if not already a repo
   git add templates static app.py
   git commit -m "Add templates/static and fallback accueil.html"
   git push origin main

2) If you cannot push from this machine, create an archive and upload to Render:

   Run:

   .\deploy-pack.ps1

   Then upload the generated deploy.zip to your Render service (or extract locally and push to git from another machine).

3) After pushing to the repo, trigger a redeploy on Render.

4) If the app still fails with TemplateNotFound, check Render build logs and ensure the repo contains `templates/accueil.html` and other templates.

If you want, I can try to run the commit script here (requires Git installed); otherwise run it locally and tell me the result.