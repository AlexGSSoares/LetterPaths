# svg_utils.py

import math
from svgpathtools import parse_path, Path


def get_global_bbox(path: Path):
    """
    Retorna (x_min, x_max, y_min, y_max) de um svgpathtools.Path,
    percorrendo todos os pontos de controle (bpoints) de cada segmento.
    """
    xs, ys = [], []
    for seg in path:
        for pt in seg.bpoints():
            xs.append(pt.real)
            ys.append(pt.imag)
    return min(xs), max(xs), min(ys), max(ys)


def normalize_glyph_path(raw_commands: str, target_size: float):
    """
    1) Converte raw_commands (string vinda do SVGPathPen) para svgpathtools.Path.
    2) Inverte verticalmente (Y → -Y) e “encosta” o mínimo em Y=0.
    3) Calcula escala uniforme para caber em [0..target_size] × [0..target_size].
    4) Centraliza o contorno nesse quadrado de lado target_size.

    Retorna:
      - transformed: svgpathtools.Path já flipado, escalonado e centralizado.
      - scale (float): fator de escala usado.
      - tx (float): translado em X (após escala).
      - ty (float): translado em Y (após escala).
    """
    # 1) Converte raw_commands para Path
    original = parse_path(raw_commands)

    # 2) Flip vertical + alinhar “pé” em y = 0
    x_min, x_max, y_min, y_max = get_global_bbox(original)
    flipped = original.scaled(1, -1).translated(complex(0, y_min + y_max))

    # 3) Calcular bounding‐box do flipped
    xf_min, xf_max, yf_min, yf_max = get_global_bbox(flipped)
    w = xf_max - xf_min
    h = yf_max - yf_min

    # 4) Escala uniforme para caber em target_size × target_size
    scale = min(target_size / w, target_size / h)

    # 5) Translação para centralizar no quadrado
    tx = -xf_min * scale + (target_size - w * scale) / 2
    ty = -yf_min * scale + (target_size - h * scale) / 2

    # 6) Constrói Path final: escalona cada segmento e depois translada
    transformed = Path(*(seg.scaled(scale).translated(complex(tx, ty)) for seg in flipped))

    return transformed, scale, tx, ty
