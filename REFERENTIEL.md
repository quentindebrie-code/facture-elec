# Référentiel de contrôle

## Version utilisée

La version de l'outil est construite sur les spécifications externes de la facturation électronique DGFiP v3.2 du 30 avril 2026 et leurs annexes publiées sur impots.gouv.fr.

Date de vérification documentaire de cette version de l'outil : 4 septembre 2026.

## Sources officielles

| Identifiant dans l'outil | Source |
| --- | --- |
| DGFiP-v3.2 | [Spécifications externes et normes](https://www.impots.gouv.fr/specifications-externes-b2b) |
| DGFiP-Principes | [Je découvre la facturation électronique](https://www.impots.gouv.fr/professionnel/je-decouvre-la-facturation-electronique) |
| DGFiP-PA | [Liste des plateformes agréées](https://www.impots.gouv.fr/je-consulte-la-liste-des-plateformes-agreees) |
| Mentions | [Mentions obligatoires d'une facture](https://www.economie.gouv.fr/entreprises/gerer-son-entreprise-au-quotidien/gerer-sa-comptabilite-et-ses-demarches/mentions-obligatoires-dune-facture-tout-savoir) |
| BOFiP-Conservation | [BOI-CF-COM-10-10-30](https://bofip.impots.gouv.fr/bofip/645-PGP.html/identifiant=BOI-CF-COM-10-10-30-20250903) |

## Correspondance fonctionnelle

| Domaine | Références principales | Contrôle réalisé par l'outil |
| --- | --- | --- |
| Calendrier et périmètre | DGFiP-Principes | Qualification de la taille, des opérations et des volets applicables |
| Plateforme agréée | DGFiP-PA | Preuve datée de l'agrément définitif |
| Annuaire et adressage | DGFiP-v3.2 §3.5 | Ligne active, plateforme de réception, maille et routage |
| Formats | DGFiP-v3.2 §3.6.3, AFNOR XP Z12-012 | UBL, CII, Factur-X, structuré et lisible |
| Données de facture | Annexe 1 v1.2, article 242 nonies A | Identifiants, montants, TVA, lignes et mentions applicables |
| Cycle de vie | DGFiP-v3.2 §3.6.4 | Statuts obligatoires 200, 210, 212 et 213 |
| Délais des statuts | DGFiP-v3.2 §3.6.6 | Preuve de transmission sous 24 heures par la plateforme |
| E-reporting | DGFiP-v3.2 §3.7 | Transactions, paiements, périodes, corrections et rejets |
| Conservation | BOFiP-Conservation | Conservation du format informatique original et garanties associées |
| Sécurité SI | Référentiel interne Hympyr | Habilitations, MFA, journaux, incidents, continuité et protection des preuves |

## Limites assumées

- L'application ne vérifie pas en direct la liste des plateformes : le contrôleur doit joindre une preuve officielle datée.
- Elle ne remplace pas un validateur syntaxique XSD, Schematron ou Factur-X. Le rapport du validateur ou de la plateforme doit être référencé comme preuve.
- Elle ne transmet aucune facture ni donnée à l'administration.
- Elle n'est ni une plateforme agréée, ni une solution de facturation, ni un outil d'e-reporting.
- La qualification des cas fiscaux particuliers doit être validée avec la direction financière, le conseil fiscal et la plateforme.
- Le rapport constate les diligences réalisées ; il ne constitue pas une certification de conformité délivrée par la DGFiP.

## Règle de mise à jour

Avant chaque campagne de contrôle, vérifier la page des spécifications externes, la liste des plateformes agréées et les éventuelles évolutions réglementaires. Toute nouvelle version doit entraîner une revue des libellés, identifiants, règles conditionnelles et pièces justificatives minimales de l'application.
