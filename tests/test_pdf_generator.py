from io import BytesIO
from pathlib import Path

from pypdf import PdfReader

from data_model import all_controls, default_payload
from pdf_generator import generate_pdf


ROOT = Path(__file__).resolve().parents[1]


def populated_payload():
    payload = default_payload()
    payload["metadata"].update({
        "siren": "123456789", "siret": "12345678900012", "responsable_comptable": "Marie Dupont",
        "logiciel": "ERP Finance", "reference_facture": "TEST-2026-001", "statut_controle": "Prêt",
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
    payload["conclusion"].update({
        "resultat_general": "Prêt - alignement démontré", "commentaires": "Contrôles réalisés avec les preuves référencées.",
        "responsable_validation": "Direction financière",
    })
    payload["attachments"] = [
        "Preuve de l'agrément de la plateforme", "Capture de la ligne d'annuaire",
        "Facture test dans son format original", "Réception horodatée", "Historique du cycle de vie",
        "Preuve d'intégration comptable", "Preuve d'archivage du format original",
    ]
    return payload


def test_generate_pdf_is_valid_and_contains_regulatory_traceability():
    result = generate_pdf(populated_payload(), ROOT / "assets" / "gabarit_factu_elec.pdf")
    assert result.startswith(b"%PDF")
    reader = PdfReader(BytesIO(result))
    assert len(reader.pages) >= 8
    text = "\n".join(page.extract_text() or "" for page in reader.pages)
    assert "TEST-2026-001" in text
    assert "Direction financière" in text
    assert "Prêt - alignement démontré" in text
    assert "DGFiP-v3.2" in text
    assert "CDV-213" in text
    for page in reader.pages:
        assert round(float(page.mediabox.width), 1) == 595.4
        assert round(float(page.mediabox.height), 1) == 841.9


def test_draft_pdf_has_badge():
    result = generate_pdf(default_payload(), ROOT / "assets" / "gabarit_factu_elec.pdf", draft=True)
    text = "\n".join(page.extract_text() or "" for page in PdfReader(BytesIO(result)).pages)
    assert "BROUILLON" in text
