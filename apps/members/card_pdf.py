import io
from datetime import datetime
from django.conf import settings
from django.http import HttpResponse
from reportlab.lib.pagesizes import landscape, A6, A4
from reportlab.lib.units import mm
from reportlab.lib.colors import HexColor, white, black
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
import qrcode
import base64

GREEN = HexColor('#0d3b12')
GOLD = HexColor('#F9A825')
WHITE = white
DARK_GREEN = HexColor('#1B5E20')
LIGHT_GRAY = HexColor('#f0f0f0')
DARK_GRAY = HexColor('#333333')
MED_GRAY = HexColor('#666666')


def generate_qr_image(data, size=100):
    qr = qrcode.make(data)
    buf = io.BytesIO()
    qr.save(buf, format='PNG')
    buf.seek(0)
    return ImageReader(buf)


def get_member_photo(member):
    if member.profile_image:
        try:
            path = str(settings.BASE_DIR / member.profile_image.name)
            return ImageReader(path)
        except Exception:
            pass
    return None


def get_member_signature(member):
    if member.signature:
        try:
            path = str(settings.BASE_DIR / member.signature.name)
            return ImageReader(path)
        except Exception:
            pass
    return None


def draw_card_front(c, member, x_offset=0, y_offset=0, scale=1.0):
    """Draw front of ID card at given offset. Card = 310 x 490 points (scaled)."""
    card_w = 310 * scale
    card_h = 490 * scale
    ox = x_offset
    oy = y_offset

    # Card shadow
    c.setFillColor(HexColor('#e0e0e0'))
    c.roundRect(ox + 2, oy - 2, card_w, card_h, 12, fill=1, stroke=0)
    # Card background
    c.setFillColor(WHITE)
    c.roundRect(ox, oy, card_w, card_h, 12, fill=1, stroke=1)
    c.setStrokeColor(GREEN)
    c.setLineWidth(2)
    c.roundRect(ox, oy, card_w, card_h, 12, fill=0, stroke=1)

    # Top green bar
    c.setFillColor(GREEN)
    p = c.beginPath()
    p.moveTo(ox + 12, oy + card_h - 65 * scale)
    p.lineTo(ox + card_w - 12, oy + card_h - 65 * scale)
    p.lineTo(ox + card_w, oy + card_h)
    p.lineTo(ox, oy + card_h)
    p.close()
    c.drawPath(p, fill=1, stroke=0)

    # Gold accent stripe
    c.setFillColor(GOLD)
    c.rect(ox, oy + card_h - 3, card_w, 3, fill=1, stroke=0)

    # Brand text
    c.setFillColor(WHITE)
    c.setFont('Helvetica-Bold', 7 * scale)
    c.drawCentredString(ox + card_w / 2, oy + card_h - 15 * scale, 'MGOWELO AMCOS')
    c.setFont('Helvetica', 5.5 * scale)
    c.drawCentredString(ox + card_w / 2, oy + card_h - 24 * scale, 'AGRICULTURAL MARKETING COOPERATIVE')

    # Membership card badge
    c.setFillColor(GOLD)
    c.setFont('Helvetica-Bold', 7 * scale)
    badge_w = 100 * scale
    badge_h = 14 * scale
    c.roundRect(ox + card_w / 2 - badge_w / 2, oy + card_h - 42 * scale, badge_w, badge_h, 7, fill=1, stroke=0)
    c.setFillColor(GREEN)
    c.drawCentredString(ox + card_w / 2, oy + card_h - 39 * scale, 'MEMBERSHIP CARD')

    # Photo circle
    photo_r = 32 * scale
    photo_cx = ox + card_w / 2
    photo_cy = oy + card_h - 118 * scale
    c.setFillColor(HexColor('#e0e0e0'))
    c.circle(photo_cx, photo_cy, photo_r + 2, fill=1, stroke=0)
    c.setStrokeColor(GREEN)
    c.setLineWidth(2.5)
    img = get_member_photo(member)
    if img:
        try:
            c.saveState()
            path_circle = c.beginPath()
            path_circle.circle(photo_cx, photo_cy, photo_r)
            c.clipPath(path_circle, stroke=0)
            c.drawImage(img, photo_cx - photo_r, photo_cy - photo_r,
                        width=photo_r * 2, height=photo_r * 2,
                        preserveAspectRatio=True, mask='auto')
            c.restoreState()
        except Exception:
            pass
    else:
        c.setFont('Helvetica', 20 * scale)
        c.setFillColor(HexColor('#999999'))
        c.drawCentredString(photo_cx, photo_cy - 7 * scale, '?')

    # Name
    c.setFillColor(GREEN)
    c.setFont('Helvetica-Bold', 11 * scale)
    name = member.full_name[:30]
    c.drawCentredString(ox + card_w / 2, oy + card_h - 170 * scale, name)

    # ID number
    c.setFillColor(GREEN)
    id_w = 130 * scale
    id_h = 20 * scale
    c.roundRect(ox + card_w / 2 - id_w / 2, oy + card_h - 195 * scale, id_w, id_h, 5, fill=1, stroke=0)
    c.setFillColor(GOLD)
    c.setFont('Helvetica-Bold', 12 * scale)
    c.drawCentredString(ox + card_w / 2, oy + card_h - 192 * scale, member.member_number)

    # Details
    detail_y = oy + card_h - 230 * scale
    line_h = 11 * scale
    details = [
        ('Phone:', member.phone),
        ('Gender:', member.get_gender_display()),
        ('Region:', member.region or 'Iringa'),
        ('Since:', member.joined_at.strftime('%b %Y') if member.joined_at else '-'),
        ('Status:', 'ACTIVE' if member.status == 'active' else member.status.upper()),
    ]
    c.setFont('Helvetica', 8 * scale)
    for label, value in details:
        c.setFillColor(GREEN)
        c.drawString(ox + 20 * scale, detail_y, label)
        c.setFillColor(DARK_GRAY)
        c.drawString(ox + 80 * scale, detail_y, value)
        detail_y -= line_h

    # Bottom bar
    c.setFillColor(GREEN)
    c.roundRect(ox, oy, card_w, 16 * scale, 0, fill=1, stroke=1)
    bottom = [0, 16, 0, 12]  # bottom-left, bottom-right corners only
    c.setFillColor(GREEN)
    p = c.beginPath()
    p.moveTo(ox + 12, oy + 16 * scale)
    p.lineTo(ox + card_w - 12, oy + 16 * scale)
    p.lineTo(ox + card_w, oy)
    p.lineTo(ox, oy)
    p.close()
    c.drawPath(p, fill=1, stroke=0)

    c.setFillColor(GOLD)
    c.setFont('Helvetica-Bold', 6 * scale)
    c.drawCentredString(ox + card_w / 2, oy + 5 * scale, 'MGOWELO AMCOS  •  IRINGA  •  TANZANIA')


def draw_card_back(c, member, qr_img, x_offset=0, y_offset=0, scale=1.0):
    """Draw back of ID card at given offset."""
    card_w = 310 * scale
    card_h = 490 * scale
    ox = x_offset
    oy = y_offset

    # Shadow
    c.setFillColor(HexColor('#e0e0e0'))
    c.roundRect(ox + 2, oy - 2, card_w, card_h, 12, fill=1, stroke=0)
    # Background
    c.setFillColor(WHITE)
    c.roundRect(ox, oy, card_w, card_h, 12, fill=1, stroke=1)
    c.setStrokeColor(GREEN)
    c.setLineWidth(2)
    c.roundRect(ox, oy, card_w, card_h, 12, fill=0, stroke=1)

    # QR Code
    qr_y = oy + card_h - 140 * scale
    if qr_img:
        try:
            c.drawImage(qr_img, ox + card_w / 2 - 50 * scale, qr_y,
                        width=100 * scale, height=100 * scale,
                        preserveAspectRatio=True)
        except Exception:
            pass

    # Info text
    c.setFillColor(GREEN)
    c.setFont('Helvetica-Bold', 9 * scale)
    c.drawCentredString(ox + card_w / 2, oy + card_h - 170 * scale, 'MGOWELO AMCOS')
    c.setFillColor(MED_GRAY)
    c.setFont('Helvetica', 6 * scale)
    lines = [
        'Iringa, Tanzania',
        'Enterprise Cooperative Management System',
        '',
        'Rules:',
        '1. This card is property of MGOWELO AMCOS',
        '2. Report lost card immediately',
        '3. Not transferable',
        '4. Present card for services',
    ]
    text_y = oy + card_h - 200 * scale
    for line in lines:
        c.drawCentredString(ox + card_w / 2, text_y, line)
        text_y -= 9 * scale

    # Signature line
    sig_y = oy + 45 * scale
    c.setStrokeColor(GREEN)
    c.setLineWidth(0.5)
    c.line(ox + 30 * scale, sig_y, ox + card_w - 30 * scale, sig_y)
    c.setFillColor(MED_GRAY)
    c.setFont('Helvetica', 6 * scale)
    c.drawCentredString(ox + card_w / 2, sig_y - 10 * scale, "MEMBER'S SIGNATURE")

    # Signature image
    sig_img = get_member_signature(member)
    if sig_img:
        try:
            c.drawImage(sig_img, ox + card_w / 2 - 40 * scale, sig_y + 5 * scale,
                        width=80 * scale, height=24 * scale,
                        preserveAspectRatio=True)
        except Exception:
            pass

    # Footer
    c.setFillColor(GREEN)
    p = c.beginPath()
    p.moveTo(ox + 12, oy + 16 * scale)
    p.lineTo(ox + card_w - 12, oy + 16 * scale)
    p.lineTo(ox + card_w, oy)
    p.lineTo(ox, oy)
    p.close()
    c.drawPath(p, fill=1, stroke=0)
    c.setFillColor(GOLD)
    c.setFont('Helvetica-Bold', 6 * scale)
    c.drawCentredString(ox + card_w / 2, oy + 5 * scale, f'MGOWELO AMCOS © {datetime.now().year}  •  Scan QR to verify')


def generate_single_card_pdf(member):
    buf = io.BytesIO()
    page_w = 340 * 1.2  # slightly larger than card
    page_h = 510 * 1.2
    c = canvas.Canvas(buf, pagesize=(page_w, page_h))

    # Front
    qr_img = generate_qr_image(
        f'MGOWELO AMCOS\nID: {member.member_number}\nName: {member.full_name}\nPhone: {member.phone}'
    )
    margin_x = (page_w - 310) / 2
    margin_y = (page_h - 490) / 2 + 15
    draw_card_front(c, member, x_offset=margin_x, y_offset=margin_y + 260)
    draw_card_back(c, member, qr_img, x_offset=margin_x, y_offset=margin_y - 240)

    c.save()
    buf.seek(0)
    return buf


def generate_bulk_cards_pdf(members):
    buf = io.BytesIO()
    # A4 landscape: 2 cards side by side, stacked vertically
    page_w, page_h = landscape(A4)
    card_w = 310
    card_h = 490
    cols = 2
    rows = 2
    gap_x = (page_w - cols * card_w) / (cols + 1)
    gap_y = (page_h - rows * card_h) / (rows + 1)

    c = canvas.Canvas(buf, pagesize=landscape(A4))
    count = 0
    for member in members:
        col = count % cols
        row = count // cols % rows
        x = gap_x + col * (card_w + gap_x)
        y = page_h - gap_y - card_h - row * (card_h + gap_y)

        qr_img = generate_qr_image(
            f'MGOWELO AMCOS\nID: {member.member_number}\nName: {member.full_name}\nPhone: {member.phone}'
        )
        draw_card_front(c, member, x_offset=x, y_offset=y)
        draw_card_back(c, member, qr_img, x_offset=x + card_w + 8, y_offset=y)

        count += 1
        if count % (cols * rows) == 0:
            c.showPage()
            # Rebuild background for next page
            c.setFillColor(HexColor('#f0f0f0'))
            c.rect(0, 0, page_w, page_h, fill=1, stroke=0)
            c.setFillColor(WHITE)

    if count % (cols * rows) != 0:
        c.showPage()

    c.save()
    buf.seek(0)
    return buf
