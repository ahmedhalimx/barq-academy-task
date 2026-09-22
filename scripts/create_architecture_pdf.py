from reportlab.lib.colors import HexColor, white
from reportlab.lib.pagesizes import landscape, letter
from reportlab.pdfgen.canvas import Canvas


OUT = "architecture.pdf"
PAGE_W, PAGE_H = landscape(letter)


def box(canvas, x, y, width, height, title, subtitle, color):
    canvas.setFillColor(HexColor(color))
    canvas.roundRect(x, y, width, height, 10, fill=1, stroke=0)
    canvas.setFillColor(white)
    canvas.setFont("Helvetica-Bold", 12)
    canvas.drawCentredString(x + width / 2, y + height - 22, title)
    canvas.setFont("Helvetica", 8)
    for index, line in enumerate(subtitle):
        canvas.drawCentredString(x + width / 2, y + height - 38 - index * 11, line)


def arrow(canvas, start, end, label):
    canvas.setStrokeColor(HexColor("#334155"))
    canvas.setFillColor(HexColor("#334155"))
    canvas.setLineWidth(1.5)
    canvas.line(*start, *end)
    canvas.circle(end[0], end[1], 2, fill=1, stroke=0)
    canvas.setFont("Helvetica", 7)
    canvas.drawCentredString((start[0] + end[0]) / 2, (start[1] + end[1]) / 2 + 5, label)


canvas = Canvas(OUT, pagesize=landscape(letter))
canvas.setTitle("BARQ architecture")
canvas.setFillColor(HexColor("#0f172a"))
canvas.setFont("Helvetica-Bold", 20)
canvas.drawString(36, 570, "BARQ assessment architecture")
canvas.setFillColor(HexColor("#475569"))
canvas.setFont("Helvetica", 9)
canvas.drawString(36, 554, "Current two-instance local stack; recorded final state adds app-03 and changes the public port to 8090.")

canvas.setStrokeColor(HexColor("#93c5fd"))
canvas.roundRect(155, 275, 555, 230, 12, fill=0, stroke=1)
canvas.setFillColor(HexColor("#1d4ed8"))
canvas.setFont("Helvetica-Bold", 10)
canvas.drawString(165, 489, "frontend network")
canvas.setStrokeColor(HexColor("#a7f3d0"))
canvas.roundRect(365, 50, 330, 190, 12, fill=0, stroke=1)
canvas.setFillColor(HexColor("#047857"))
canvas.drawString(375, 224, "backend network (internal)")

box(canvas, 36, 365, 95, 65, "Client", ["loopback HTTP"], "#475569")
box(canvas, 180, 365, 120, 65, "NGINX", ["only published port", "8080 (8090 final)"], "#1d4ed8")
box(canvas, 365, 395, 120, 65, "app-01", ["Flask :8080", "/health, /ready"], "#7c3aed")
box(canvas, 550, 395, 120, 65, "app-02", ["Flask :8080", "distinct identity"], "#7c3aed")
box(canvas, 410, 110, 120, 65, "PostgreSQL", [":5432", "named volume"], "#047857")
box(canvas, 560, 110, 120, 65, "Redis", [":6379", "AOF enabled"], "#047857")

arrow(canvas, (131, 397), (180, 397), "HTTP")
arrow(canvas, (300, 397), (365, 427), "proxy / health")
arrow(canvas, (300, 397), (550, 427), "round robin")
arrow(canvas, (425, 395), (470, 175), "SQL / readiness")
arrow(canvas, (610, 395), (620, 175), "counter / readiness")
arrow(canvas, (485, 427), (560, 142), "apps only")

canvas.setFillColor(HexColor("#0f172a"))
canvas.setFont("Helvetica-Bold", 10)
canvas.drawString(36, 215, "Health and failure boundaries")
canvas.setFont("Helvetica", 8)
notes = [
    "- Docker health check: each app /health; NGINX /health; PostgreSQL pg_isready; Redis ping.",
    "- Public /ready verifies PostgreSQL and Redis through an app instance.",
    "- NGINX is not attached to backend, so it cannot resolve or reach data services directly.",
    "- Remaining single points of failure: Docker host, NGINX, PostgreSQL, Redis, and their storage.",
]
for offset, note in enumerate(notes):
    canvas.drawString(36, 198 - offset * 14, note)

canvas.showPage()
canvas.save()
