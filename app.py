"""Application Streamlit Hympyr - préparation à la facturation électronique."""

from __future__ import annotations

from datetime import date
import hashlib
import json
import logging
from pathlib import Path

import pandas as pd
import streamlit as st

from data_model import (
    ATTACHMENTS,
    OFFICIAL_SOURCES,
    REFERENCE_VERSION,
    RESULT_OPTIONS,
    all_controls,
    default_payload,
    normalize_payload,
    overall_progress,
    regulatory_scope,
    section_scores,
    validation_issues,
)
from pdf_generator import generate_pdf


APP_DIR = Path(__file__).resolve().parent
TEMPLATE_PATH = APP_DIR / "assets" / "gabarit_factu_elec.pdf"
LOGGER = logging.getLogger(__name__)

NAV_ITEMS = [
    ("Hub", "Vue d'ensemble"),
    ("Profil", "1. Profil et périmètre"),
    ("Plateforme", "2. Plateforme et annuaire"),
    ("Formats", "3. Formats et données"),
    ("Réception", "4. Réception et cycle de vie"),
    ("E-reporting", "5. E-reporting"),
    ("SSI", "6. Sécurité et exploitation"),
    ("Écarts", "7. Écarts et actions"),
    ("Validation", "8. Synthèse et PDF"),
]
NAV_LABELS = [label for label, _ in NAV_ITEMS]
NAV_DISPLAY = dict(NAV_ITEMS)
STEP_ORDER = NAV_LABELS[1:]


st.set_page_config(page_title="Hympyr | Préparation facturation électronique", page_icon="✅", layout="wide", initial_sidebar_state="expanded")

st.markdown(
    """
<style>
    :root { --green:#0c9d67; --dark:#004b36; --pale:#e8f5f0; --ink:#122e26; --muted:#64736e; --line:#d9e4df; }
    .stApp { background:#f6f8f7; color:var(--ink); }
    [data-testid="stSidebar"] { background:#fff; border-right:1px solid var(--line); }
    [data-testid="stSidebar"] .stRadio label { font-weight:600; }
    .block-container { padding-top:1.35rem; padding-bottom:4rem; max-width:1480px; }
    h1,h2,h3 { color:var(--dark); letter-spacing:-.02em; }
    .brand-shell { background:linear-gradient(120deg,#003f2f 0%,#076a4c 58%,#0c9d67 100%); border-radius:20px; padding:1.35rem 1.6rem; color:white; box-shadow:0 14px 32px rgba(0,75,54,.13); margin-bottom:1.15rem; }
    .brand-kicker { font-size:.72rem; font-weight:800; letter-spacing:.12em; opacity:.82; }
    .brand-title { font-size:1.7rem; font-weight:800; margin-top:.25rem; }
    .brand-subtitle { font-size:.92rem; opacity:.9; margin-top:.2rem; }
    .reference-pill { display:inline-block; margin-top:.7rem; padding:.25rem .55rem; border:1px solid rgba(255,255,255,.35); border-radius:999px; font-size:.7rem; }
    .step-banner { display:flex; align-items:center; gap:.75rem; margin:.15rem 0 1.1rem; }
    .step-chip { background:var(--pale); color:var(--dark); border:1px solid #c9e6da; padding:.32rem .66rem; border-radius:999px; font-size:.78rem; font-weight:800; white-space:nowrap; }
    .metric-card,.hub-card { background:white; border:1px solid var(--line); border-radius:15px; padding:1rem 1.05rem; box-shadow:0 7px 18px rgba(0,75,54,.045); }
    .metric-value { color:var(--dark); font-size:1.55rem; font-weight:800; }
    .metric-label { color:var(--muted); font-size:.76rem; margin-top:.15rem; }
    .scope-value { color:var(--dark); font-size:.98rem; font-weight:800; line-height:1.25; margin-top:.35rem; }
    .hub-card { min-height:142px; margin-bottom:.5rem; }
    .hub-index { color:var(--green); font-size:.74rem; font-weight:800; }
    .hub-title { color:var(--dark); font-size:1rem; font-weight:800; margin:.25rem 0 .35rem; }
    .hub-copy { color:var(--muted); font-size:.81rem; line-height:1.35; }
    .status-good { color:#08784f; font-weight:800; }
    .status-warn { color:#9a5b00; font-weight:800; }
    .small-note { color:var(--muted); font-size:.78rem; }
    div[data-testid="stDataEditor"] { border:1px solid var(--line); border-radius:12px; overflow:hidden; }
    .stButton>button,.stDownloadButton>button { border-radius:10px; min-height:2.55rem; font-weight:700; }
    .stButton>button[kind="primary"],.stDownloadButton>button[kind="primary"] { background:var(--green); border-color:var(--green); }
    footer { visibility:hidden; }
</style>
""",
    unsafe_allow_html=True,
)


def clear_editor_state() -> None:
    for key in list(st.session_state):
        if key.startswith("editor_"):
            del st.session_state[key]


def init_state() -> None:
    if "control_data" not in st.session_state:
        st.session_state.control_data = default_payload()
    if "current_page" not in st.session_state or st.session_state.current_page not in NAV_LABELS:
        st.session_state.current_page = "Hub"
    if "nav_override" in st.session_state:
        st.session_state.nav_selector = st.session_state.pop("nav_override")
    st.session_state.setdefault("generated_pdf", None)
    st.session_state.setdefault("generated_name", "Rapport_preparation_facturation_electronique_Hympyr.pdf")
    st.session_state.setdefault("generated_fingerprint", None)


def option_index(options: list[str], value: str) -> int:
    return options.index(value) if value in options else 0


def go_to(label: str) -> None:
    st.session_state.current_page = label
    st.session_state.nav_override = label
    st.rerun()


def sync_sidebar_navigation() -> None:
    st.session_state.current_page = st.session_state.nav_selector


def parse_date(value: str | None) -> date:
    try:
        return date.fromisoformat((value or "")[:10])
    except ValueError:
        return date.today()


def rows_from_editor(frame: pd.DataFrame) -> list[dict]:
    return frame.where(pd.notnull(frame), None).to_dict(orient="records")


def data_fingerprint(data: dict) -> str:
    payload = json.dumps(data, ensure_ascii=False, sort_keys=True, default=str).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def render_header() -> None:
    st.markdown(
        f"""
        <div class="brand-shell">
            <div class="brand-kicker">HYMPYR ÉNERGIES · DAF · CONFORMITÉ & SÉCURITÉ SI</div>
            <div class="brand-title">Préparation à la facturation électronique</div>
            <div class="brand-subtitle">Qualifier le périmètre, éprouver les flux et constituer un dossier de preuves vérifiable.</div>
            <div class="reference-pill">Référentiel : {REFERENCE_VERSION}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_step_header(index: int, title: str, copy: str) -> None:
    st.markdown(
        f'<div class="step-banner"><span class="step-chip">ÉTAPE {index} / {len(STEP_ORDER)}</span>'
        f'<div><h2 style="margin:0">{title}</h2><div class="small-note">{copy}</div></div></div>',
        unsafe_allow_html=True,
    )


def render_bottom_navigation(current: str) -> None:
    idx = STEP_ORDER.index(current)
    st.divider()
    left, middle, right = st.columns([1, 3, 1])
    with left:
        target = "Hub" if idx == 0 else STEP_ORDER[idx - 1]
        if st.button("← Précédent", use_container_width=True, key=f"back_{current}"):
            go_to(target)
    with middle:
        st.markdown(f'<div style="text-align:center;color:#64736e;padding:.72rem">Étape {idx + 1} sur {len(STEP_ORDER)}</div>', unsafe_allow_html=True)
    with right:
        target = "Hub" if idx == len(STEP_ORDER) - 1 else STEP_ORDER[idx + 1]
        label = "Retour au hub" if target == "Hub" else "Suivant →"
        if st.button(label, type="primary", use_container_width=True, key=f"next_{current}"):
            go_to(target)


def render_sidebar(data: dict) -> None:
    with st.sidebar:
        st.markdown("### Hympyr Énergies")
        progress = overall_progress(data)
        st.caption("Avancement documentaire")
        st.progress(progress / 100)
        st.markdown(f"**{progress} % complété**")
        st.radio("Navigation", NAV_LABELS, index=NAV_LABELS.index(st.session_state.current_page), format_func=lambda value: NAV_DISPLAY[value], key="nav_selector", on_change=sync_sidebar_navigation)

        st.divider()
        with st.expander("Référentiel officiel", expanded=False):
            st.caption(REFERENCE_VERSION)
            for source in OFFICIAL_SOURCES:
                st.markdown(f"[{source['id']}]({source['url']})")

        with st.expander("Brouillon et reprise", expanded=False):
            draft = json.dumps(data, ensure_ascii=False, indent=2, default=str).encode("utf-8")
            st.download_button("Télécharger le brouillon JSON", draft, file_name="controle_facturation_hympyr_v2.json", mime="application/json", use_container_width=True)
            uploaded = st.file_uploader("Importer un brouillon JSON", type=["json"], label_visibility="collapsed")
            if st.button("Importer", use_container_width=True, disabled=uploaded is None):
                try:
                    st.session_state.control_data = normalize_payload(json.loads(uploaded.getvalue().decode("utf-8")))
                    st.session_state.generated_pdf = None
                    st.session_state.generated_fingerprint = None
                    clear_editor_state()
                    st.success("Brouillon importé et normalisé sur le schéma actuel.")
                    st.rerun()
                except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                    st.error(f"Fichier JSON invalide : {exc}")

        with st.expander("Nouveau contrôle", expanded=False):
            st.caption("Cette action efface les données de la session en cours.")
            if st.button("Réinitialiser la fiche", use_container_width=True):
                st.session_state.confirm_reset = True
            if st.session_state.get("confirm_reset"):
                st.warning("Confirmer la réinitialisation ?")
                yes, no = st.columns(2)
                if yes.button("Confirmer", type="primary", use_container_width=True):
                    st.session_state.control_data = default_payload()
                    st.session_state.generated_pdf = None
                    st.session_state.generated_fingerprint = None
                    st.session_state.confirm_reset = False
                    clear_editor_state()
                    st.rerun()
                if no.button("Annuler", use_container_width=True):
                    st.session_state.confirm_reset = False
                    st.rerun()

        st.divider()
        st.caption("Les données restent dans la session. Exportez le JSON pour reprendre le contrôle et archivez les preuves dans l'emplacement sécurisé prévu par Hympyr.")


def render_control_editor(data: dict, section_key: str, editor_key: str) -> None:
    frame = pd.DataFrame(data[section_key])
    edited = st.data_editor(
        frame,
        column_order=["id", "controle", "attendu", "source", "resultat", "preuve"],
        column_config={
            "id": st.column_config.TextColumn("ID", width="small"),
            "controle": st.column_config.TextColumn("Contrôle", width="large"),
            "attendu": st.column_config.TextColumn("Attendu", width="large"),
            "source": st.column_config.TextColumn("Source", width="medium"),
            "resultat": st.column_config.SelectboxColumn("Résultat", options=RESULT_OPTIONS, required=True, width="medium"),
            "preuve": st.column_config.TextColumn("Preuve ou justification", width="large"),
        },
        disabled=["id", "controle", "attendu", "source"],
        hide_index=True,
        use_container_width=True,
        height=min(680, 38 + 35 * (len(frame) + 1)),
        key=editor_key,
    )
    data[section_key] = rows_from_editor(edited)
    st.caption("Une preuve est exigée pour chaque résultat. N/A doit être justifié ; les contrôles critiques ne doivent pas être neutralisés par défaut.")


def render_hub(data: dict) -> None:
    scores = section_scores(data)
    progress = overall_progress(data)
    controls = list(all_controls(data))
    nonconforming = sum(row.get("resultat") == "Non conforme" for row in controls)
    unchecked = sum(row.get("resultat") == "Non contrôlé" for row in controls)
    issues = validation_issues(data)

    st.markdown("## Vue d'ensemble")
    st.caption("Le score mesure la complétude documentaire, pas une certification délivrée par la DGFiP.")
    cols = st.columns(4)
    metrics = [(f"{progress} %", "Avancement"), (str(unchecked), "Contrôles à réaliser"), (str(nonconforming), "Non-conformités"), (str(len(issues)), "Points bloquants")]
    for col, (value, label) in zip(cols, metrics):
        with col:
            st.markdown(f'<div class="metric-card"><div class="metric-value">{value}</div><div class="metric-label">{label}</div></div>', unsafe_allow_html=True)

    st.info("Le rapport produit documente la préparation et les contrôles réalisés. Il ne transforme pas un PDF ordinaire en facture électronique et ne remplace ni la plateforme agréée ni un avis juridique.")
    cards = [
        ("Profil", "01", "Profil et périmètre", "Déterminer les échéances et les volets applicables.", scores["profil"]),
        ("Plateforme", "02", "Plateforme et annuaire", "Vérifier l'agrément, l'adressage et le routage.", scores["plateforme"]),
        ("Formats", "03", "Formats et données", "Contrôler le structuré, le lisible et les mentions.", scores["formats"]),
        ("Réception", "04", "Réception et cycle de vie", "Éprouver le flux nominal, les statuts et les anomalies.", scores["reception"]),
        ("E-reporting", "05", "E-reporting", "Qualifier transactions, paiements et périodicité.", scores["ereporting"]),
        ("SSI", "06", "Sécurité et exploitation", "Sécuriser accès, preuves, incidents et continuité.", scores["ssi"]),
        ("Écarts", "07", "Écarts et actions", "Relier chaque non-conformité à une action pilotée.", scores["ecarts"]),
        ("Validation", "08", "Synthèse et PDF", "Valider le dossier et générer le rapport Hympyr.", scores["validation"]),
    ]
    for start in range(0, len(cards), 4):
        columns = st.columns(4)
        for col, (key, number, title, copy, score) in zip(columns, cards[start:start + 4]):
            with col:
                css = "status-good" if score == 100 else "status-warn"
                st.markdown(f'<div class="hub-card"><div class="hub-index">ÉTAPE {number}</div><div class="hub-title">{title}</div><div class="hub-copy">{copy}</div><div class="{css}" style="margin-top:.65rem">{"Complet" if score == 100 else f"{score} %"}</div></div>', unsafe_allow_html=True)
                if st.button(f"Ouvrir {title.lower()}", use_container_width=True, key=f"open_{key}"):
                    go_to(key)

    if issues:
        with st.expander(f"{len(issues)} point(s) bloquant(s) avant un rapport final", expanded=False):
            for issue in issues:
                st.write(f"- {issue}")
    else:
        st.success("Le dossier est complet et cohérent pour produire un rapport final de préparation.")


def render_profile(data: dict) -> None:
    render_step_header(1, "Profil et périmètre fiscal", "Les échéances dépendent de la taille ; l'e-reporting dépend des clients, opérations et règles d'exigibilité de TVA.")
    meta, profile = data["metadata"], data["profile"]
    left, right = st.columns(2)
    with left:
        st.markdown("#### Entité et contrôle")
        meta["societe"] = st.text_input("Société contrôlée", value=meta.get("societe", ""))
        c1, c2 = st.columns(2)
        meta["siren"] = c1.text_input("SIREN", value=meta.get("siren", ""), placeholder="9 chiffres")
        meta["siret"] = c2.text_input("SIRET contrôlé, si pertinent", value=meta.get("siret", ""), placeholder="14 chiffres")
        meta["date_controle"] = st.date_input("Date du contrôle", value=parse_date(meta.get("date_controle")), format="DD/MM/YYYY").isoformat()
        meta["controleur"] = st.text_input("Contrôle réalisé par", value=meta.get("controleur", ""))
        meta["responsable_comptable"] = st.text_input("Responsable comptable", value=meta.get("responsable_comptable", ""))
        meta["logiciel"] = st.text_input("Logiciel comptable / ERP", value=meta.get("logiciel", ""))
        meta["reference_facture"] = st.text_input("Référence de la facture test", value=meta.get("reference_facture", ""))
    with right:
        st.markdown("#### Qualification réglementaire")
        sizes = ["À déterminer", "Grande entreprise (GE)", "Entreprise de taille intermédiaire (ETI)", "Petite ou moyenne entreprise (PME)", "Micro-entreprise"]
        regimes = ["À déterminer", "Réel normal mensuel", "Réel normal trimestriel", "Régime simplifié", "Franchise en base de TVA"]
        yes_no = ["À déterminer", "Oui", "Non"]
        profile["taille_entreprise"] = st.selectbox("Taille de l'entreprise", sizes, index=option_index(sizes, profile.get("taille_entreprise", "")))
        profile["regime_tva"] = st.selectbox("Régime de TVA", regimes, index=option_index(regimes, profile.get("regime_tva", "")))
        profile["b2b_france"] = st.selectbox("Opérations B2B entre assujettis établis en France", yes_no, index=option_index(yes_no, profile.get("b2b_france", "")))
        profile["b2c"] = st.selectbox("Opérations avec particuliers ou non-assujettis", yes_no, index=option_index(yes_no, profile.get("b2c", "")))
        profile["international"] = st.selectbox("Opérations avec des entreprises non établies en France", yes_no, index=option_index(yes_no, profile.get("international", "")))
        profile["prestations_encaissements"] = st.selectbox("Prestations avec TVA exigible à l'encaissement", yes_no, index=option_index(yes_no, profile.get("prestations_encaissements", "")))
        profile["option_tva_debits"] = st.selectbox("Option pour le paiement de la TVA d'après les débits", yes_no, index=option_index(yes_no, profile.get("option_tva_debits", "")))

    scope = regulatory_scope(data)
    st.markdown("#### Lecture automatique du périmètre")
    cols = st.columns(4)
    for col, (label, value) in zip(cols, [("Réception", scope["reception"]), ("Émission / e-reporting", scope["emission"]), ("E-reporting transactions", scope["ereporting_transactions"]), ("E-reporting paiements", scope["ereporting_paiements"])]):
        col.markdown(f'<div class="metric-card"><div class="metric-label">{label}</div><div class="scope-value">{value}</div></div>', unsafe_allow_html=True)
    st.caption("Cette lecture est une aide au cadrage. Les cas particuliers doivent être validés avec la direction financière, le conseil fiscal et la plateforme.")
    render_bottom_navigation("Profil")


def render_platform(data: dict) -> None:
    render_step_header(2, "Plateforme agréée et annuaire", "Vérifiez l'agrément définitif à la date du contrôle puis la ligne d'annuaire réellement utilisée pour le routage.")
    platform = data["platform"]
    st.markdown("[Consulter la liste officielle des plateformes agréées](https://www.impots.gouv.fr/je-consulte-la-liste-des-plateformes-agreees)")
    left, right = st.columns(2)
    yes_no = ["À déterminer", "Oui", "Non"]
    with left:
        platform["nom"] = st.text_input("Nom exact de la plateforme", value=platform.get("nom", ""))
        platform["agrement_verifie"] = st.selectbox("Agrément définitif vérifié", yes_no, index=option_index(yes_no, platform.get("agrement_verifie", "")))
        platform["date_verification"] = st.date_input("Date de vérification de l'agrément", value=parse_date(platform.get("date_verification")), format="DD/MM/YYYY").isoformat()
        platform["preuve_agrement"] = st.text_input("Référence de la preuve d'agrément", value=platform.get("preuve_agrement", ""), placeholder="Ex. P-01")
    with right:
        platform["annuaire_verifie"] = st.selectbox("Ligne d'annuaire active vérifiée", yes_no, index=option_index(yes_no, platform.get("annuaire_verifie", "")))
        granularities = ["SIREN", "SIRET", "Code routage", "Suffixe"]
        platform["maille_adressage"] = st.selectbox("Maille d'adressage", granularities, index=option_index(granularities, platform.get("maille_adressage", "SIREN")))
        platform["code_routage"] = st.text_input("Code routage ou suffixe, si applicable", value=platform.get("code_routage", ""))
        platform["preuve_annuaire"] = st.text_input("Référence de la preuve annuaire", value=platform.get("preuve_annuaire", ""), placeholder="Ex. P-02")
    st.markdown("#### Grille de contrôle")
    render_control_editor(data, "platform_controls", "editor_platform")
    render_bottom_navigation("Plateforme")


def render_formats(data: dict) -> None:
    render_step_header(3, "Formats, données et mentions", "Contrôlez à la fois la représentation lisible et les données structurées de la facture témoin.")
    st.info("Un PDF ordinaire ne constitue pas une facture électronique réglementaire. Le contrôle doit porter sur le fichier structuré UBL/CII ou le XML embarqué dans un Factur-X.")
    render_control_editor(data, "format_data_controls", "editor_formats")
    render_bottom_navigation("Formats")


def render_reception(data: dict) -> None:
    render_step_header(4, "Réception, cycle de vie et anomalies", "Testez le scénario nominal et les cas dégradés avec des preuves horodatées.")
    nominal, anomalies = st.tabs(["Flux nominal et statuts", "Cas d'anomalie"])
    with nominal:
        render_control_editor(data, "reception_controls", "editor_reception")
    with anomalies:
        render_control_editor(data, "anomaly_controls", "editor_anomalies")
    render_bottom_navigation("Réception")


def render_ereporting(data: dict) -> None:
    render_step_header(5, "E-reporting des transactions et paiements", "Le périmètre dépend des opérations avec les non-assujettis, de l'international et de l'exigibilité de la TVA.")
    scope = regulatory_scope(data)
    c1, c2 = st.columns(2)
    c1.info(f"Transactions : {scope['ereporting_transactions']}")
    c2.info(f"Paiements : {scope['ereporting_paiements']}")
    st.caption("Si un contrôle n'est pas applicable, sélectionnez N/A et expliquez précisément le motif dans la preuve ou justification.")
    render_control_editor(data, "ereporting_controls", "editor_ereporting")
    render_bottom_navigation("E-reporting")


def render_security(data: dict) -> None:
    render_step_header(6, "Sécurité, exploitation et preuves", "Ces contrôles Hympyr complètent le référentiel fiscal sans être présentés comme une homologation DGFiP.")
    render_control_editor(data, "security_controls", "editor_security")
    st.markdown("#### Registre des preuves")
    frame = pd.DataFrame(data["proofs"])
    edited = st.data_editor(
        frame,
        column_order=["reference", "description", "emplacement"],
        column_config={"reference": st.column_config.TextColumn("Réf.", width="small"), "description": st.column_config.TextColumn("Description", width="large"), "emplacement": st.column_config.TextColumn("Emplacement sécurisé", width="large")},
        num_rows="dynamic", hide_index=True, use_container_width=True, key="editor_proofs",
    )
    data["proofs"] = rows_from_editor(edited)
    render_bottom_navigation("SSI")


def render_gaps(data: dict) -> None:
    render_step_header(7, "Écarts et actions correctives", "Chaque résultat non conforme doit être relié à son ID de contrôle et à une action pilotée.")
    nonconforming_ids = [row["id"] for row in all_controls(data) if row.get("resultat") == "Non conforme"]
    if nonconforming_ids:
        st.warning("IDs à traiter : " + ", ".join(nonconforming_ids))
    frame = pd.DataFrame(data["gaps"])
    edited = st.data_editor(
        frame,
        column_order=["numero", "controle_id", "ecart", "risque", "action", "responsable", "echeance"],
        column_config={
            "numero": st.column_config.TextColumn("N°", width="small"), "controle_id": st.column_config.TextColumn("ID contrôle", width="small"),
            "ecart": st.column_config.TextColumn("Écart constaté", width="large"), "risque": st.column_config.SelectboxColumn("Risque", options=["Faible", "Moyen", "Élevé", "Critique"], required=True, width="small"),
            "action": st.column_config.TextColumn("Action corrective", width="large"), "responsable": st.column_config.TextColumn("Responsable", width="medium"),
            "echeance": st.column_config.TextColumn("Échéance", width="medium", help="Format recommandé : JJ/MM/AAAA"),
        },
        num_rows="dynamic", hide_index=True, use_container_width=True, key="editor_gaps",
    )
    rows = rows_from_editor(edited)
    for index, row in enumerate(rows, 1):
        row["numero"] = f"{index:02d}"
    data["gaps"] = rows
    render_bottom_navigation("Écarts")


def render_validation(data: dict) -> None:
    render_step_header(8, "Synthèse, validation et rapport PDF", "Concluez uniquement sur la base des contrôles et preuves consignés dans le dossier.")
    conclusion = data["conclusion"]
    left, right = st.columns([1.1, 1])
    with left:
        results = ["Non conclu", "Prêt - alignement démontré", "Prêt avec réserves", "Non prêt", "Contrôle impossible"]
        conclusion["resultat_general"] = st.selectbox("Conclusion générale", results, index=option_index(results, conclusion.get("resultat_general", "")))
        conclusion["commentaires"] = st.text_area("Synthèse et réserves", value=conclusion.get("commentaires", ""), height=145)
        enable_next = st.checkbox("Planifier un prochain contrôle", value=bool(conclusion.get("prochain_controle")))
        conclusion["prochain_controle"] = st.date_input("Date du prochain contrôle", value=parse_date(conclusion.get("prochain_controle")), format="DD/MM/YYYY").isoformat() if enable_next else ""
        conclusion["controleur_signature"] = st.text_input("Contrôleur - nom", value=conclusion.get("controleur_signature", ""))
        conclusion["responsable_validation"] = st.text_input("Responsable de validation", value=conclusion.get("responsable_validation", ""))
        data["metadata"]["statut_controle"] = st.selectbox("Statut du dossier", ["À réaliser", "En cours", "Prêt", "Avec réserves", "Non prêt"], index=option_index(["À réaliser", "En cours", "Prêt", "Avec réserves", "Non prêt"], data["metadata"].get("statut_controle", "")))
    with right:
        data["attachments"] = st.multiselect("Pièces justificatives présentes dans le dossier", ATTACHMENTS, default=data.get("attachments", []))
        issues = validation_issues(data)
        if issues:
            st.warning(f"{len(issues)} point(s) empêchent un rapport final sans réserve documentaire.")
            with st.expander("Voir les points bloquants", expanded=True):
                for issue in issues:
                    st.write(f"- {issue}")
        else:
            st.success("Dossier complet et cohérent pour générer le rapport final.")

        allow_draft = st.checkbox("Autoriser un rapport marqué BROUILLON", value=bool(issues), disabled=not issues)
        current_fingerprint = data_fingerprint(data)
        if st.session_state.generated_pdf and st.session_state.generated_fingerprint != current_fingerprint:
            st.session_state.generated_pdf = None
            st.session_state.generated_fingerprint = None
            st.info("Les données ont changé. Générez un nouveau rapport PDF.")

        if st.button("Générer le rapport PDF Hympyr", type="primary", use_container_width=True, disabled=bool(issues) and not allow_draft):
            try:
                pdf_bytes = generate_pdf(data, TEMPLATE_PATH, draft=bool(issues))
                reference = str(data["metadata"].get("reference_facture", "")).strip().replace("/", "-").replace("\\", "-")
                suffix = f"_{reference}" if reference else ""
                st.session_state.generated_name = f"Rapport_preparation_facturation_electronique_Hympyr{suffix}.pdf"
                st.session_state.generated_pdf = pdf_bytes
                st.session_state.generated_fingerprint = current_fingerprint
                st.success("Rapport PDF généré. Il constate les contrôles réalisés et ne vaut pas certification de la DGFiP.")
            except Exception:
                LOGGER.exception("Échec de la génération du PDF")
                st.error("La génération du PDF a échoué. Vérifiez le gabarit puis réessayez.")

        if st.session_state.generated_pdf:
            st.download_button("Télécharger le rapport PDF", data=st.session_state.generated_pdf, file_name=st.session_state.generated_name, mime="application/pdf", type="primary", use_container_width=True)
            st.caption("Le PDF est statique et figé au moment de la génération.")
    render_bottom_navigation("Validation")


init_state()
data = st.session_state.control_data
render_header()
render_sidebar(data)

page = st.session_state.current_page
if page == "Hub":
    render_hub(data)
elif page == "Profil":
    render_profile(data)
elif page == "Plateforme":
    render_platform(data)
elif page == "Formats":
    render_formats(data)
elif page == "Réception":
    render_reception(data)
elif page == "E-reporting":
    render_ereporting(data)
elif page == "SSI":
    render_security(data)
elif page == "Écarts":
    render_gaps(data)
elif page == "Validation":
    render_validation(data)
