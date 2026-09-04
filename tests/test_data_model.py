from data_model import (
    CONTROL_GROUPS,
    REFERENCE_VERSION,
    all_controls,
    default_payload,
    normalize_payload,
    overall_progress,
    regulatory_scope,
    section_scores,
    validation_issues,
)


def completed_payload():
    payload = default_payload()
    payload["metadata"].update({
        "siren": "123456789", "siret": "12345678900012", "responsable_comptable": "Marie Dupont",
        "logiciel": "ERP de test", "reference_facture": "TEST-001", "statut_controle": "Prêt",
    })
    payload["profile"].update({
        "taille_entreprise": "Petite ou moyenne entreprise (PME)", "regime_tva": "Réel normal mensuel",
        "b2b_france": "Oui", "b2c": "Non", "international": "Non",
        "prestations_encaissements": "Non", "option_tva_debits": "Non",
    })
    payload["platform"].update({
        "nom": "Plateforme agréée de démonstration", "agrement_verifie": "Oui", "preuve_agrement": "P-01",
        "annuaire_verifie": "Oui", "preuve_annuaire": "P-02",
    })
    for row in all_controls(payload):
        row["resultat"] = "Conforme"
        row["preuve"] = "Preuve disponible"
    payload["gaps"] = []
    payload["attachments"] = [
        "Preuve de l'agrément de la plateforme", "Capture de la ligne d'annuaire",
        "Facture test dans son format original", "Réception horodatée", "Historique du cycle de vie",
        "Preuve d'intégration comptable", "Preuve d'archivage du format original",
    ]
    payload["conclusion"].update({"resultat_general": "Prêt - alignement démontré", "responsable_validation": "Direction financière"})
    return payload


def test_default_payload_contains_versioned_referential():
    payload = default_payload()
    assert payload["schema_version"] == 2
    assert payload["reference_version"] == REFERENCE_VERSION
    assert len(CONTROL_GROUPS) == 6
    assert {"CDV-200", "CDV-210", "CDV-212", "CDV-213"}.issubset({row["id"] for row in all_controls(payload)})
    assert 0 <= overall_progress(payload) <= 100
    assert validation_issues(payload)


def test_normalize_payload_migrates_old_combined_identifier():
    normalized = normalize_payload({"metadata": {"siret": "123 456 789 00012"}})
    assert normalized["metadata"]["siren"] == "123456789"
    assert normalized["metadata"]["siret"] == "12345678900012"
    assert len(normalized["format_data_controls"]) == len(CONTROL_GROUPS["format_data_controls"])


def test_complete_payload_reaches_full_progress():
    payload = completed_payload()
    assert all(value == 100 for value in section_scores(payload).values())
    assert overall_progress(payload) == 100
    assert validation_issues(payload) == []


def test_nonconformity_requires_linked_gap_and_consistent_conclusion():
    payload = completed_payload()
    payload["format_data_controls"][0]["resultat"] = "Non conforme"
    issues = validation_issues(payload)
    assert any("Un écart" in issue for issue in issues)
    assert any("incompatible" in issue for issue in issues)


def test_identifiers_are_checked_separately():
    payload = completed_payload()
    payload["metadata"]["siren"] = "123"
    payload["metadata"]["siret"] = "1234"
    issues = validation_issues(payload)
    assert any("SIREN doit contenir exactement 9" in issue for issue in issues)
    assert any("SIRET" in issue and "14" in issue for issue in issues)


def test_regulatory_schedule_depends_on_company_size():
    payload = default_payload()
    payload["profile"]["taille_entreprise"] = "Entreprise de taille intermédiaire (ETI)"
    assert regulatory_scope(payload)["emission"] == "1er septembre 2026"
    payload["profile"]["taille_entreprise"] = "Petite ou moyenne entreprise (PME)"
    assert regulatory_scope(payload)["emission"] == "1er septembre 2027"
