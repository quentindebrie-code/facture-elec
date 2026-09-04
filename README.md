# Hympyr - préparation à la facturation électronique

Application Streamlit destinée au DAF et au référent conformité / sécurité SI pour qualifier le périmètre réglementaire, réaliser une recette documentée et générer un rapport PDF au gabarit Hympyr.

## Périmètre et référentiel

La grille est rattachée aux sources officielles suivantes, consultables depuis l'application :

- spécifications externes DGFiP v3.2 du 30 avril 2026 ;
- annexes sémantiques v3.2, notamment l'annexe 1 e-invoicing et l'annexe 2 cycle de vie ;
- page DGFiP de présentation de la réforme, mise à jour le 26 mai 2026 ;
- liste officielle des plateformes agréées ;
- mentions obligatoires publiées par le ministère de l'Économie le 25 février 2026 ;
- doctrine BOFiP relative à la conservation des factures électroniques.

La matrice de correspondance et les limites de l'outil sont détaillées dans `REFERENTIEL.md`.

Le rapport produit constitue une preuve de préparation et de contrôle interne. Il ne vaut ni agrément, ni certification, ni décision de conformité délivrée par la DGFiP. La liste des plateformes et le référentiel doivent être revérifiés à la date de chaque contrôle.

## Parcours DAF

1. Profil et périmètre fiscal : taille, TVA, B2B France, B2C, international et encaissements.
2. Plateforme et annuaire : agrément définitif, ligne active, maille d'adressage et routage.
3. Formats et données : UBL, CII ou Factur-X, lisible, structuré et mentions applicables.
4. Réception et cycle de vie : flux nominal, statuts obligatoires et anomalies.
5. E-reporting : transactions, paiements, périodicité, corrections et rejets.
6. Sécurité et exploitation : habilitations, MFA, journaux, incidents et continuité.
7. Écarts : rattachement obligatoire à l'ID du contrôle concerné.
8. Synthèse : pièces justificatives, conclusion et génération du rapport PDF.

Chaque résultat doit être accompagné d'une preuve ou d'une justification. Les contrôles critiques ne peuvent pas être neutralisés par défaut avec `N/A`. Une non-conformité doit être reliée à une action corrective.

## Installation locale

Prérequis : Python 3.10 ou supérieur.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

Sous Windows :

```powershell
.venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```

Le gabarit PDF et les polices sont inclus dans `assets/`.

## Sécurité et conservation

L'application n'écrit aucune donnée métier dans une base. Les données restent dans la session Streamlit ; le brouillon JSON permet une reprise ultérieure.

Le PDF généré n'est pas la facture électronique originale. Hympyr doit conserver les factures reçues dans leur format informatique original et maintenir les garanties d'authenticité, d'intégrité et de lisibilité pendant la durée réglementaire applicable. Les rapports, brouillons et preuves doivent être rangés dans un emplacement sécurisé avec des droits maîtrisés.
