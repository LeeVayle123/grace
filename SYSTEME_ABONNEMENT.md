# 📱 Système d'Abonnement et de Notifications

## Vue d'ensemble
Les clients peuvent maintenant s'abonner à la boutique pour recevoir des notifications chaque fois qu'un nouveau produit est ajouté par l'admin.

---

## 🔐 Modèles de données

### Client (modifié)
```python
- id: Identifiant unique
- nom: Nom du client
- postnom: Postnom
- telephone: Numéro de téléphone
- adresse: Adresse de livraison
- mot_de_passe: Mot de passe chiffré
- email: Email unique de l'abonné
- sexe: M ou F
- est_abonne: True si abonné
- date_abonnement: Date d'inscription
```

### Notification (nouveau)
```python
- id: Identifiant unique
- id_client: Référence au client abonné
- id_produit: Référence au nouveau produit
- titre: Titre de la notification
- message: Contenu du message
- type_notification: 'nouveau_produit', 'promotion', etc.
- est_lue: Boolean (lue ou non)
- date_creation: Timestamp de création
```

---

## 🎯 Flux utilisateur

### 1️⃣ S'abonner
```
Client clique sur le bouton "Mon compte" (icone utilisateur)
    ↓
Modal d'abonnement s'ouvre
    ↓
Client remplit le formulaire:
  - Nom (obligatoire)
  - Postnom
  - Sexe (obligatoire)
  - Email (obligatoire)
  - Mot de passe (obligatoire)
  - Téléphone
  - Adresse
    ↓
Clique "S'abonner"
    ↓
Nouveau client créé avec est_abonne=True
    ↓
Message de succès
```

### 2️⃣ Admin ajoute un produit
```
Admin accède à /produits
    ↓
Remplit le formulaire d'ajout de produit
    ↓
Clique "Ajouter"
    ↓
Produit créé en BD
    ↓
Pour CHAQUE client abonné:
  - Une notification est créée automatiquement
  - Titre: "Nouveau produit: [nom du produit]"
  - Message: Description du produit
    ↓
Notifications stockées en BD
```

### 3️⃣ Client abonné reçoit les notifications
```
Client se connecte/ou demande ses notifications
    ↓
Endpoint /api/abonne/<id>/notifications retourne toutes les notifications
    ↓
Les notifications non-lues sont affichées
    ↓
Client peut cliquer pour marquer comme lue
    ↓
Client peut voir les détails du produit
```

---

## 🔌 API Endpoints

### 📝 S'abonner
```http
POST /api/abonne/inscription
Content-Type: application/json

{
  "nom": "Jean",
  "postnom": "Dupont",
  "sexe": "M",
  "email": "jean@example.com",
  "mot_de_passe": "secure_password",
  "telephone": "+243991234567",
  "adresse": "123 Rue principale"
}
```

**Réponse (201):**
```json
{
  "success": true,
  "message": "Inscription réussie!...",
  "client_id": 42
}
```

---

### 📬 Récupérer les notifications
```http
GET /api/abonne/{client_id}/notifications
```

**Réponse (200):**
```json
{
  "notifications": [
    {
      "id": 1,
      "titre": "Nouveau produit: iPhone 17 Pro",
      "message": "Un nouveau produit 'iPhone 17 Pro' vient d'être ajouté...",
      "type": "nouveau_produit",
      "est_lue": false,
      "date": "21/04/2026 14:30",
      "id_produit": 5,
      "produit_nom": "iPhone 17 Pro",
      "produit_image": "https://..."
    }
  ]
}
```

---

### ✅ Marquer notification comme lue
```http
POST /api/abonne/notification/{notification_id}/marquer-lue
```

**Réponse (200):**
```json
{
  "success": true
}
```

---

### 👤 Récupérer infos abonné
```http
GET /api/abonne/{client_id}/info
```

**Réponse (200):**
```json
{
  "id": 42,
  "nom": "Jean",
  "postnom": "Dupont",
  "email": "jean@example.com",
  "sexe": "M",
  "telephone": "+243991234567",
  "adresse": "123 Rue principale",
  "est_abonne": true,
  "date_abonnement": "21/04/2026",
  "nb_non_lues": 3
}
```

---

### 🔓 Désabonner
```http
POST /api/abonne/{client_id}/desabonner
```

**Réponse (200):**
```json
{
  "success": true,
  "message": "Vous avez été désabonné"
}
```

---

## 🎨 Interface Frontend

### Modal d'abonnement
- S'ouvre au clic du bouton "Mon compte"
- Formulaire avec validation
- Message d'erreur en cas d'email déjà utilisé
- Animation fluide avec Framer Motion
- Responsive (mobile + desktop)

### Variables localStorage
- `abonne_client_id`: ID du client abonné (stocké pour les notifications futures)

---

## 🔄 Workflow complet

```
1. Client clique "Mon compte"
   ↓
2. Modal d'abonnement s'ouvre
   ↓
3. Client remplit et valide le formulaire
   ↓
4. POST /api/abonne/inscription
   ↓
5. Client stocké en BD avec est_abonne=True
   ↓
6. client_id sauvegardé en localStorage
   ↓
7. Admin ajoute un produit
   ↓
8. Boucle de création de notifications pour tous les abonnés
   ↓
9. Notifications visibles via GET /api/abonne/{id}/notifications
   ↓
10. Client marque comme lue
    ↓
11. POST /api/abonne/notification/{id}/marquer-lue
```

---

## 🛠️ Configuration requise

### Base de données
Les tables suivantes doivent être créées automatiquement:
- `clients` (modifiée)
- `notifications` (nouvelle)

### Variables d'environnement
- `DATABASE_URL` - Connexion PostgreSQL
- `SUPABASE_URL` - URL Supabase
- `SUPABASE_KEY` - Clé API Supabase

---

## 📊 Exemple d'utilisation JavaScript

```javascript
// S'abonner
const inscription = async (formData) => {
  const response = await fetch('/api/abonne/inscription', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(formData)
  });
  const data = await response.json();
  if (response.ok) {
    localStorage.setItem('abonne_client_id', data.client_id);
  }
};

// Récupérer les notifications
const chargerNotifications = async (clientId) => {
  const response = await fetch(`/api/abonne/${clientId}/notifications`);
  const data = await response.json();
  return data.notifications;
};

// Marquer comme lue
const marquerCommeLue = async (notificationId) => {
  await fetch(`/api/abonne/notification/${notificationId}/marquer-lue`, {
    method: 'POST'
  });
};
```

---

## 🎯 Points clés

✅ Système automatisé de notifications
✅ Validation complète des données
✅ Emails uniques (pas de doublon)
✅ Stockage sécurisé des mots de passe (bcrypt)
✅ Interface intuitive et responsive
✅ Intégration seamless avec l'interface existante

---

**Version:** 1.0
**Date:** 21/04/2026
**Statut:** ✅ Production-ready
