# Linkboard

Petite interface web pour ranger les liens de vos applications par catégorie.
Flask + SQLite (un seul fichier `links.db`), packagée dans une image Docker.

## Lancer

```bash
docker compose up -d --build
```

Puis ouvrir http://localhost:8080

Sans compose :

```bash
docker build -t linkboard .
docker run -d --name linkboard -p 8080:8080 -v $(pwd)/data:/data linkboard
```

La base SQLite est stockée dans `./data/links.db` (volume `/data`) : pensez à la sauvegarder.

## Fonctionnalités
- Tableau de bord des liens groupés par catégorie (couleur, ordre), avec favicon
- Formulaire d'ajout / modification / suppression de liens
- Formulaire de gestion des catégories (supprimer une catégorie garde ses liens en « Sans catégorie »)
- Recherche instantanée (touche `/`)
- Thème clair / sombre automatique

## Variables d'environnement
| Variable | Défaut | Rôle |
|---|---|---|
| `DB_PATH` | `/data/links.db` | Emplacement de la base |
| `SECRET_KEY` | `change-me` | Clé de session Flask (messages flash) |
