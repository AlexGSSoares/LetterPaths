# shape.py

"""
Script para gerar SOMENTE os SVG paths (shapes) das letras, no formato de constantes Dart,
já com INVERSÃO VERTICAL aplicada, para que, quando colar no editor SVG (que tem Y para baixo),
a letra apareça na orientação “de pé” (e não de cabeça para baixo).

Saída:
  - shapes_svg.dart com constantes `shapeLetterA`, `shapeLetterB` etc.,
    cada uma contendo uma única string do atributo 'd', já invertida verticalmente.

Basta rodar:
    python shape.py
e o arquivo shapes_svg.dart será gerado/atualizado.
"""

import os
from fontTools.ttLib import TTFont
from fontTools.pens.svgPathPen import SVGPathPen
from svgpathtools import parse_path

# --- CONFIGURAÇÃO ---
TTF_PATH    = "Cursive-Regular.ttf"        # Caminho para seu arquivo .ttf com a fonte cursiva
OUTPUT_DART = "shapes_svg.dart"            # Arquivo Dart de saída
SCALE       = 600.0                        # “Caixa” final (em px) para cada glifo
EXCLUDE     = set("KYWkyw")                # Se quiser pular determinados caracteres
LETTERS     = [
    c for c in "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
    if c not in EXCLUDE
]


def get_bounding_box(path):
    """
    Retorna (min_x, max_x, min_y, max_y) do Path fornecido,
    examinando cada segmento via path.bpoints().
    """
    xs, ys = [], []
    for seg in path:
        for pt in seg.bpoints():
            xs.append(pt.real)
            ys.append(pt.imag)
    return min(xs), max(xs), min(ys), max(ys)


def main():
    # 1) Abre (ou cria) o arquivo Dart para escrita
    with open(OUTPUT_DART, "w", encoding="utf-8") as dart_f:
        dart_f.write("// Gerado por shape.py (com inversão vertical)\n")
        dart_f.write("class CursiveSvgs {\n\n")

        # 2) Carrega a fonte e faz mapeamento Unicode → glyph name
        font     = TTFont(TTF_PATH)
        glyphset = font.getGlyphSet()
        cmap     = font.getBestCmap()

        # 3) Para cada letra, extrai o d="..." bruto, escala, centraliza, aplica flip e grava
        for char in LETTERS:
            glyph_name = cmap.get(ord(char))
            if not glyph_name:
                print(f"[WARN] Glifo não encontrado para '{char}', pulando.")
                continue

            # 3.1) Extrai o comando SVG bruto do glifo (sem flip ainda)
            pen = SVGPathPen(glyphset)
            glyphset[glyph_name].draw(pen)
            raw_d = pen.getCommands().strip()
            if not raw_d:
                print(f"[WARN] Comandos vazios para '{char}', pulando.")
                continue

            # 3.2) Converte para Path apenas para achar o bounding‐box
            path_obj = parse_path(raw_d)
            min_x, max_x, min_y, max_y = get_bounding_box(path_obj)
            width  = max_x - min_x
            height = max_y - min_y

            # 3.3) Calcula escala uniforme para caber em SCALE×SCALE
            scale_factor = min(SCALE / width, SCALE / height)

            # 3.4) Calcula translação para centrar dentro do quadrado
            tx = (SCALE - (width * scale_factor)) / 2.0 - (min_x * scale_factor)
            ty = (SCALE - (height * scale_factor)) / 2.0 - (min_y * scale_factor)

            # 3.5) Aplica escala e centralização
            transformed = path_obj.scaled(scale_factor, scale_factor)
            transformed = transformed.translated(
                complex(-min_x * scale_factor + tx,
                        -min_y * scale_factor + ty)
            )

            # 3.6) Agora aplicamos o FLIP VERTICAL em relação ao “eixo horizontal Y=SCALE/2”.
            #      Se um ponto tem coordenada y_original em [0 .. SCALE], ele será levado a y' = SCALE - y_original.
            #      Para isso, basta:
            flipped = transformed.scaled(1, -1)
            flipped = flipped.translated(complex(0, SCALE))

            # 3.7) Extrai o atributo “d” do path flipado, em uma só linha (sem quebras)
            final_d = flipped.d().replace("\n", "").strip()

            # 3.8) Grava no Dart como:
            #      static const shapeLetterA = 'M...Z...';
            dart_f.write(f"  static const shapeLetter{char} = '{final_d}';\n")
            print(f"[shape.py] Gerado: shapeLetter{char}")

        dart_f.write("\n}\n")

    print(f"\n✅ Arquivo Dart gerado: {OUTPUT_DART}")


if __name__ == "__main__":
    main()
