"""Générateur PDF statique conforme au gabarit Hympyr."""

from __future__ import annotations

from copy import deepcopy
from datetime import date, datetime
from html import escape
from io import BytesIO
import math
from pathlib import Path
from typing import Any

from pypdf import PdfReader, PdfWriter
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import BaseDocTemplate, Frame, KeepTogether, PageBreak, PageTemplate, Paragraph, Spacer, Table, TableStyle

from data_model import ATTACHMENTS, OFFICIAL_SOURCES, REFERENCE_VERSION, regulatory_scope


GREEN = colors.HexColor("#0C9D67")
DARK_GREEN = colors.HexColor("#004B36")
PALE_GREEN = colors.HexColor("#E8F5F0")
SOFT_GRAY = colors.HexColor("#F3F5F4")
LINE = colors.HexColor("#CAD8D2")
INK = colors.HexColor("#122E26")
MUTED = colors.HexColor("#5C6D67")
WHITE = colors.white

PAGE_W, PAGE_H = A4
LEFT = 22 * mm
RIGHT = 28 * mm
BODY_W = PAGE_W - LEFT - RIGHT
BODY_BOTTOM = 30 * mm
BODY_TOP = 246 * mm
BODY_H = BODY_TOP - BODY_BOTTOM

_FONTS_REGISTERED = False


def _register_fonts(assets_dir: Path) -> None:
    global _FONTS_REGISTERED
    if _FONTS_REGISTERED:
        return
    pdfmetrics.registerFont(TTFont("HympyrSans", str(assets_dir / "DejaVuSans.ttf")))
    pdfmetrics.registerFont(TTFont("HympyrSansBold", str(assets_dir / "DejaVuSans-Bold.ttf")))
    pdfmetrics.registerFont(TTFont("HympyrSansItalic", str(assets_dir / "DejaVuSans-Oblique.ttf")))
    _FONTS_REGISTERED = True


def _clean(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, float) and math.isnan(value):
        return ""
    return str(value).strip()


def _safe(value: Any) -> str:
    return escape(_clean(value), quote=True)


def _format_date(value: Any) -> str:
    raw = _clean(value)
    if not raw:
        return "À renseigner"
    try:
        parsed = datetime.strptime(raw[:10], "%Y-%m-%d").date()
    except ValueError:
        return raw
    months = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août", "septembre", "octobre", "novembre", "décembre"]
    return f"{parsed.day} {months[parsed.month - 1]} {parsed.year}"


def _box(label: str, selected: bool = False) -> str:
    symbol = "☒" if selected else "☐"
    return f"{symbol} {_safe(label)}"


def _choices(options: list[str], selected: str) -> str:
    return "&nbsp;&nbsp;".join(_box(item, item == selected) for item in options)


def _styles() -> dict[str, ParagraphStyle]:
    sheet = getSampleStyleSheet()
    return {
        "kicker": ParagraphStyle("Kicker", fontName="HympyrSansBold", fontSize=7.2, leading=9, textColor=GREEN, spaceAfter=4),
        "title": ParagraphStyle("TitleBrand", fontName="HympyrSansBold", fontSize=20, leading=22, textColor=DARK_GREEN, spaceAfter=5),
        "subtitle": ParagraphStyle("SubtitleBrand", fontName="HympyrSansItalic", fontSize=8.5, leading=11, textColor=MUTED, spaceAfter=9),
        "section": ParagraphStyle("SectionBrand", fontName="HympyrSansBold", fontSize=12.5, leading=15, textColor=DARK_GREEN, spaceBefore=3, spaceAfter=5, keepWithNext=True),
        "subsection": ParagraphStyle("SubsectionBrand", fontName="HympyrSansBold", fontSize=9.5, leading=12, textColor=DARK_GREEN, spaceBefore=3, spaceAfter=4, keepWithNext=True),
        "body": ParagraphStyle("BodyBrand", fontName="HympyrSans", fontSize=8.2, leading=10.8, textColor=INK, spaceAfter=5),
        "small": ParagraphStyle("SmallBrand", fontName="HympyrSans", fontSize=7.1, leading=8.8, textColor=INK),
        "cell": ParagraphStyle("CellBrand", fontName="HympyrSans", fontSize=6.8, leading=8.2, textColor=INK),
        "cell_bold": ParagraphStyle("CellBoldBrand", fontName="HympyrSansBold", fontSize=6.8, leading=8.2, textColor=DARK_GREEN),
        "cell_white": ParagraphStyle("CellWhiteBrand", fontName="HympyrSansBold", fontSize=6.6, leading=7.8, textColor=WHITE),
        "tiny": ParagraphStyle("TinyBrand", fontName="HympyrSans", fontSize=6.3, leading=7.5, textColor=MUTED),
    }


def _paragraph(text: Any, style: ParagraphStyle) -> Paragraph:
    return Paragraph(_safe(text) or "&nbsp;", style)


def _rich(text: str, style: ParagraphStyle) -> Paragraph:
    return Paragraph(text or "&nbsp;", style)


def _section(number: str, label: str, styles: dict[str, ParagraphStyle]) -> Paragraph:
    return _rich(f'<font color="#0C9D67">{number}</font>&nbsp;&nbsp;{_safe(label)}', styles["section"])


def _table(data: list[list[Any]], widths: list[float], *, header: bool = True, compact: bool = True, row_heights=None) -> Table:
    table = Table(data, colWidths=widths, rowHeights=row_heights, repeatRows=1 if header else 0, hAlign="LEFT")
    pad = 4 if compact else 5
    commands = [
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), pad),
        ("BOTTOMPADDING", (0, 0), (-1, -1), pad),
        ("GRID", (0, 0), (-1, -1), 0.45, LINE),
    ]
    body_start = 0
    if header:
        commands += [("BACKGROUND", (0, 0), (-1, 0), DARK_GREEN), ("TEXTCOLOR", (0, 0), (-1, 0), WHITE)]
        body_start = 1
    for row in range(body_start, len(data)):
        if (row - body_start) % 2 == 1:
            commands.append(("BACKGROUND", (0, row), (-1, row), SOFT_GRAY))
    table.setStyle(TableStyle(commands))
    return table


def _page_decorator(data: dict[str, Any], total_pages: int | None, draft: bool):
    metadata = data.get("metadata", {})
    display_date = _format_date(metadata.get("date_controle"))

    def draw(canvas, doc):
        page_no = canvas.getPageNumber()
        canvas.saveState()
        canvas.setFillColor(WHITE)
        canvas.rect(350, 747, 175, 35, fill=1, stroke=0)
        canvas.setFillColor(DARK_GREEN)
        canvas.setFont("HympyrSansBold", 6.5)
        canvas.drawRightString(522, 773, "PRÉPARATION FACTURATION ÉLECTRONIQUE")
        canvas.setFont("HympyrSans", 6.4)
        canvas.drawRightString(522, 760, display_date)
        canvas.setFillColor(MUTED)
        canvas.setFont("HympyrSans", 6.2)
        page_label = f"Page {page_no}" if total_pages is None else f"Page {page_no} / {total_pages}"
        canvas.drawRightString(518, 60, page_label)
        if draft:
            draft_red = colors.HexColor("#A63C3C")
            canvas.setStrokeColor(draft_red)
            canvas.setLineWidth(0.8)
            canvas.roundRect(447, 710, 76, 17, 4, fill=0, stroke=1)
            canvas.setFillColor(draft_red)
            canvas.setFont("HympyrSansBold", 7)
            canvas.drawCentredString(485, 716, "BROUILLON")
        canvas.restoreState()

    return draw


def _build_story(data: dict[str, Any], styles: dict[str, ParagraphStyle]) -> list[Any]:
    metadata = data.get("metadata", {})
    profile = data.get("profile", {})
    platform = data.get("platform", {})
    conclusion = data.get("conclusion", {})
    story: list[Any] = []

    def control_table(rows: list[dict[str, Any]]) -> Table:
        table_rows = [[
            _rich("ID", styles["cell_white"]), _rich("Contrôle, attendu et source", styles["cell_white"]),
            _rich("Résultat", styles["cell_white"]), _rich("Preuve / justification", styles["cell_white"]),
        ]]
        for row in rows:
            detail = (
                f"<b>{_safe(row.get('controle'))}</b><br/>"
                f"{_safe(row.get('attendu'))}<br/>"
                f'<font color="#5C6D67" size="5.7">Source : {_safe(row.get("source"))}</font>'
            )
            table_rows.append([
                _paragraph(row.get("id"), styles["cell_bold"]), _rich(detail, styles["cell"]),
                _rich(_choices(["Conforme", "Non conforme", "N/A"], _clean(row.get("resultat"))), styles["cell"]),
                _paragraph(row.get("preuve"), styles["cell"]),
            ])
        return _table(table_rows, [20*mm, 65*mm, 32*mm, BODY_W - 117*mm])

    story += [
        _rich("RAPPORT DE PRÉPARATION ET DE CONTRÔLE INTERNE", styles["kicker"]),
        _rich("Facturation électronique", styles["title"]),
        _rich("Périmètre fiscal, plateforme, données, cycle de vie, e-reporting et sécurité", styles["subtitle"]),
    ]
    status = Table([[
        _rich("STATUT DU CONTRÔLE", styles["cell_white"]),
        _rich(_choices(["À réaliser", "En cours", "Prêt", "Avec réserves", "Non prêt"], _clean(metadata.get("statut_controle"))), styles["cell_bold"]),
    ]], colWidths=[45*mm, BODY_W - 45*mm], hAlign="LEFT")
    status.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, 0), DARK_GREEN), ("BACKGROUND", (1, 0), (1, 0), PALE_GREEN),
        ("GRID", (0, 0), (-1, -1), 0.45, LINE), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6), ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    story += [status, Spacer(1, 7), _section("01", "Entité et périmètre", styles)]

    meta_rows = [[_rich("Champ", styles["cell_white"]), _rich("Information", styles["cell_white"])]]
    fields = [
        ("Société contrôlée", metadata.get("societe")),
        ("SIREN", metadata.get("siren")),
        ("SIRET contrôlé", metadata.get("siret") or "Non renseigné"),
        ("Date du contrôle", _format_date(metadata.get("date_controle"))),
        ("Contrôle réalisé par", metadata.get("controleur")),
        ("Responsable comptable", metadata.get("responsable_comptable")),
        ("Logiciel comptable / ERP", metadata.get("logiciel")),
        ("Environnement", metadata.get("environnement")),
        ("Référence de la facture test", metadata.get("reference_facture")),
    ]
    for label, value in fields:
        meta_rows.append([_paragraph(label, styles["cell_bold"]), _paragraph(value or "À renseigner", styles["cell"])])
    story += [_table(meta_rows, [48*mm, BODY_W - 48*mm]), Spacer(1, 6)]

    profile_rows = [[_rich("Qualification", styles["cell_white"]), _rich("Valeur", styles["cell_white"])]]
    profile_fields = [
        ("Taille de l'entreprise", profile.get("taille_entreprise")), ("Régime de TVA", profile.get("regime_tva")),
        ("B2B France", profile.get("b2b_france")), ("B2C / non-assujettis", profile.get("b2c")),
        ("Opérations internationales", profile.get("international")), ("Prestations à TVA sur encaissements", profile.get("prestations_encaissements")),
        ("Option TVA sur les débits", profile.get("option_tva_debits")),
    ]
    for label, value in profile_fields:
        profile_rows.append([_paragraph(label, styles["cell_bold"]), _paragraph(value, styles["cell"])])
    story += [_rich("Qualification réglementaire", styles["subsection"]), _table(profile_rows, [70*mm, BODY_W - 70*mm]), Spacer(1, 6)]

    scope = regulatory_scope(data)
    scope_rows = [[_rich("Volet", styles["cell_white"]), _rich("Lecture du périmètre", styles["cell_white"])]]
    for label, key in (("Réception", "reception"), ("Émission / e-reporting", "emission"), ("E-reporting transactions", "ereporting_transactions"), ("E-reporting paiements", "ereporting_paiements")):
        scope_rows.append([_paragraph(label, styles["cell_bold"]), _paragraph(scope[key], styles["cell"])])
    story += [_rich("Échéances et volets applicables", styles["subsection"]), _table(scope_rows, [52*mm, BODY_W - 52*mm]), Spacer(1, 6)]

    note = Table([[_rich(
        f"<b>PORTÉE DU RAPPORT</b> - Référentiel utilisé : {_safe(data.get('reference_version') or REFERENCE_VERSION)}. "
        "Ce document consigne des contrôles et des preuves. Il ne vaut ni certification, ni agrément, ni décision de la DGFiP.",
        styles["small"],
    )]], colWidths=[BODY_W], hAlign="LEFT")
    note.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), PALE_GREEN), ("BOX", (0, 0), (-1, -1), 0.6, GREEN),
        ("LEFTPADDING", (0, 0), (-1, -1), 7), ("RIGHTPADDING", (0, 0), (-1, -1), 7),
        ("TOPPADDING", (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    story += [note, PageBreak()]

    story += [_section("02", "Plateforme agréée et annuaire", styles)]
    platform_rows = [[_rich("Élément", styles["cell_white"]), _rich("Valeur contrôlée", styles["cell_white"])]]
    platform_fields = [
        ("Plateforme", platform.get("nom")), ("Agrément définitif vérifié", platform.get("agrement_verifie")),
        ("Date de vérification", _format_date(platform.get("date_verification"))), ("Preuve d'agrément", platform.get("preuve_agrement")),
        ("Ligne d'annuaire vérifiée", platform.get("annuaire_verifie")), ("Maille d'adressage", platform.get("maille_adressage")),
        ("Code routage ou suffixe", platform.get("code_routage") or "Non applicable"), ("Preuve annuaire", platform.get("preuve_annuaire")),
    ]
    for label, value in platform_fields:
        platform_rows.append([_paragraph(label, styles["cell_bold"]), _paragraph(value, styles["cell"])])
    story += [_table(platform_rows, [52*mm, BODY_W - 52*mm]), Spacer(1, 7), control_table(data.get("platform_controls", [])), PageBreak()]

    story += [_section("03", "Formats, données et mentions", styles)]
    story += [_rich("Contrôles de la représentation lisible et des données structurées de la facture témoin.", styles["body"]), control_table(data.get("format_data_controls", [])), PageBreak()]

    story += [_section("04", "Réception et cycle de vie", styles), control_table(data.get("reception_controls", [])), Spacer(1, 7)]
    story += [_section("05", "Tests d'anomalie", styles), control_table(data.get("anomaly_controls", [])), PageBreak()]

    story += [_section("06", "E-reporting des transactions et paiements", styles), control_table(data.get("ereporting_controls", [])), Spacer(1, 7)]
    story += [_section("07", "Sécurité et exploitation Hympyr", styles)]
    story.append(_rich("Les contrôles SSI ci-dessous complètent le référentiel fiscal ; ils ne sont pas présentés comme des exigences d'agrément applicables à Hympyr.", styles["body"]))
    story += [control_table(data.get("security_controls", [])), PageBreak()]

    story += [_section("08", "Registre des preuves", styles)]
    proof_rows = [[_rich("Réf.", styles["cell_white"]), _rich("Nom ou description de la preuve", styles["cell_white"]), _rich("Emplacement sécurisé", styles["cell_white"])]]
    proofs = data.get("proofs", []) or [{"reference": "", "description": "", "emplacement": ""}]
    for row in proofs:
        proof_rows.append([_paragraph(row.get("reference"), styles["cell"]), _paragraph(row.get("description"), styles["cell"]), _paragraph(row.get("emplacement"), styles["cell"])])
    story += [_table(proof_rows, [15*mm, 79*mm, BODY_W - 94*mm]), Spacer(1, 7)]

    story += [_section("09", "Écarts et actions correctives", styles)]
    gap_rows = [[
        _rich("N°", styles["cell_white"]), _rich("ID", styles["cell_white"]), _rich("Écart constaté", styles["cell_white"]), _rich("Risque", styles["cell_white"]),
        _rich("Action corrective", styles["cell_white"]), _rich("Responsable", styles["cell_white"]), _rich("Échéance", styles["cell_white"]),
    ]]
    gaps = [row for row in data.get("gaps", []) if any(_clean(row.get(k)) for k in ("ecart", "action", "responsable", "echeance"))]
    if not gaps:
        gaps = [{"numero": "01", "controle_id": "-", "ecart": "Aucun écart déclaré", "risque": "-", "action": "-", "responsable": "-", "echeance": "-"}]
    for index, row in enumerate(gaps, 1):
        gap_rows.append([
            _paragraph(row.get("numero") or f"{index:02d}", styles["cell"]), _paragraph(row.get("controle_id"), styles["cell"]), _paragraph(row.get("ecart"), styles["cell"]),
            _paragraph(row.get("risque"), styles["cell"]), _paragraph(row.get("action"), styles["cell"]),
            _paragraph(row.get("responsable"), styles["cell"]), _paragraph(row.get("echeance"), styles["cell"]),
        ])
    story += [_table(gap_rows, [8*mm, 16*mm, 31*mm, 18*mm, 38*mm, 28*mm, BODY_W - 139*mm]), Spacer(1, 6)]
    conclusion_box = Table([
        [_rich(_choices(["Prêt - alignement démontré", "Prêt avec réserves", "Non prêt", "Contrôle impossible"], _clean(conclusion.get("resultat_general"))), styles["cell_bold"])],
        [_rich(
            "Commentaires : " + (_safe(conclusion.get("commentaires")) or "________________________________________________________________________________<br/>________________________________________________________________________________"),
            styles["cell"],
        )],
    ], colWidths=[BODY_W], hAlign="LEFT")
    conclusion_box.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, 0), PALE_GREEN), ("GRID", (0, 0), (-1, -1), 0.45, LINE),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6), ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    signature = Table([
        [_rich("Prochain contrôle prévu", styles["cell_bold"]), _paragraph(_format_date(conclusion.get("prochain_controle")), styles["cell"])],
        [_rich("Contrôleur - nom et signature", styles["cell_bold"]), _rich("Responsable - nom et validation", styles["cell_bold"])],
        [_paragraph(conclusion.get("controleur_signature"), styles["cell"]), _paragraph(conclusion.get("responsable_validation"), styles["cell"])],
    ], colWidths=[BODY_W/2, BODY_W/2], rowHeights=[22, 22, 48], hAlign="LEFT")
    signature.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 1), SOFT_GRAY), ("GRID", (0, 0), (-1, -1), 0.45, LINE),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6), ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story += [KeepTogether([_section("10", "Conclusion du contrôle", styles), conclusion_box, Spacer(1, 5), signature]), Spacer(1, 6), _section("11", "Pièces justificatives du dossier", styles)]
    selected_attachments = set(data.get("attachments", []))
    attachment_rows = []
    for start in range(0, len(ATTACHMENTS), 2):
        pair = ATTACHMENTS[start:start + 2]
        attachment_rows.append([_rich(_box(label, label in selected_attachments), styles["small"]) for label in pair] + ([_rich("", styles["small"])] if len(pair) == 1 else []))
    story += [_table(attachment_rows, [BODY_W/2, BODY_W/2], header=False), Spacer(1, 7), _section("12", "Références officielles", styles)]
    source_rows = [[_rich("Référence", styles["cell_white"]), _rich("Source consultable", styles["cell_white"])]]
    for source in OFFICIAL_SOURCES:
        source_rows.append([_paragraph(source["id"], styles["cell_bold"]), _rich(f"{_safe(source['label'])}<br/><font size=\"5.7\">{_safe(source['url'])}</font>", styles["cell"])])
    story.append(_table(source_rows, [35*mm, BODY_W - 35*mm]))
    return story


def _render_overlay(data: dict[str, Any], assets_dir: Path, *, total_pages: int | None, draft: bool) -> bytes:
    _register_fonts(assets_dir)
    styles = _styles()
    stream = BytesIO()
    doc = BaseDocTemplate(
        stream, pagesize=A4, leftMargin=LEFT, rightMargin=RIGHT,
        topMargin=PAGE_H - BODY_TOP, bottomMargin=BODY_BOTTOM,
        title="Rapport de préparation à la facturation électronique",
        author="Hympyr Énergies",
    )
    frame = Frame(LEFT, BODY_BOTTOM, BODY_W, BODY_H, leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)
    doc.addPageTemplates(PageTemplate(id="Hympyr", frames=[frame], onPage=_page_decorator(data, total_pages, draft)))
    doc.build(_build_story(deepcopy(data), styles))
    return stream.getvalue()


def generate_pdf(data: dict[str, Any], template_path: str | Path, *, draft: bool = False) -> bytes:
    """Génère un PDF final en mémoire, avec le gabarit Hympyr sur chaque page."""
    template = Path(template_path)
    if not template.is_file():
        raise FileNotFoundError(f"Gabarit PDF introuvable : {template}")
    assets_dir = template.parent

    first_pass = _render_overlay(data, assets_dir, total_pages=None, draft=draft)
    page_count = len(PdfReader(BytesIO(first_pass)).pages)
    overlay_bytes = _render_overlay(data, assets_dir, total_pages=page_count, draft=draft)
    overlay_reader = PdfReader(BytesIO(overlay_bytes))

    template_bytes = template.read_bytes()
    writer = PdfWriter()
    for overlay_page in overlay_reader.pages:
        background = PdfReader(BytesIO(template_bytes)).pages[0]
        writer.add_page(background)
        writer.pages[-1].merge_page(overlay_page)

    metadata = data.get("metadata", {})
    writer.add_metadata({
        "/Title": "Rapport de préparation à la facturation électronique",
        "/Author": "Hympyr Énergies",
        "/Subject": f"Préparation DGFiP v3.2 - {_clean(metadata.get('reference_facture')) or 'sans référence'}",
        "/CreationDate": datetime.now().strftime("D:%Y%m%d%H%M%S"),
    })
    output = BytesIO()
    writer.write(output)
    result = output.getvalue()
    if not result.startswith(b"%PDF"):
        raise RuntimeError("Le fichier produit n'est pas un PDF valide.")
    return result
