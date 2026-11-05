from pathlib import Path

from docx import Document


def markdown_para_docx(markdown_texto: str, destino: Path) -> None:
    doc = Document()
    for linha in markdown_texto.split("\n"):
        linha_strip = linha.strip()
        if not linha_strip:
            continue
        if linha_strip.startswith("### "):
            doc.add_heading(linha_strip[4:], level=3)
        elif linha_strip.startswith("## "):
            doc.add_heading(linha_strip[3:], level=2)
        elif linha_strip.startswith("# "):
            doc.add_heading(linha_strip[2:], level=1)
        elif linha_strip.startswith(("- ", "* ")):
            doc.add_paragraph(linha_strip[2:], style="List Bullet")
        else:
            doc.add_paragraph(linha_strip)
    doc.save(destino)
