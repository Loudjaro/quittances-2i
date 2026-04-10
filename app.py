from flask import Flask, request, send_file, jsonify
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
import calendar, io, base64, os
from datetime import datetime

app = Flask(__name__)

W, H = A4
MARGIN_L, MARGIN_R = 50, 50

MOIS_FR = {
    1:"janvier",2:"février",3:"mars",4:"avril",5:"mai",6:"juin",
    7:"juillet",8:"août",9:"septembre",10:"octobre",11:"novembre",12:"décembre"
}

def fmt(n):
    try:
        return f"{int(float(n)):,}".replace(",", " ") + " Fr CFA"
    except:
        return f"{n} Fr CFA"

def wrap(c, text, font, size, max_w):
    words, lines, cur = text.split(" "), [], ""
    for w in words:
        test = cur + (" " if cur else "") + w
        if c.stringWidth(test, font, size) < max_w:
            cur = test
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines

def get_logo():
    logo_path = os.path.join(os.path.dirname(__file__), "logo.png")
    if os.path.exists(logo_path):
        from PIL import Image as PILImage
        import numpy as np
        img = PILImage.open(logo_path).convert("RGBA")
        data = np.array(img)
        r,g,b,a = data[:,:,0],data[:,:,1],data[:,:,2],data[:,:,3]
        lum = 0.299*r.astype(float)+0.587*g.astype(float)+0.114*b.astype(float)
        data[lum > 210] = [255,255,255,0]
        clean = PILImage.fromarray(data)
        buf = io.BytesIO()
        clean.save(buf, format="PNG")
        buf.seek(0)
        return ImageReader(buf)
    return None

def generate_pdf(nom, prenom, appt, zone, loyer, mode_paie, date_paie, mois_slug=None):
    if not mois_slug:
        now = datetime.now()
        mois_slug = f"{now.year}{now.month:02d}"

    year  = int(mois_slug[:4])
    month = int(mois_slug[4:6])
    last_day = calendar.monthrange(year, month)[1]
    d_debut  = f"01/{month:02d}/{year}"
    d_fin    = f"{last_day}/{month:02d}/{year}"
    mois_lbl = f"{MOIS_FR[month]} {year}"

    nom_complet = f"{nom} {prenom}".strip()
    right  = W - MARGIN_R
    col_w  = W - MARGIN_L - MARGIN_R

    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)

    logo = get_logo()

    # En-tête
    title_y  = H - 48
    period_y = H - 66
    addr_y   = H - 81
    ref_y    = H - 95

    c.setFillColorRGB(0.08,0.08,0.08)
    c.setFont("Helvetica-Bold", 18)
    c.drawRightString(right, title_y, "QUITTANCE DE LOYER")
    c.setFont("Helvetica", 10)
    c.setFillColorRGB(0.25,0.25,0.25)
    c.drawRightString(right, period_y, f"Période du {d_debut} au {d_fin}")
    c.setFont("Helvetica", 8.5)
    c.setFillColorRGB(0.45,0.45,0.45)
    c.drawRightString(right, addr_y, "Immeuble 2i  —  Palmeraies, Cocody / Abidjan, Côte d'Ivoire")
    c.setFont("Helvetica", 8)
    c.setFillColorRGB(0.55,0.55,0.55)
    c.drawRightString(right, ref_y, f"Réf. : {mois_slug}{appt}")

    if logo:
        text_top    = title_y + 14
        text_bottom = ref_y - 6
        logo_h = text_top - text_bottom
        logo_w = logo_h * (2000 / 1090)
        c.drawImage(logo, MARGIN_L, text_bottom, width=logo_w, height=logo_h,
                    mask='auto', preserveAspectRatio=True)

    sep1_y = ref_y - 18
    c.setStrokeColorRGB(0.72,0.72,0.72)
    c.setLineWidth(0.7)
    c.line(MARGIN_L, sep1_y, right, sep1_y)

    bl_top = sep1_y - 24
    c.setFillColorRGB(0.08,0.08,0.08)
    c.setFont("Helvetica-Bold", 9)
    c.drawString(MARGIN_L, bl_top, "BAILLEUR")
    c.setFont("Helvetica", 9)
    c.setFillColorRGB(0.2,0.2,0.2)
    c.drawString(MARGIN_L, bl_top-15, "Madame Diaby Djeneba")
    c.drawString(MARGIN_L, bl_top-28, "Immeuble 2i — Palmeraies, Cocody / Abidjan")
    c.drawString(MARGIN_L, bl_top-41, "Côte d'Ivoire")

    mid = W/2+10
    c.setFillColorRGB(0.08,0.08,0.08)
    c.setFont("Helvetica-Bold", 9)
    c.drawString(mid, bl_top, "LOCATAIRE")
    c.setFont("Helvetica", 9)
    c.setFillColorRGB(0.2,0.2,0.2)
    c.drawString(mid, bl_top-15, nom_complet)
    c.setFont("Helvetica", 8.5)
    c.drawString(mid, bl_top-28, f"Appt {appt} - {zone}, Immeuble 2i")
    c.drawString(mid, bl_top-40, "Palmeraies, Cocody / Abidjan, Côte d'Ivoire")

    sep2_y = bl_top - 58
    c.setStrokeColorRGB(0.72,0.72,0.72)
    c.setLineWidth(0.5)
    c.line(MARGIN_L, sep2_y, right, sep2_y)

    body_y = sep2_y - 24
    c.setFillColorRGB(0.18,0.18,0.18)
    c.setFont("Helvetica", 9.5)
    texte = (f"Je soussignée, Madame Diaby Djeneba, propriétaire de l'immeuble 2i situé aux Palmeraies, "
             f"Cocody / Abidjan, déclare avoir reçu de {nom_complet}, locataire de l'appartement {appt} ({zone}), "
             f"la somme de {fmt(loyer)} au titre du loyer pour la période du {d_debut} au {d_fin}.")
    for line in wrap(c, texte, "Helvetica", 9.5, col_w):
        c.drawString(MARGIN_L, body_y, line)
        body_y -= 15

    tbl_top = body_y - 24
    row_h   = 20
    c.setFillColorRGB(0.12,0.12,0.12)
    c.rect(MARGIN_L, tbl_top-row_h, col_w, row_h, fill=1, stroke=0)
    c.setFillColorRGB(1,1,1)
    c.setFont("Helvetica-Bold", 9)
    c.drawString(MARGIN_L+8, tbl_top-row_h+6, "Désignation")
    c.drawRightString(right-8, tbl_top-row_h+6, "Montant")

    c.setFillColorRGB(0.96,0.96,0.96)
    c.rect(MARGIN_L, tbl_top-2*row_h, col_w, row_h, fill=1, stroke=0)
    c.setFillColorRGB(0.18,0.18,0.18)
    c.setFont("Helvetica", 9.5)
    c.drawString(MARGIN_L+8, tbl_top-2*row_h+6, "Loyer mensuel")
    c.drawRightString(right-8, tbl_top-2*row_h+6, fmt(loyer))

    c.setFillColorRGB(1,1,1)
    c.rect(MARGIN_L, tbl_top-3*row_h, col_w, row_h, fill=1, stroke=0)
    c.setFillColorRGB(0.18,0.18,0.18)
    c.drawString(MARGIN_L+8, tbl_top-3*row_h+6, "Charges locatives")
    c.drawRightString(right-8, tbl_top-3*row_h+6, "0 Fr CFA")

    c.setFillColorRGB(0.08,0.08,0.08)
    c.rect(MARGIN_L, tbl_top-4*row_h, col_w, row_h, fill=1, stroke=0)
    c.setFillColorRGB(1,1,1)
    c.setFont("Helvetica-Bold", 9.5)
    c.drawString(MARGIN_L+8, tbl_top-4*row_h+6, "Total reçu")
    c.drawRightString(right-8, tbl_top-4*row_h+6, fmt(loyer))

    c.setStrokeColorRGB(0.72,0.72,0.72)
    c.setLineWidth(0.5)
    c.rect(MARGIN_L, tbl_top-4*row_h, col_w, 4*row_h, fill=0, stroke=1)

    pay_y = tbl_top-4*row_h-24
    c.setFillColorRGB(0.18,0.18,0.18)
    c.setFont("Helvetica", 9.5)
    c.drawString(MARGIN_L, pay_y, f"Mode de paiement : {mode_paie}")
    c.drawString(MARGIN_L, pay_y-16, f"Date d'émission : {date_paie}")

    leg_top = pay_y - 38
    c.setStrokeColorRGB(0.78,0.78,0.78)
    c.rect(MARGIN_L, leg_top-36, col_w, 42, fill=0, stroke=1)
    c.setFont("Helvetica", 7.5)
    c.setFillColorRGB(0.45,0.45,0.45)
    leg1 = ("Cette quittance est établie conformément aux dispositions de la loi ivoirienne relative aux "
            "baux d'habitation et aux locaux à usage commercial (Loi n°77-1444 du 14 décembre 1977).")
    lly = leg_top - 8
    for line in wrap(c, leg1, "Helvetica", 7.5, col_w-20)[:2]:
        c.drawString(MARGIN_L+8, lly, line)
        lly -= 11
    c.drawString(MARGIN_L+8, lly, "Document valable uniquement après encaissement effectif du loyer.")

    c.setStrokeColorRGB(0.78,0.78,0.78)
    c.line(MARGIN_L, 38, right, 38)
    c.setFont("Helvetica", 7)
    c.setFillColorRGB(0.6,0.6,0.6)
    c.drawString(MARGIN_L, 26, "Immeuble 2i — Palmeraies, Cocody / Abidjan, Côte d'Ivoire")
    c.drawRightString(right, 26, f"Réf. {mois_slug}{appt}  |  {mois_lbl}")

    c.showPage()
    c.save()
    buf.seek(0)
    return buf

@app.route("/generate", methods=["POST"])
def generate():
    data = request.json
    nom       = data.get("nom", "")
    prenom    = data.get("prenom", "")
    appt      = data.get("appt", "")
    zone      = data.get("zone", "")
    loyer     = data.get("loyer", 0)
    mode_paie = data.get("mode_paie", "Dépôt bancaire")
    date_paie = data.get("date_paie", "")
    mois_slug = data.get("mois_slug", "")

    pdf_buf = generate_pdf(nom, prenom, appt, zone, loyer, mode_paie, date_paie, mois_slug)
    pdf_b64 = base64.b64encode(pdf_buf.read()).decode("utf-8")

    nom_fichier = f"Quittance_{nom}_{prenom}_{mois_slug}.pdf".replace(" ", "_")

    return jsonify({
        "pdf_base64": pdf_b64,
        "filename": nom_fichier,
        "status": "ok"
    })

@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "service": "Quittances 2i"})

if __name__ == "__main__":
    app.run(debug=False, host="0.0.0.0", port=5000)
