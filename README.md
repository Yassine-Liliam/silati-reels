# silati-reels

Publication automatique des reels Silati sur Instagram.

- La tâche planifiée Claude de 16h (heure de Casablanca) génère un reel, puis pousse un commit unique sur une nouvelle branche `reel/AAAA-MM-JJ` : `reel.mp4`, `caption.txt`, le workflow et le script. Pas de force push.
- `Publish reel` (`.github/workflows/publish.yml`) publie le reel via l'API Instagram (Instagram Login, `graph.instagram.com`). Meta récupère la vidéo depuis l'URL `raw.githubusercontent.com` du commit, d'où le repo public.
- Un push sur une branche `test/...` lance le même flux **sans publier** (test à blanc).
- Après un succès, l'Action supprime la branche poussée.
- `Refresh Instagram token` renouvelle le token (valable 60 jours) le 1er et le 15 de chaque mois.

## Secrets (Settings → Secrets and variables → Actions)

| Secret | Contenu |
| --- | --- |
| `IG_ACCESS_TOKEN` | Token Instagram longue durée (généré dans le tableau de bord Meta) |
| `IG_USER_ID` | ID du compte Instagram professionnel |
| `GH_PAT` | Token GitHub fine-grained limité à ce repo, permission « Secrets : Read and write » |

Le token n'est jamais écrit dans le repo ni dans les logs.
