from pathlib import Path

from streamlit.testing.v1 import AppTest


def test_hub_navigation_and_draft_generation_work():
    app_path = Path(__file__).resolve().parents[1] / "app.py"
    app = AppTest.from_file(app_path).run(timeout=30)
    assert not app.exception

    open_profile = next(button for button in app.button if button.label == "Ouvrir profil et périmètre")
    open_profile.click().run(timeout=30)
    assert not app.exception
    assert any(field.label == "SIREN" for field in app.text_input)

    app.radio[0].set_value("Validation").run(timeout=30)
    assert not app.exception
    generate = next(button for button in app.button if button.label == "Générer le rapport PDF Hympyr")
    generate.click().run(timeout=45)

    assert not app.exception
    assert any("Rapport PDF généré" in message.value for message in app.success)
    assert any(button.label == "Télécharger le rapport PDF" for button in app.get("download_button"))


def test_all_daf_steps_render_without_exception():
    app_path = Path(__file__).resolve().parents[1] / "app.py"
    app = AppTest.from_file(app_path).run(timeout=30)
    for page in ["Profil", "Plateforme", "Formats", "Réception", "E-reporting", "SSI", "Écarts", "Validation"]:
        app.radio[0].set_value(page).run(timeout=45)
        assert not app.exception, page
