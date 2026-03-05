# CLAUDE.md - Wine Cellar WhatsApp Chatbot

## Projet

Chatbot WhatsApp de gestion de cave à vin personnelle. L'utilisateur interagit en français via WhatsApp pour gérer sa collection de vins : ajouter, supprimer, rechercher des bouteilles, obtenir des accords mets-vins, consulter la maturité, noter ses dégustations, voir des statistiques.

## Stack technique

- **Backend** : Python 3.11+ / FastAPI (async)
- **LLM** : Mistral AI (`mistral-large-latest` pour NLU, `pixtral-large-latest` pour vision)
- **Base de données** : Supabase (PostgreSQL) via `supabase-py`
- **Messaging** : WhatsApp Business Cloud API (Meta)
- **Déploiement** : Docker + Docker Compose (serveur Hostinger KVM2)
- **Tests** : pytest + pytest-asyncio

## Conventions

- Type hints partout
- Docstrings en français
- Logging structuré avec `logging` (pas de print)
- Validation des données avec Pydantic v2
- Async/await pour tous les appels réseau
- Variables d'environnement via pydantic-settings
- Pas de secrets en dur dans le code

## Structure cible

```
wine-cellar-bot/
├── CLAUDE.md
├── app/
│   ├── __init__.py
│   ├── main.py
│   ├── config.py
│   ├── models/
│   │   ├── __init__.py
│   │   ├── bottle.py
│   │   └── conversation.py
│   ├── services/
│   │   ├── __init__.py
│   │   ├── whatsapp.py
│   │   ├── mistral_ai.py
│   │   ├── wine_manager.py
│   │   └── image_analyzer.py
│   ├── database/
│   │   ├── __init__.py
│   │   ├── supabase_client.py
│   │   └── queries.py
│   └── utils/
│       ├── __init__.py
│       ├── prompts.py
│       └── formatters.py
├── tests/
│   ├── __init__.py
│   ├── test_wine_manager.py
│   ├── test_mistral_ai.py
│   └── test_whatsapp.py
├── sql/
│   └── schema.sql
├── .env.example
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── README.md
```

---

# ÉTAPES DE DÉVELOPPEMENT

Exécute les étapes une par une. Ne passe à l'étape suivante que quand l'étape en cours est terminée et validée.

---

## ÉTAPE 1 : Initialisation du projet

### À faire
1. Créer la structure de dossiers complète (tous les `__init__.py` inclus)
2. Créer `requirements.txt` avec :
   ```
   fastapi>=0.104.0
   uvicorn[standard]>=0.24.0
   httpx>=0.25.0
   supabase>=2.0.0
   mistralai>=1.0.0
   python-dotenv>=1.0.0
   pydantic>=2.5.0
   pydantic-settings>=2.1.0
   python-multipart>=0.0.6
   pytest>=7.4.0
   pytest-asyncio>=0.23.0
   ```
3. Créer `.env.example` :
   ```env
   # WhatsApp Business API
   WHATSAPP_TOKEN=your_whatsapp_access_token
   WHATSAPP_PHONE_NUMBER_ID=your_phone_number_id
   WHATSAPP_VERIFY_TOKEN=your_custom_verify_token
   
   # Mistral AI
   MISTRAL_API_KEY=your_mistral_api_key
   
   # Supabase
   SUPABASE_URL=https://your-project.supabase.co
   SUPABASE_KEY=your_supabase_service_role_key
   
   # App
   APP_HOST=0.0.0.0
   APP_PORT=8000
   LOG_LEVEL=info
   CONVERSATION_HISTORY_LIMIT=20
   ```
4. Créer `app/config.py` : classe `Settings` avec pydantic-settings qui charge le `.env`

### Critère de validation
- `python -c "from app.config import Settings; print(Settings())"` fonctionne (avec un `.env` rempli)
- Tous les dossiers et fichiers existent

---

## ÉTAPE 2 : Schéma de base de données

### À faire
Créer `sql/schema.sql` avec :

**Table `bottles`** :
- `id` UUID PK default gen_random_uuid()
- `name` TEXT NOT NULL (nom du vin)
- `color` TEXT NOT NULL (rouge, blanc, rosé, champagne, mousseux, liquoreux)
- `region` TEXT (région viticole)
- `appellation` TEXT (appellation d'origine)
- `producer` TEXT (domaine/château)
- `vintage` INTEGER (millésime)
- `grape_varieties` TEXT[] (cépages, array PostgreSQL)
- `purchase_price` DECIMAL(10,2)
- `purchase_date` DATE
- `quantity` INTEGER NOT NULL DEFAULT 1
- `storage_location` TEXT (emplacement cave)
- `drink_from` INTEGER (année début fenêtre optimale)
- `drink_until` INTEGER (année fin fenêtre optimale)
- `notes` TEXT
- `image_url` TEXT
- `created_at` TIMESTAMPTZ DEFAULT now()
- `updated_at` TIMESTAMPTZ DEFAULT now()

**Table `tasting_log`** :
- `id` UUID PK
- `bottle_id` UUID FK -> bottles.id (ON DELETE SET NULL)
- `bottle_name` TEXT NOT NULL (copie du nom pour garder l'historique même si la bouteille est supprimée)
- `tasted_at` DATE NOT NULL DEFAULT CURRENT_DATE
- `rating` INTEGER CHECK (rating >= 1 AND rating <= 5)
- `tasting_notes` TEXT
- `food_pairing` TEXT
- `occasion` TEXT
- `created_at` TIMESTAMPTZ DEFAULT now()

**Table `wishlist`** :
- `id` UUID PK
- `name` TEXT NOT NULL
- `notes` TEXT
- `priority` INTEGER DEFAULT 3 CHECK (priority >= 1 AND priority <= 5)
- `added_at` TIMESTAMPTZ DEFAULT now()

**Table `conversation_history`** :
- `id` UUID PK
- `phone_number` TEXT NOT NULL
- `role` TEXT NOT NULL (user ou assistant)
- `content` TEXT NOT NULL
- `created_at` TIMESTAMPTZ DEFAULT now()

**Aussi** :
- Index sur `conversation_history(phone_number, created_at DESC)`
- Index sur `bottles(color)`
- Index sur `bottles(region)`
- Trigger auto-update `updated_at` sur `bottles`
- Activer Row Level Security sur toutes les tables (politique allow all pour le service role)

### Critère de validation
- Le SQL est syntaxiquement correct
- Peut être copié-collé dans le SQL Editor de Supabase

---

## ÉTAPE 3 : Client Supabase et modèles Pydantic

### À faire
1. `app/database/supabase_client.py` :
   - Fonction `get_supabase_client()` qui retourne un client Supabase singleton
   - Utilise les settings de `config.py`

2. `app/models/bottle.py` :
   - `BottleCreate` : modèle Pydantic pour la création (tous les champs optionnels sauf name et color)
   - `BottleUpdate` : modèle Pydantic pour la mise à jour (tous les champs optionnels)
   - `BottleResponse` : modèle complet avec id, created_at, updated_at
   - `TastingNoteCreate` : modèle pour ajouter une note de dégustation
   - `TastingNoteResponse` : modèle de réponse avec id
   - `WishlistItemCreate` / `WishlistItemResponse`

3. `app/models/conversation.py` :
   - `ConversationMessage` : phone_number, role, content
   - `MistralIntent` : modèle Pydantic pour la réponse structurée de Mistral (intent, parameters, response_text)

4. `app/database/queries.py` :
   - Fonctions async CRUD pour `bottles` : add, get_by_id, search (filtres multiples), list_all, update, delete, decrement_quantity
   - Fonctions async pour `tasting_log` : add, list (avec filtre date/note)
   - Fonctions async pour `wishlist` : add, list, delete
   - Fonctions async pour `conversation_history` : add_message, get_recent (N derniers messages par phone_number)
   - Fonction `get_stats()` : requêtes d'agrégation (count, group by color, group by region, sum prix, etc.)

### Critère de validation
- Les modèles Pydantic sont instanciables avec des données de test
- `python -c "from app.database.queries import *"` fonctionne sans erreur d'import

---

## ÉTAPE 4 : Service WhatsApp Business API

### À faire
`app/services/whatsapp.py` :

1. Classe `WhatsAppService` avec :
   - `__init__(self, token, phone_number_id)` : initialise un client httpx async
   - `async send_message(self, to: str, text: str)` : envoie un message texte via l'API WhatsApp
     - POST `https://graph.facebook.com/v21.0/{phone_number_id}/messages`
     - Headers : Authorization Bearer {token}
     - Body : `{"messaging_product": "whatsapp", "to": to, "type": "text", "text": {"body": text}}`
   - `async download_media(self, media_id: str) -> bytes` : télécharge une image envoyée par l'utilisateur
     - GET `https://graph.facebook.com/v21.0/{media_id}` pour obtenir l'URL de téléchargement
     - GET sur l'URL retournée pour télécharger le fichier
   - `parse_incoming_message(self, payload: dict) -> dict | None` : parse le webhook entrant et extrait :
     - `phone_number` : numéro de l'expéditeur
     - `message_type` : "text" ou "image"
     - `text` : contenu du message (si texte)
     - `media_id` : ID du media (si image)
     - Retourne None si le payload n'est pas un message valide (ex: statut de livraison)

2. Dans `app/main.py` :
   - `GET /webhook` : vérification Meta (compare verify_token, retourne le challenge)
   - `POST /webhook` : réception des messages (pour l'instant, juste parse et log le message, réponse echo)
   - `GET /health` : retourne `{"status": "ok"}`

### Critère de validation
- `uvicorn app.main:app --reload` démarre sans erreur
- `GET /health` retourne 200
- `GET /webhook?hub.mode=subscribe&hub.verify_token=test&hub.challenge=abc` retourne "abc"

---

## ÉTAPE 5 : Service Mistral AI (NLU)

### À faire
1. `app/utils/prompts.py` : contient les system prompts comme constantes

   **SYSTEM_PROMPT_NLU** :
   ```
   Tu es "Sommelier", un assistant virtuel expert en vin, passionné et amical.
   Tu gères la cave à vin personnelle de l'utilisateur via WhatsApp.
   
   RÔLE : Analyser chaque message et retourner un JSON structuré.
   
   FORMAT DE RÉPONSE (JSON strict, rien d'autre) :
   {
     "intent": "<intent>",
     "parameters": { ... },
     "response_text": "<ta réponse conversationnelle en français>"
   }
   
   INTENTS DISPONIBLES :
   - "add_bottle" : Ajouter une bouteille. Params: {name, color, region, appellation, producer, vintage (int), grape_varieties (list), purchase_price (float), quantity (int), storage_location, drink_from (int), drink_until (int), notes}
   - "remove_bottle" : Retirer/boire une bouteille. Params: {search_query, quantity_to_remove (int)}
   - "search_bottles" : Chercher dans la cave. Params: {query, color, region, vintage_min (int), vintage_max (int), price_min (float), price_max (float)}
   - "list_all" : Lister toute la cave. Params: {}
   - "get_stats" : Voir les statistiques. Params: {}
   - "food_pairing" : Accord mets-vin. Params: {dish_description}
   - "maturity_check" : Vérifier quels vins sont prêts. Params: {}
   - "add_tasting_note" : Noter une dégustation. Params: {search_query, rating (int 1-5), tasting_notes, food_pairing, occasion}
   - "view_history" : Voir l'historique des dégustations. Params: {limit (int), min_rating (int)}
   - "add_wishlist" : Ajouter à la liste de souhaits. Params: {name, notes, priority (int 1-5)}
   - "view_wishlist" : Voir la liste de souhaits. Params: {}
   - "help" : Demande d'aide. Params: {}
   - "unknown" : Message pas clair ou infos manquantes. Params: {}
   
   RÈGLES :
   1. Réponds TOUJOURS en français dans response_text
   2. Sois chaleureux et passionné, utilise des emojis vin avec modération (🍷🍇🥂)
   3. Si des infos essentielles manquent pour une action, utilise intent="unknown" et pose des questions dans response_text
   4. Pour add_bottle, seuls name et color sont obligatoires. Encourage l'utilisateur à donner plus d'infos mais n'insiste pas
   5. Pour remove_bottle, search_query doit permettre d'identifier la bouteille (nom, millésime, etc.)
   6. Sois flexible dans l'interprétation : "un bordeaux rouge" -> color="rouge", region="Bordeaux"
   7. Les paramètres non fournis doivent être null (pas de chaîne vide)
   8. Pour food_pairing, reformule le plat de manière claire dans dish_description
   9. Retourne UNIQUEMENT le JSON, aucun texte avant ou après
   ```

   **SYSTEM_PROMPT_VISION** :
   ```
   Tu es un expert en vin et en lecture d'étiquettes. Analyse cette photo d'étiquette de bouteille de vin.
   
   Extrais les informations suivantes et retourne un JSON strict (rien d'autre) :
   {
     "name": "nom complet du vin tel qu'écrit sur l'étiquette",
     "producer": "domaine, château ou maison",
     "appellation": "appellation d'origine contrôlée",
     "region": "région viticole (Bordeaux, Bourgogne, Rhône, Loire, Alsace, Champagne, Languedoc, Provence, etc.)",
     "vintage": 2020,
     "color": "rouge|blanc|rosé|champagne|mousseux|liquoreux",
     "grape_varieties": ["cépage1", "cépage2"],
     "confidence": 0.85
   }
   
   RÈGLES :
   - Si une info n'est pas visible sur l'étiquette, mets null
   - Pour la couleur, déduis-la si possible (ex: "Chablis" = blanc, "Saint-Émilion" = rouge)
   - vintage doit être un integer ou null
   - confidence = ton niveau de confiance global (0.0 à 1.0)
   - Retourne UNIQUEMENT le JSON
   ```

   **SYSTEM_PROMPT_FOOD_PAIRING** :
   ```
   Tu es un sommelier expert. L'utilisateur prépare un repas et veut savoir quelle bouteille choisir dans sa cave.
   
   Voici les bouteilles disponibles dans sa cave :
   {bottles_list}
   
   Suggère les 3 meilleures bouteilles pour accompagner le plat décrit, en expliquant pourquoi chaque vin convient.
   Si aucune bouteille ne convient parfaitement, suggère le type de vin idéal et propose d'ajouter à la wishlist.
   
   Réponds en français, de manière chaleureuse et passionnée. Utilise le format :
   🥇 [Nom du vin, millésime] - [Explication courte]
   🥈 [Nom du vin, millésime] - [Explication courte]
   🥉 [Nom du vin, millésime] - [Explication courte]
   ```

2. `app/services/mistral_ai.py` :
   - Classe `MistralService` avec :
     - `__init__(self, api_key)` : initialise le client Mistral
     - `async analyze_message(self, user_message: str, conversation_history: list[dict]) -> MistralIntent` :
       - Envoie le message + historique au modèle `mistral-large-latest`
       - Parse la réponse JSON en `MistralIntent`
       - En cas d'erreur de parsing, retourne un intent "unknown" avec un message d'excuse
     - `async analyze_image(self, image_bytes: bytes, mime_type: str) -> dict` :
       - Encode l'image en base64
       - Envoie à `pixtral-large-latest` avec SYSTEM_PROMPT_VISION
       - Parse et retourne le JSON des infos extraites
     - `async get_food_pairing(self, dish: str, bottles: list[dict]) -> str` :
       - Formate la liste des bouteilles
       - Envoie à `mistral-large-latest` avec SYSTEM_PROMPT_FOOD_PAIRING
       - Retourne la réponse textuelle (pas de JSON ici)

### Critère de validation
- Les prompts sont bien structurés et complets
- `from app.services.mistral_ai import MistralService` fonctionne
- Le parsing JSON inclut une gestion d'erreur robuste (try/except avec fallback)

---

## ÉTAPE 6 : Logique métier Wine Manager

### À faire
`app/services/wine_manager.py` :

Classe `WineManager` qui orchestre les actions selon l'intent reçu :

- `async handle_intent(self, intent: MistralIntent, phone_number: str) -> str` :
  - Switch sur `intent.intent` et dispatch vers la méthode correspondante
  - Retourne le texte de réponse final à envoyer à l'utilisateur

- `async add_bottle(self, params: dict) -> str` :
  - Crée un `BottleCreate` depuis les params
  - Insère dans Supabase via queries
  - Retourne confirmation avec résumé de la bouteille ajoutée

- `async remove_bottle(self, params: dict) -> str` :
  - Recherche la bouteille via search_query
  - Si plusieurs résultats : demande à l'utilisateur de préciser (retourne la liste)
  - Si un seul résultat :
    - Si quantity > quantity_to_remove : décrémente
    - Si quantity <= quantity_to_remove : propose de noter la dégustation avant suppression
  - Retourne confirmation

- `async search_bottles(self, params: dict) -> str` :
  - Appelle queries.search avec les filtres
  - Formate les résultats (max 10 par page)
  - Retourne la liste formatée ou "Aucune bouteille trouvée"

- `async list_all(self) -> str` :
  - Récupère toutes les bouteilles
  - Groupe par couleur, puis par région
  - Formate avec emojis couleur (🔴⚪🌸🥂)

- `async get_stats(self) -> str` :
  - Appelle queries.get_stats()
  - Formate : total, par couleur, par région (top 5), fourchette millésimes, valeur totale, derniers ajouts, dernières dégustations

- `async food_pairing(self, params: dict, mistral_service) -> str` :
  - Récupère toutes les bouteilles de la cave
  - Appelle mistral_service.get_food_pairing()
  - Retourne les suggestions

- `async maturity_check(self) -> str` :
  - Récupère les bouteilles ayant drink_from ou drink_until renseigné
  - Compare avec l'année en cours
  - Catégorise : "Trop jeune 🌱", "Fenêtre optimale ✅", "À boire rapidement ⚠️", "Passé le pic 📉"
  - Trie par urgence (à boire rapidement en premier)

- `async add_tasting_note(self, params: dict) -> str` :
  - Recherche la bouteille
  - Crée l'entrée dans tasting_log
  - Décrémente la quantité de la bouteille (ou la supprime si quantity = 1)
  - Retourne confirmation avec la note

- `async view_history(self, params: dict) -> str` :
  - Récupère les dégustations récentes (avec filtres optionnels)
  - Formate avec étoiles (⭐) pour les notes

- `async add_wishlist(self, params: dict) -> str` / `async view_wishlist(self) -> str`

- `async help(self) -> str` :
  - Retourne un message d'aide listant toutes les fonctionnalités disponibles

### Critère de validation
- Toutes les méthodes sont implémentées avec gestion d'erreur
- Les réponses sont formatées pour WhatsApp (max 4096 chars, emojis, *gras*)

---

## ÉTAPE 7 : Connecter le flux complet

### À faire
Modifier `app/main.py` pour connecter tous les services :

```python
# Flux principal du POST /webhook :
# 1. Parse le message WhatsApp entrant
# 2. Si c'est un message texte :
#    a. Charger les N derniers messages de conversation_history
#    b. Envoyer à MistralService.analyze_message()
#    c. Passer l'intent à WineManager.handle_intent()
#    d. Envoyer la réponse via WhatsAppService.send_message()
#    e. Sauvegarder les 2 messages (user + assistant) dans conversation_history
# 3. Si c'est une image :
#    a. Télécharger l'image via WhatsAppService.download_media()
#    b. Analyser via MistralService.analyze_image()
#    c. Formater les infos extraites et demander confirmation
#    d. Envoyer via WhatsApp
#    e. Sauvegarder dans conversation_history
# 4. Retourner 200 OK immédiatement (traitement en background avec BackgroundTasks)
```

Points importants :
- Utiliser `BackgroundTasks` de FastAPI pour traiter le message en arrière-plan (le webhook Meta attend un 200 rapide)
- Gérer le cas où l'utilisateur confirme l'ajout d'une bouteille après analyse d'image (via conversation_history, Mistral comprendra le contexte)
- Logger chaque étape du flux
- Capturer toutes les exceptions pour ne jamais crasher le webhook

### Critère de validation
- Le serveur démarre avec `uvicorn app.main:app --reload`
- Un message texte simulé via curl déclenche tout le flux (avec un .env valide)
- Les erreurs sont catchées et loguées proprement

---

## ÉTAPE 8 : Analyse d'images (Pixtral)

### À faire
`app/services/image_analyzer.py` :

Classe `ImageAnalyzer` qui :
1. Reçoit les bytes d'une image
2. Appelle `MistralService.analyze_image()`
3. Valide les données extraites (vérifications basiques : vintage entre 1900 et année en cours, couleur dans la liste autorisée, etc.)
4. Formate un message de confirmation pour l'utilisateur :
   ```
   📸 J'ai analysé l'étiquette ! Voici ce que j'ai trouvé :
   
   🍷 *Château Margaux 2015*
   📍 Margaux, Bordeaux
   🏰 Château Margaux
   🍇 Cabernet Sauvignon, Merlot
   🎨 Rouge
   
   Confiance : ⭐⭐⭐⭐ (85%)
   
   Tu veux que j'ajoute cette bouteille à ta cave ? Tu peux aussi corriger les infos si besoin.
   ```
5. Stocke temporairement les infos extraites dans `conversation_history` pour que Mistral puisse les utiliser quand l'utilisateur confirme

### Critère de validation
- Le formatage du message est clair et lisible sur WhatsApp
- La validation des données ne plante pas sur des valeurs null
- Le flux image -> analyse -> confirmation -> ajout fonctionne de bout en bout

---

## ÉTAPE 9 : Formatage WhatsApp

### À faire
`app/utils/formatters.py` :

Fonctions utilitaires :
- `format_bottle(bottle: dict) -> str` : formate une bouteille sur 2-3 lignes avec emojis
- `format_bottle_list(bottles: list[dict], title: str) -> str` : formate une liste groupée, avec pagination si > 10
- `format_stats(stats: dict) -> str` : formate les statistiques de manière visuelle
- `format_tasting_log(entries: list[dict]) -> str` : formate l'historique de dégustation
- `format_wishlist(items: list[dict]) -> str` : formate la wishlist
- `format_maturity_report(categories: dict) -> str` : formate le rapport de maturité
- `truncate_message(text: str, max_length: int = 4096) -> str` : tronque si nécessaire avec "... (suite)"
- `color_emoji(color: str) -> str` : retourne l'emoji correspondant à la couleur
- `rating_stars(rating: int) -> str` : retourne des étoiles (ex: ⭐⭐⭐⭐)

Rappel formatage WhatsApp :
- `*gras*`
- `_italique_`
- `~barré~`
- ``` `code` ```
- Pas de markdown complexe, pas de tableaux, pas de HTML

### Critère de validation
- Chaque fonction produit un output lisible et compact
- Aucun message ne dépasse 4096 caractères
- Les emojis sont utilisés de manière cohérente

---

## ÉTAPE 10 : Tests

### À faire
1. `tests/test_wine_manager.py` :
   - Tester add_bottle avec données complètes et minimales
   - Tester search avec différents filtres
   - Tester remove_bottle (cas quantity > 1 et quantity = 1)
   - Tester maturity_check avec différentes dates
   - Tester get_stats
   - Mocker les appels Supabase

2. `tests/test_mistral_ai.py` :
   - Tester analyze_message avec différents messages
   - Tester le parsing JSON (cas valide, invalide, partiel)
   - Tester analyze_image
   - Mocker les appels Mistral

3. `tests/test_whatsapp.py` :
   - Tester parse_incoming_message avec différents payloads (texte, image, statut)
   - Tester le webhook GET (vérification)
   - Tester le webhook POST avec TestClient FastAPI
   - Mocker les appels HTTP

### Critère de validation
- `pytest tests/ -v` passe à 100%
- Tous les cas limites sont couverts (données manquantes, erreurs réseau, JSON invalide)

---

## ÉTAPE 11 : Docker et README

### À faire
1. `Dockerfile` :
   ```dockerfile
   FROM python:3.11-slim
   WORKDIR /app
   COPY requirements.txt .
   RUN pip install --no-cache-dir -r requirements.txt
   COPY . .
   EXPOSE 8000
   CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
   ```

2. `docker-compose.yml` :
   ```yaml
   version: "3.8"
   services:
     wine-bot:
       build: .
       env_file: .env
       ports:
         - "8000:8000"
       restart: unless-stopped
       networks:
         - default
   ```

3. `README.md` complet avec :
   - Description du projet
   - Prérequis (compte Meta Developer, projet Supabase, clé API Mistral)
   - Instructions d'installation pas à pas :
     1. Cloner le repo
     2. Créer le projet Supabase et exécuter schema.sql
     3. Configurer l'app Meta Developer et le webhook WhatsApp
     4. Copier .env.example vers .env et remplir les variables
     5. Lancer avec docker-compose up -d
     6. Configurer le webhook Meta vers https://ton-domaine.com/webhook
   - Guide d'utilisation (exemples de messages)
   - Architecture technique (schéma simplifié du flux)
   - Roadmap / améliorations futures

### Critère de validation
- `docker build -t wine-bot .` réussit
- `docker-compose up` démarre l'application
- Le README est clair et complet
