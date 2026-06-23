import io

from flask import Blueprint, Response, jsonify, send_file
from openpyxl import Workbook

from .auth_helpers import login_required
from .models import Installment, Policy, VipCard

reports_bp = Blueprint("reports", __name__, url_prefix="/reports")


def _make_basic_pdf(title, lines):
    escaped_lines = [line.replace("(", "[").replace(")", "]") for line in lines]
    content = ["BT /F1 14 Tf 50 780 Td ({}) Tj ET".format(title)]
    y = 760
    for line in escaped_lines:
        content.append(f"BT /F1 10 Tf 50 {y} Td ({line}) Tj ET")
        y -= 16
    stream = "\n".join(content).encode("latin-1", errors="ignore")

    pdf = b"%PDF-1.4\n"
    objects = []
    objects.append(b"1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj\n")
    objects.append(b"2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj\n")
    objects.append(
        b"3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >> endobj\n"
    )
    objects.append(
        f"4 0 obj << /Length {len(stream)} >> stream\n".encode("latin-1") + stream + b"\nendstream endobj\n"
    )
    objects.append(b"5 0 obj << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> endobj\n")

    offsets = []
    for obj in objects:
        offsets.append(len(pdf))
        pdf += obj

    xref_pos = len(pdf)
    pdf += f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode("latin-1")
    for offset in offsets:
        pdf += f"{offset:010d} 00000 n \n".encode("latin-1")

    pdf += (
        f"trailer << /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref_pos}\n%%EOF".encode("latin-1")
    )
    return pdf


@reports_bp.route("/api/overview")
@login_required
def overview_api():
    return jsonify(
        {
            "insurance": {
                "policies": Policy.query.count(),
                "installments": Installment.query.filter_by(module_type="insurance").count(),
            },
            "vip": {
                "cards": VipCard.query.count(),
                "installments": Installment.query.filter_by(module_type="vip").count(),
            },
        }
    )


@reports_bp.route("/export/insurance.xlsx")
@login_required
def export_insurance_excel():
    wb = Workbook()
    ws = wb.active
    ws.title = "Insurance"
    ws.append(["Policy Number", "Status", "Premium Amount"])
    for policy in Policy.query.order_by(Policy.id).all():
        ws.append([policy.policy_number, policy.status, policy.premium_amount])

    buffer = io.BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    return send_file(
        buffer,
        as_attachment=True,
        download_name="insurance_report.xlsx",
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


@reports_bp.route("/export/vip.xlsx")
@login_required
def export_vip_excel():
    wb = Workbook()
    ws = wb.active
    ws.title = "VIP"
    ws.append(["Card Number", "Status", "Monthly Fee"])
    for card in VipCard.query.order_by(VipCard.id).all():
        ws.append([card.card_number, card.status, card.monthly_fee])

    buffer = io.BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    return send_file(
        buffer,
        as_attachment=True,
        download_name="vip_report.xlsx",
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


@reports_bp.route("/export/dashboard.pdf")
@login_required
def export_dashboard_pdf():
    lines = [
        f"Total policies: {Policy.query.count()}",
        f"Total VIP cards: {VipCard.query.count()}",
        f"Insurance installments: {Installment.query.filter_by(module_type='insurance').count()}",
        f"VIP installments: {Installment.query.filter_by(module_type='vip').count()}",
    ]
    content = _make_basic_pdf("Elite Insurance Dashboard", lines)
    return Response(
        content,
        mimetype="application/pdf",
        headers={"Content-Disposition": "attachment; filename=dashboard_report.pdf"},
    )
