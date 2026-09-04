"""Référentiel et règles métier de l'outil Hympyr.

Le modèle distingue les exigences réglementaires vérifiables par l'entreprise
des contrôles de sécurité et d'exploitation internes. Les libellés réglementaires
sont rattachés à une source officielle et à sa version.
"""

from __future__ import annotations

from copy import deepcopy
from datetime import date
from typing import Any, Iterable


SCHEMA_VERSION = 2
REFERENCE_VERSION = "DGFiP - spécifications externes de la facturation électronique v3.2 du 30/04/2026"

OFFICIAL_SOURCES = [
    {"id": "DGFiP-v3.2", "label": REFERENCE_VERSION, "url": "https://www.impots.gouv.fr/specifications-externes-b2b"},
    {"id": "DGFiP-Principes", "label": "DGFiP - Je découvre la facturation électronique, mise à jour du 26/05/2026", "url": "https://www.impots.gouv.fr/professionnel/je-decouvre-la-facturation-electronique"},
    {"id": "DGFiP-PA", "label": "DGFiP - Liste officielle des plateformes agréées", "url": "https://www.impots.gouv.fr/je-consulte-la-liste-des-plateformes-agreees"},
    {"id": "Mentions", "label": "Ministère de l'Économie - Mentions obligatoires d'une facture, 25/02/2026", "url": "https://www.economie.gouv.fr/entreprises/gerer-son-entreprise-au-quotidien/gerer-sa-comptabilite-et-ses-demarches/mentions-obligatoires-dune-facture-tout-savoir"},
    {"id": "BOFiP-Conservation", "label": "BOFiP - BOI-CF-COM-10-10-30, conservation des factures électroniques", "url": "https://bofip.impots.gouv.fr/bofip/645-PGP.html/identifiant=BOI-CF-COM-10-10-30-20250903"},
]

RESULT_OPTIONS = ["Non contrôlé", "Conforme", "Non conforme", "N/A"]


def _control(identifier: str, control: str, expected: str, source: str, *, critical: bool = False) -> dict[str, Any]:
    return {"id": identifier, "controle": control, "attendu": expected, "source": source, "critique": critical, "resultat": "Non contrôlé", "preuve": ""}


PLATFORM_CONTROLS = [
    _control("PA-01", "Plateforme présente sur la liste officielle des plateformes agréées", "Agrément définitif vérifié sur impots.gouv.fr, avec date et preuve", "DGFiP-PA", critical=True),
    _control("PA-02", "Contrat ou mandat de réception actif pour l'entité contrôlée", "Périmètre, responsabilités et date d'effet documentés", "DGFiP-v3.2 §2.5", critical=True),
    _control("AN-01", "Entreprise identifiable dans l'annuaire à la bonne maille", "SIREN, SIRET, code routage ou suffixe cohérent avec l'organisation", "DGFiP-v3.2 §3.5.1 à §3.5.3", critical=True),
    _control("AN-02", "Plateforme de réception correctement rattachée dans l'annuaire", "Ligne active et période de validité contrôlée", "DGFiP-v3.2 §3.5.3", critical=True),
    _control("AN-03", "Adressage et routage testés sur la facture témoin", "La facture atteint l'entité et le service attendus", "DGFiP-v3.2 §3.5.4", critical=True),
    _control("PA-03", "Responsabilités entre plateforme, solution compatible et ERP documentées", "Aucune fonction réglementaire n'est attribuée à tort à une solution non agréée", "DGFiP - plateformes agréées"),
]

FORMAT_DATA_CONTROLS = [
    _control("FMT-01", "Facture reçue par l'intermédiaire d'une plateforme agréée", "Aucun recours à un simple PDF transmis par courriel pour le flux réglementaire", "DGFiP-Principes", critical=True),
    _control("FMT-02", "Format électronique accepté et identifié", "UBL, CII ou format mixte Factur-X ; le format réellement reçu est tracé", "DGFiP-v3.2 §2.6 et §3.6.3", critical=True),
    _control("FMT-03", "Données structurées exploitables", "XML accessible, lisible par le SI et cohérent avec la représentation humaine", "DGFiP-v3.2 §3.6.3 / AFNOR XP Z12-012", critical=True),
    _control("FMT-04", "Représentation lisible disponible", "La facture peut être présentée sans difficulté à l'utilisateur et à l'administration", "BOFiP - article 289 V CGI", critical=True),
    _control("BT-1", "Numéro unique de facture", "Identifiant présent et non altéré", "Annexe 1 v1.2 - BT-1 / Mentions", critical=True),
    _control("BT-2", "Date d'émission", "Date présente au format attendu", "Annexe 1 v1.2 - BT-2 / Mentions", critical=True),
    _control("BT-3", "Type de facture ou d'avoir", "Code de type renseigné et cohérent", "Annexe 1 v1.2 - BT-3", critical=True),
    _control("BT-5", "Devise de facturation", "Code ISO 4217 présent", "Annexe 1 v1.2 - BT-5", critical=True),
    _control("ID-01", "Identité et adresse du vendeur", "Nom, adresse et identifiant de l'entreprise présents", "Article 242 nonies A annexe II CGI / Mentions", critical=True),
    _control("BT-30", "SIREN du vendeur", "SIREN à 9 chiffres dans le champ structuré", "Annexe 1 v1.2 - BT-30", critical=True),
    _control("ID-02", "Identité et adresse de l'acheteur", "Nom et adresses client/facturation présents", "Article 242 nonies A annexe II CGI / Mentions", critical=True),
    _control("BT-47", "SIREN du client", "SIREN à 9 chiffres dans le champ structuré", "Annexe 1 v1.2 - BT-47 / nouvelle mention 2026", critical=True),
    _control("TVA-01", "Identifiants TVA applicables", "Numéros de TVA vendeur et client présents lorsque requis", "Article 242 nonies A annexe II CGI / Annexe 1 BT-31 et BT-48"),
    _control("OP-01", "Catégorie de l'opération", "Livraison de biens, prestation de services ou combinaison renseignée", "Nouvelle mention 2026 / Mentions", critical=True),
    _control("LIV-01", "Adresse complète de livraison lorsqu'elle diffère", "Mention présente si différente de l'adresse de facturation", "Nouvelle mention 2026 / Mentions"),
    _control("TVA-02", "Option pour le paiement de la TVA d'après les débits", "Mention présente lorsque l'option est exercée", "Nouvelle mention 2026 / Annexe 1 BT-8"),
    _control("LIG-01", "Détail des biens ou services", "Désignation, quantité, prix unitaire HT et taux ou exonération par ligne", "Article 242 nonies A annexe II CGI / Mentions", critical=True),
    _control("BT-109", "Montant total hors TVA", "Total HT structuré et cohérent avec les lignes", "Annexe 1 v1.2 - BT-109", critical=True),
    _control("BT-110", "Montant total de TVA", "Total TVA structuré et cohérent", "Annexe 1 v1.2 - BT-110", critical=True),
    _control("BG-23", "Ventilation de la TVA", "Base, montant et taux cohérents pour chaque catégorie de TVA", "Annexe 1 v1.2 - BG-23 / BT-116 à BT-121", critical=True),
    _control("PAY-01", "Mentions relatives au règlement", "Échéance, escompte, pénalités et indemnité forfaitaire présents", "Article 242 nonies A annexe II CGI / Mentions"),
    _control("CAS-01", "Mentions particulières applicables", "Autoliquidation, franchise, exonération ou autre mention ajoutée selon le cas", "Article 242 nonies A annexe II CGI / Mentions"),
]

RECEPTION_CONTROLS = [
    _control("REC-01", "Réception horodatée de la facture témoin", "Date et heure de mise à disposition traçables", "DGFiP-v3.2 §3.6", critical=True),
    _control("REC-02", "Notification au bon destinataire", "Le circuit d'alerte rejoint le rôle comptable désigné", "Contrôle interne Hympyr"),
    _control("REC-03", "Consultation du lisible et des données structurées", "Contenu complet et données accessibles", "DGFiP-Principes / BOFiP", critical=True),
    _control("REC-04", "Rapprochement facture, commande et livraison", "Piste d'audit et pièces justificatives accessibles", "Article 289 V CGI / contrôle interne Hympyr"),
    _control("REC-05", "Intégration dans l'ERP ou le logiciel comptable", "Aucune perte ou altération de données lors de l'import", "Contrôle interne Hympyr", critical=True),
    _control("REC-06", "Conservation du fichier dans son format informatique original", "L'original UBL, CII ou Factur-X est conservé ; un PDF de gestion ne le remplace pas", "BOFiP-Conservation", critical=True),
    _control("REC-07", "Authenticité, intégrité et lisibilité garanties", "Garanties maintenues de la réception à la fin de conservation", "Article 289 V CGI / BOFiP", critical=True),
    _control("CDV-200", "Statut 200 - Déposée", "Statut obligatoire observable et horodaté", "DGFiP-v3.2 §3.6.4", critical=True),
    _control("CDV-210", "Statut 210 - Refusée", "Scénario de refus intégral testé et motif tracé", "DGFiP-v3.2 §3.6.4", critical=True),
    _control("CDV-212", "Statut 212 - Encaissée", "Statut géré lorsqu'il est applicable aux opérations et à l'exigibilité de TVA", "DGFiP-v3.2 §3.6.4"),
    _control("CDV-213", "Statut 213 - Rejetée", "Rejet fonctionnel détecté, transmis et exploitable", "DGFiP-v3.2 §3.6.4", critical=True),
    _control("CDV-24H", "Transmission des statuts obligatoires sous 24 heures", "Preuve fournie par la plateforme pour les statuts applicables", "DGFiP-v3.2 §3.6.6"),
]

ANOMALY_CONTROLS = [
    _control("ANO-01", "Destinataire ou maille d'adressage erroné", "Erreur détectée sans intégration dans la mauvaise entité", "DGFiP-v3.2 §3.5 / contrôle interne Hympyr"),
    _control("ANO-02", "Fournisseur inconnu ou identité incohérente", "Facture mise en attente avant validation", "Article 289 V CGI / contrôle interne Hympyr"),
    _control("ANO-03", "Donnée obligatoire absente ou invalide", "Rejet ou traitement d'exception traçable", "DGFiP-v3.2 §3.6.7 / Annexe 7"),
    _control("ANO-04", "Montant, taux ou ventilation de TVA incohérent", "Blocage avant comptabilisation", "Annexe 1 v1.2 / contrôle interne Hympyr"),
    _control("ANO-05", "Facture en double", "Doublon détecté sans double comptabilisation", "DGFiP-v3.2 §3.6.7 - contrôle d'unicité"),
    _control("ANO-06", "Facture refusée ou rejetée", "Motif conservé et procédure d'annulation comptable connue", "DGFiP-v3.2 §3.6.4"),
    _control("ANO-07", "Plateforme ou ERP indisponible", "Procédure de continuité et reprise testée", "Contrôle interne Hympyr"),
    _control("ANO-08", "Écart entre données structurées et lisible", "Anomalie détectée, fichier non validé et incident escaladé", "Article 289 V CGI / contrôle interne Hympyr"),
]

EREPORTING_CONTROLS = [
    _control("ER-01", "Périmètre e-reporting qualifié", "B2C, opérations internationales et encaissements identifiés", "DGFiP-v3.2 §3.7.1", critical=True),
    _control("ER-02", "Données des opérations internationales", "Données de facture transmises lorsque l'opération entre dans le champ", "DGFiP-v3.2 §3.7.3"),
    _control("ER-03", "Données des opérations avec des non-assujettis", "Transactions B2C agrégées par jour, devise et type de transaction", "DGFiP-v3.2 §3.7.5"),
    _control("ER-04", "Données de paiement ou d'encaissement", "Date et montant transmis lorsque la TVA est exigible à l'encaissement", "DGFiP-v3.2 §3.7.4 et §3.7.6"),
    _control("ER-05", "Fréquence conforme au régime de TVA", "Périodes et échéances paramétrées selon le tableau 13, lorsque l'e-reporting est applicable", "DGFiP-v3.2 §3.7.7"),
    _control("ER-06", "Correction d'une période erronée", "Flux rectificatif annule et remplace les données antérieures", "DGFiP-v3.2 §3.7.7"),
    _control("ER-07", "Accusés de traitement et rejets exploitables", "Acceptation ou rejet de chaque objet métier traçable", "DGFiP-v3.2 §3.7.8 à §3.7.10"),
]

SECURITY_CONTROLS = [
    _control("SSI-01", "Comptes nominatifs et habilitations par rôle", "Accès limités au besoin d'en connaître", "Contrôle interne Hympyr"),
    _control("SSI-02", "MFA sur les comptes sensibles", "MFA activé pour administrateurs et utilisateurs à privilèges", "Contrôle interne Hympyr"),
    _control("SSI-03", "Revue périodique des droits", "Entrées, mobilités et sorties prises en compte", "Contrôle interne Hympyr"),
    _control("SSI-04", "Journalisation des opérations sensibles", "Dépôts, consultations, statuts, exports et actions d'administration traçables", "Contrôle interne Hympyr"),
    _control("SSI-05", "Procédure d'incident et contacts d'escalade", "Responsables, plateforme et éditeur joignables", "Contrôle interne Hympyr"),
    _control("SSI-06", "Continuité et reprise du traitement", "Mode dégradé, rattrapage et contrôle après reprise documentés", "Contrôle interne Hympyr"),
    _control("SSI-07", "Protection des exports et des preuves", "Emplacement sécurisé, accès maîtrisés et absence de données inutiles", "Contrôle interne Hympyr"),
]

ATTACHMENTS = [
    "Preuve de l'agrément de la plateforme", "Contrat ou mandat de la plateforme", "Capture de la ligne d'annuaire",
    "Facture test dans son format original", "Représentation lisible de la facture", "Rapport de validation du format ou des données",
    "Réception horodatée", "Historique du cycle de vie", "Preuve d'intégration comptable", "Preuve ou rapport d'e-reporting",
    "Matrice des habilitations", "Ticket d'incident", "Preuve d'archivage du format original", "Plan d'actions correctives",
]

CONTROL_GROUPS = {
    "platform_controls": PLATFORM_CONTROLS,
    "format_data_controls": FORMAT_DATA_CONTROLS,
    "reception_controls": RECEPTION_CONTROLS,
    "anomaly_controls": ANOMALY_CONTROLS,
    "ereporting_controls": EREPORTING_CONTROLS,
    "security_controls": SECURITY_CONTROLS,
}


def default_payload() -> dict[str, Any]:
    today = date.today().isoformat()
    payload: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "reference_version": REFERENCE_VERSION,
        "metadata": {
            "societe": "Hympyr Énergies", "siren": "", "siret": "", "date_controle": today,
            "controleur": "Michael ROSA", "responsable_comptable": "", "logiciel": "",
            "environnement": "Production", "reference_facture": "", "statut_controle": "À réaliser",
        },
        "profile": {
            "taille_entreprise": "À déterminer", "regime_tva": "À déterminer", "b2b_france": "À déterminer",
            "b2c": "À déterminer", "international": "À déterminer", "prestations_encaissements": "À déterminer",
            "option_tva_debits": "À déterminer",
        },
        "platform": {
            "nom": "", "agrement_verifie": "À déterminer", "date_verification": today, "preuve_agrement": "",
            "annuaire_verifie": "À déterminer", "maille_adressage": "SIREN", "code_routage": "", "preuve_annuaire": "",
        },
        "proofs": [{"reference": f"P-{index:02d}", "description": "", "emplacement": ""} for index in range(1, 7)],
        "gaps": [{"numero": "01", "controle_id": "", "ecart": "", "risque": "Moyen", "action": "", "responsable": "", "echeance": ""}],
        "conclusion": {"resultat_general": "Non conclu", "commentaires": "", "prochain_controle": "", "controleur_signature": "Quentin Debrie", "responsable_validation": ""},
        "attachments": [],
    }
    for key, rows in CONTROL_GROUPS.items():
        payload[key] = deepcopy(rows)
    return payload


def _normalise_result(value: Any) -> str:
    mapping = {"Oui": "Conforme", "OK": "Conforme", "Non": "Non conforme", "KO": "Non conforme", "Non testé": "Non contrôlé", "Non contrôlé": "Non contrôlé", "N/A": "N/A"}
    return mapping.get(str(value), str(value) if str(value) in RESULT_OPTIONS else "Non contrôlé")


def _merge_controls(default_rows: list[dict[str, Any]], incoming: Any) -> list[dict[str, Any]]:
    if not isinstance(incoming, list):
        return deepcopy(default_rows)
    by_id = {str(row.get("id")): row for row in incoming if isinstance(row, dict)}
    merged = []
    for default in default_rows:
        row = deepcopy(default)
        candidate = by_id.get(default["id"])
        if candidate:
            row["resultat"] = _normalise_result(candidate.get("resultat"))
            row["preuve"] = str(candidate.get("preuve", ""))
        merged.append(row)
    return merged


def normalize_payload(value: Any) -> dict[str, Any]:
    """Normalise un brouillon et migre les données communes des versions antérieures."""
    defaults = default_payload()
    if not isinstance(value, dict):
        return defaults
    result = deepcopy(defaults)
    for section in ("metadata", "profile", "platform", "conclusion"):
        if isinstance(value.get(section), dict):
            result[section].update(value[section])

    old_identifier = str(value.get("metadata", {}).get("siret", ""))
    digits = "".join(character for character in old_identifier if character.isdigit())
    if not result["metadata"].get("siren") and len(digits) in (9, 14):
        result["metadata"]["siren"] = digits[:9]
    if len(digits) == 14:
        result["metadata"]["siret"] = digits

    for key, default_rows in CONTROL_GROUPS.items():
        result[key] = _merge_controls(default_rows, value.get(key))
    for key in ("proofs", "gaps"):
        if isinstance(value.get(key), list):
            result[key] = [dict(row) for row in value[key] if isinstance(row, dict)]
    if isinstance(value.get("attachments"), list):
        result["attachments"] = [item for item in value["attachments"] if item in ATTACHMENTS]
    result["schema_version"] = SCHEMA_VERSION
    result["reference_version"] = REFERENCE_VERSION
    return result


def all_controls(payload: dict[str, Any]) -> Iterable[dict[str, Any]]:
    for key in CONTROL_GROUPS:
        yield from payload.get(key, [])


def _group_score(rows: list[dict[str, Any]]) -> int:
    return round(100 * sum(row.get("resultat") != "Non contrôlé" for row in rows) / len(rows)) if rows else 0


def regulatory_scope(payload: dict[str, Any]) -> dict[str, str]:
    profile = payload.get("profile", {})
    size = profile.get("taille_entreprise", "À déterminer")
    if size in ("Grande entreprise (GE)", "Entreprise de taille intermédiaire (ETI)"):
        emission = "1er septembre 2026"
    elif size in ("Petite ou moyenne entreprise (PME)", "Micro-entreprise"):
        emission = "1er septembre 2027"
    else:
        emission = "À déterminer selon la taille"

    transaction_scope = []
    if profile.get("b2c") == "Oui":
        transaction_scope.append("opérations avec des non-assujettis")
    if profile.get("international") == "Oui":
        transaction_scope.append("opérations internationales")
    if transaction_scope:
        e_reporting = ", ".join(transaction_scope)
    elif profile.get("b2c") == profile.get("international") == "Non":
        e_reporting = "Aucun périmètre déclaré"
    else:
        e_reporting = "À déterminer"

    if profile.get("prestations_encaissements") == "Oui" and profile.get("option_tva_debits") != "Oui":
        payment = "Applicable à qualifier"
    elif profile.get("prestations_encaissements") == "Non" or profile.get("option_tva_debits") == "Oui":
        payment = "A priori non applicable"
    else:
        payment = "À déterminer"
    return {"reception": "1er septembre 2026 - toutes les entreprises", "emission": emission, "ereporting_transactions": e_reporting, "ereporting_paiements": payment}


def section_scores(payload: dict[str, Any]) -> dict[str, int]:
    meta = payload.get("metadata", {})
    profile = payload.get("profile", {})
    profile_values = [
        meta.get("societe"), meta.get("siren"), meta.get("date_controle"), meta.get("controleur"), meta.get("responsable_comptable"),
        meta.get("logiciel"), meta.get("reference_facture"), profile.get("taille_entreprise") not in ("", "À déterminer"), profile.get("regime_tva") not in ("", "À déterminer"),
    ]
    profil = round(100 * sum(bool(value) for value in profile_values) / len(profile_values))
    gap_rows = [row for row in payload.get("gaps", []) if str(row.get("ecart", "")).strip()]
    if not gap_rows:
        gaps = 100
    else:
        fields = ("controle_id", "ecart", "risque", "action", "responsable", "echeance")
        gaps = round(100 * sum(bool(str(row.get(field, "")).strip()) for row in gap_rows for field in fields) / (len(gap_rows) * len(fields)))
    conclusion = payload.get("conclusion", {})
    validation_values = [conclusion.get("resultat_general") not in ("", "Non conclu"), bool(str(conclusion.get("controleur_signature", "")).strip()), bool(str(conclusion.get("responsable_validation", "")).strip())]
    return {
        "profil": profil,
        "plateforme": _group_score(payload.get("platform_controls", [])),
        "formats": _group_score(payload.get("format_data_controls", [])),
        "reception": round((_group_score(payload.get("reception_controls", [])) + _group_score(payload.get("anomaly_controls", []))) / 2),
        "ereporting": _group_score(payload.get("ereporting_controls", [])),
        "ssi": _group_score(payload.get("security_controls", [])),
        "ecarts": gaps,
        "validation": round(100 * sum(validation_values) / len(validation_values)),
    }


def overall_progress(payload: dict[str, Any]) -> int:
    scores = section_scores(payload)
    weights = {"profil": 0.14, "plateforme": 0.14, "formats": 0.18, "reception": 0.18, "ereporting": 0.11, "ssi": 0.09, "ecarts": 0.07, "validation": 0.09}
    return round(sum(scores[key] * weights[key] for key in weights))


def validation_issues(payload: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    meta = payload.get("metadata", {})
    required_meta = {"societe": "société", "siren": "SIREN", "date_controle": "date du contrôle", "controleur": "contrôleur", "responsable_comptable": "responsable comptable", "logiciel": "logiciel comptable / ERP", "reference_facture": "facture test"}
    missing = [label for key, label in required_meta.items() if not str(meta.get(key, "")).strip()]
    if missing:
        issues.append("Profil incomplet : " + ", ".join(missing) + ".")
    siren = "".join(character for character in str(meta.get("siren", "")) if character.isdigit())
    siret = "".join(character for character in str(meta.get("siret", "")) if character.isdigit())
    if siren and len(siren) != 9:
        issues.append("Le SIREN doit contenir exactement 9 chiffres.")
    if siret and len(siret) != 14:
        issues.append("Le SIRET, lorsqu'il est renseigné, doit contenir exactement 14 chiffres.")

    profile = payload.get("profile", {})
    profile_fields = {"taille_entreprise": "taille de l'entreprise", "regime_tva": "régime de TVA", "b2b_france": "opérations B2B France", "b2c": "opérations B2C", "international": "opérations internationales", "prestations_encaissements": "prestations à TVA sur encaissements", "option_tva_debits": "option TVA sur les débits"}
    unknown = [label for key, label in profile_fields.items() if profile.get(key) in (None, "", "À déterminer")]
    if unknown:
        issues.append("Périmètre fiscal à qualifier : " + ", ".join(unknown) + ".")

    platform = payload.get("platform", {})
    if not str(platform.get("nom", "")).strip():
        issues.append("Le nom de la plateforme agréée n'est pas renseigné.")
    if platform.get("agrement_verifie") != "Oui" or not str(platform.get("preuve_agrement", "")).strip():
        issues.append("L'agrément définitif de la plateforme doit être vérifié, daté et justifié par une preuve.")
    if platform.get("annuaire_verifie") != "Oui" or not str(platform.get("preuve_annuaire", "")).strip():
        issues.append("La ligne d'annuaire active et sa maille d'adressage doivent être vérifiées et prouvées.")

    unchecked = [row["id"] for row in all_controls(payload) if row.get("resultat") == "Non contrôlé"]
    if unchecked:
        issues.append(f"{len(unchecked)} contrôles restent non renseignés : " + ", ".join(unchecked[:10]) + ("…" if len(unchecked) > 10 else "") + ".")
    undocumented = [row["id"] for row in all_controls(payload) if row.get("resultat") != "Non contrôlé" and not str(row.get("preuve", "")).strip()]
    if undocumented:
        issues.append(f"{len(undocumented)} résultats ne disposent pas d'une preuve ou justification : " + ", ".join(undocumented[:10]) + ("…" if len(undocumented) > 10 else "") + ".")
    invalid_na = [row["id"] for row in all_controls(payload) if row.get("critique") and row.get("resultat") == "N/A"]
    if invalid_na:
        issues.append("Les contrôles critiques suivants ne peuvent pas être classés N/A sans réexamen du périmètre : " + ", ".join(invalid_na) + ".")

    controls_by_id = {row["id"]: row for row in all_controls(payload)}
    conditional_na = []
    if profile.get("international") == "Oui" and controls_by_id.get("ER-02", {}).get("resultat") == "N/A":
        conditional_na.append("ER-02")
    if profile.get("b2c") == "Oui" and controls_by_id.get("ER-03", {}).get("resultat") == "N/A":
        conditional_na.append("ER-03")
    payment_applicable = profile.get("prestations_encaissements") == "Oui" and profile.get("option_tva_debits") != "Oui"
    if payment_applicable and controls_by_id.get("ER-04", {}).get("resultat") == "N/A":
        conditional_na.append("ER-04")
    if (profile.get("international") == "Oui" or profile.get("b2c") == "Oui" or payment_applicable) and controls_by_id.get("ER-05", {}).get("resultat") == "N/A":
        conditional_na.append("ER-05")
    if conditional_na:
        issues.append("Ces contrôles e-reporting sont applicables au profil déclaré et ne peuvent pas être N/A : " + ", ".join(conditional_na) + ".")

    nonconforming = [row["id"] for row in all_controls(payload) if row.get("resultat") == "Non conforme"]
    gap_ids = {str(row.get("controle_id", "")).strip() for row in payload.get("gaps", []) if str(row.get("ecart", "")).strip()}
    missing_gaps = [identifier for identifier in nonconforming if identifier not in gap_ids]
    if missing_gaps:
        issues.append("Un écart et une action doivent être créés pour : " + ", ".join(missing_gaps) + ".")
    incomplete_gaps = []
    for row in payload.get("gaps", []):
        if str(row.get("ecart", "")).strip() and not all(str(row.get(key, "")).strip() for key in ("controle_id", "action", "responsable", "echeance")):
            incomplete_gaps.append(str(row.get("numero", "?")))
    if incomplete_gaps:
        issues.append("Actions correctives incomplètes pour les écarts : " + ", ".join(incomplete_gaps) + ".")

    required_attachments = {
        "Preuve de l'agrément de la plateforme", "Capture de la ligne d'annuaire",
        "Facture test dans son format original", "Réception horodatée",
        "Historique du cycle de vie", "Preuve d'intégration comptable",
        "Preuve d'archivage du format original",
    }
    if profile.get("international") == "Oui" or profile.get("b2c") == "Oui" or payment_applicable:
        required_attachments.add("Preuve ou rapport d'e-reporting")
    missing_attachments = sorted(required_attachments - set(payload.get("attachments", [])))
    if missing_attachments:
        issues.append("Pièces justificatives minimales absentes : " + ", ".join(missing_attachments) + ".")

    conclusion = payload.get("conclusion", {})
    result = conclusion.get("resultat_general")
    if result in ("", "Non conclu"):
        issues.append("La conclusion générale n'est pas renseignée.")
    if result == "Prêt - alignement démontré" and nonconforming:
        issues.append("La conclusion « Prêt - alignement démontré » est incompatible avec un contrôle non conforme.")
    if not str(conclusion.get("responsable_validation", "")).strip():
        issues.append("Le responsable de validation n'est pas renseigné.")
    return issues
