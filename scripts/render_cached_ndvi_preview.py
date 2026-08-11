#!/usr/bin/env python3
# ruff: noqa: E501, RUF001
"""Render the checksummed cached Sentinel NDVI crop as a self-contained report."""

from __future__ import annotations

import hashlib
import html
import json
import struct
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIR = (
    ROOT
    / "data/processed/sentinel/aef56900-9470-45a5-8fb5-b142994f03e9"
    / "685d33f38e064428661e9c60c6acb53ee4a4e38f9a4b3baf72a4081e5b671d37"
)
SOURCE_TIFF = SOURCE_DIR / "ndvi.tif"
SOURCE_METADATA = SOURCE_DIR / "userdata.json"
OUTPUT_HTML = ROOT / "docs/previews/sentinel-ndvi-preview.html"
OUTPUT_MANIFEST = ROOT / "data/manifests/sentinel-ndvi-preview.json"

EXPECTED_TIFF_SHA256 = "49a56d955b5f47cfb1c009004a0ab7f0515644961f108f7b8a7bac083ccd76dc"
EXPECTED_METADATA_SHA256 = (
    "0f0fff226c03d496fabf5efec1b7972d313167287f18e6dba930aedb97c33f12"
)
PROCESSOR_VERSION = "zenit-cached-ndvi-preview-v1"

TYPE_FORMATS = {2: "c", 3: "H", 4: "I", 11: "f", 12: "d"}
TYPE_SIZES = {2: 1, 3: 2, 4: 4, 11: 4, 12: 8}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_tiff_values(path: Path) -> tuple[int, int, float, list[float]]:
    content = path.read_bytes()
    endian = ">" if content[:2] == b"MM" else "<" if content[:2] == b"II" else None
    if endian is None or struct.unpack(f"{endian}H", content[2:4])[0] != 42:
        raise ValueError("Unsupported TIFF header")
    ifd_offset = struct.unpack(f"{endian}I", content[4:8])[0]
    entry_count = struct.unpack(f"{endian}H", content[ifd_offset : ifd_offset + 2])[0]
    tags: dict[int, tuple[int, int, bytes]] = {}
    for index in range(entry_count):
        offset = ifd_offset + 2 + index * 12
        tag, value_type, count = struct.unpack(
            f"{endian}HHI", content[offset : offset + 8]
        )
        encoded = content[offset + 8 : offset + 12]
        size = TYPE_SIZES.get(value_type, 1) * count
        if size > 4:
            value_offset = struct.unpack(f"{endian}I", encoded)[0]
            encoded = content[value_offset : value_offset + size]
        tags[tag] = (value_type, count, encoded[:size])

    def values(tag: int) -> tuple[object, ...]:
        value_type, count, encoded = tags[tag]
        value_format = TYPE_FORMATS[value_type]
        return struct.unpack(f"{endian}{count}{value_format}", encoded)

    width = int(values(256)[0])
    height = int(values(257)[0])
    bits_per_sample = int(values(258)[0])
    compression = int(values(259)[0])
    samples_per_pixel = int(values(277)[0])
    sample_format = int(values(339)[0])
    if (width, height, bits_per_sample, samples_per_pixel, sample_format) != (
        5,
        11,
        32,
        1,
        3,
    ):
        raise ValueError("Cached raster contract changed")
    if compression not in {8, 32946}:
        raise ValueError("Expected Deflate-compressed TIFF")
    strip_offsets = tuple(int(value) for value in values(273))
    strip_sizes = tuple(int(value) for value in values(279))
    raw = b"".join(
        zlib.decompress(content[offset : offset + size])
        for offset, size in zip(strip_offsets, strip_sizes, strict=True)
    )
    raster_values = list(struct.unpack(f"{endian}{width * height}f", raw))
    nodata_type, nodata_count, nodata_bytes = tags[42113]
    if nodata_type != 2:
        raise ValueError("Expected ASCII GDAL NoData tag")
    nodata = float(nodata_bytes[:nodata_count].rstrip(b"\x00").decode("ascii"))
    return width, height, nodata, raster_values


def ndvi_color(value: float | None) -> str:
    if value is None:
        return "#3f4654"
    if value < 0:
        return "#5d86c2"
    if value < 0.1:
        return "#d9c98a"
    if value < 0.2:
        return "#a8c96a"
    if value < 0.3:
        return "#4d9b50"
    if value < 0.5:
        return "#237a3b"
    return "#0b4f2b"


def grayscale(value: float | None) -> str:
    if value is None:
        return "#3f4654"
    normalized = min(1.0, max(0.0, (value + 0.2) / 0.5))
    channel = round(35 + normalized * 205)
    return f"rgb({channel},{channel},{channel})"


def grid_svg(
    values: list[float | None],
    width: int,
    height: int,
    color_function: object,
    title: str,
) -> str:
    cell_width = 78
    cell_height = 43
    rectangles: list[str] = []
    for row in range(height):
        for column in range(width):
            value = values[row * width + column]
            label = "NoData" if value is None else f"{value:.3f}"
            text_color = "#ffffff" if value is None or value < 0 else "#172119"
            fill = color_function(value)  # type: ignore[operator]
            x = column * cell_width
            y = row * cell_height
            rectangles.append(
                f'<g><title>linha {row + 1}, coluna {column + 1}: {label}</title>'
                f'<rect x="{x}" y="{y}" width="{cell_width}" height="{cell_height}" '
                f'fill="{fill}" stroke="#111827" stroke-width="1"/>'
                f'<text x="{x + cell_width / 2}" y="{y + 27}" text-anchor="middle" '
                f'fill="{text_color}" font-size="13" font-family="ui-monospace, monospace">'
                f"{label}</text></g>"
            )
    return (
        f'<svg role="img" aria-label="{html.escape(title)}" '
        f'viewBox="0 0 {width * cell_width} {height * cell_height}" '
        'xmlns="http://www.w3.org/2000/svg">'
        + "".join(rectangles)
        + "</svg>"
    )


def render() -> tuple[str, dict[str, object]]:
    if sha256(SOURCE_TIFF) != EXPECTED_TIFF_SHA256:
        raise ValueError("Cached NDVI GeoTIFF checksum does not match provenance")
    if sha256(SOURCE_METADATA) != EXPECTED_METADATA_SHA256:
        raise ValueError("Cached Sentinel metadata checksum does not match provenance")
    width, height, nodata, raster = read_tiff_values(SOURCE_TIFF)
    display_values = [None if value == nodata else value for value in raster]
    valid = [value for value in display_values if value is not None]
    metadata = json.loads(SOURCE_METADATA.read_text(encoding="utf-8"))
    products = [scene["productId"] for scene in metadata["scenes"]]
    mean = sum(valid) / len(valid)
    numeric_rows = "".join(
        "<tr>"
        + "".join(
            f'<td>{"NoData" if value is None else f"{value:.5f}"}</td>'
            for value in display_values[row * width : (row + 1) * width]
        )
        + "</tr>"
        for row in range(height)
    )
    product_items = "".join(f"<li><code>{html.escape(product)}</code></li>" for product in products)
    report = f"""<!doctype html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>ZENIT · Prévia Sentinel-2 NDVI</title>
  <style>
    :root {{ color-scheme: dark; --bg:#0b1120; --panel:#121b2e; --line:#26344f; --text:#e7edf8; --muted:#9eabc1; --accent:#75c878; }}
    * {{ box-sizing:border-box; }}
    body {{ margin:0; background:radial-gradient(circle at top,#17243a 0,var(--bg) 48%); color:var(--text); font:16px/1.5 system-ui,sans-serif; }}
    main {{ width:min(1180px,calc(100% - 32px)); margin:36px auto 72px; }}
    h1 {{ margin:0 0 6px; font-size:clamp(28px,5vw,48px); }} h2 {{ margin-top:0; }}
    .eyebrow {{ color:var(--accent); font-weight:700; letter-spacing:.12em; text-transform:uppercase; }}
    .badges {{ display:flex; flex-wrap:wrap; gap:8px; margin:18px 0; }}
    .badge {{ border:1px solid var(--line); border-radius:999px; padding:5px 10px; background:#162237; }}
    .warning {{ border-left:4px solid #f2bd4f; background:#2a2419; padding:14px 16px; border-radius:6px; }}
    .panels,.metrics {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(260px,1fr)); gap:16px; margin:22px 0; }}
    .panel,.metric {{ background:color-mix(in srgb,var(--panel) 94%,transparent); border:1px solid var(--line); border-radius:14px; padding:18px; box-shadow:0 16px 35px #0005; }}
    .metric strong {{ display:block; font-size:25px; color:#fff; }} .metric span,.muted {{ color:var(--muted); }}
    svg {{ width:100%; height:auto; display:block; border-radius:8px; overflow:hidden; image-rendering:pixelated; }}
    .legend {{ display:flex; flex-wrap:wrap; gap:10px 14px; margin-top:12px; color:var(--muted); font-size:14px; }}
    .swatch {{ display:inline-block; width:13px; height:13px; margin-right:5px; border-radius:3px; vertical-align:-1px; }}
    table {{ width:100%; border-collapse:collapse; font:13px/1.4 ui-monospace,monospace; }} td {{ border:1px solid var(--line); padding:7px; text-align:right; }}
    code {{ overflow-wrap:anywhere; color:#c6d4ed; }} details {{ margin-top:22px; }} li {{ margin:6px 0; }}
  </style>
</head>
<body><main>
  <div class="eyebrow">ZENIT · evidência satelital real</div>
  <h1>Prévia do recorte Sentinel-2 com filtro NDVI</h1>
  <p class="muted">Aquisição de 29/07/2026 · Sentinel-2 L2A · AOI preparada do segmento de desenvolvimento 195 · resolução de 10 m.</p>
  <div class="badges"><span class="badge">Resposta real do provedor</span><span class="badge">AOI estimada/preparada</span><span class="badge">Não operacional</span><span class="badge">Não oficial</span></div>
  <p class="warning"><strong>O que está e não está aqui:</strong> o cache local contém apenas o raster NDVI, não uma composição RGB/foto normal. NDVI representa resposta espectral da vegetação e <strong>não mede altura</strong>, não confirma necessidade de roçada e não autoriza trabalho de campo.</p>
  <section class="metrics">
    <div class="metric"><span>Grade cacheada</span><strong>{width} × {height}</strong><span>{width * height} pixels; {len(valid)} válidos; {width * height - len(valid)} NoData</span></div>
    <div class="metric"><span>NDVI médio deste GeoTIFF</span><strong>{mean:.4f}</strong><span>mín. {min(valid):.4f} · máx. {max(valid):.4f}</span></div>
    <div class="metric"><span>Qualidade estatística</span><strong>100% válidos</strong><span>na resposta Statistical API; conclusão de domínio: inconclusiva</span></div>
  </section>
  <section class="panels">
    <article class="panel"><h2>Recorte bruto em tons de cinza</h2><p class="muted">Contraste ampliado entre −0,20 e 0,30 apenas para inspeção visual. Passe o cursor sobre uma célula.</p>{grid_svg(display_values, width, height, grayscale, "NDVI bruto em tons de cinza")}</article>
    <article class="panel"><h2>Filtro NDVI por classes</h2><p class="muted">Paleta descritiva; não é uma classificação de altura ou roçada.</p>{grid_svg(display_values, width, height, ndvi_color, "NDVI colorido por classes")}
      <div class="legend"><span><i class="swatch" style="background:#5d86c2"></i>&lt; 0</span><span><i class="swatch" style="background:#d9c98a"></i>0–0,10</span><span><i class="swatch" style="background:#a8c96a"></i>0,10–0,20</span><span><i class="swatch" style="background:#4d9b50"></i>0,20–0,30</span><span><i class="swatch" style="background:#237a3b"></i>≥ 0,30</span><span><i class="swatch" style="background:#3f4654"></i>NoData</span></div>
    </article>
  </section>
  <section class="panel"><h2>Como interpretar</h2><ul><li>NDVI = (infravermelho próximo − vermelho) / (infravermelho próximo + vermelho).</li><li>Valores maiores costumam indicar resposta vegetal mais vigorosa, mas mistura de pavimento, solo e vegetação afeta este recorte estreito.</li><li>A média {mean:.6f} foi calculada dos 35 pixels válidos deste GeoTIFF. A Statistical API registrou 0,097354 em uma execução relacionada, porém distinta; os dois números não devem ser forçados a coincidir.</li><li>O resultado oficial do pipeline continua <strong>inconclusivo</strong>, com recomendação de inspeção e baixa confiança.</li></ul></section>
  <details class="panel"><summary><strong>Valores exatos da grade</strong></summary><p class="muted">Linhas no sentido armazenado pelo GeoTIFF, do topo para baixo.</p><table><tbody>{numeric_rows}</tbody></table></details>
  <details class="panel"><summary><strong>Proveniência técnica</strong></summary><ul><li>GeoTIFF SHA‑256: <code>{EXPECTED_TIFF_SHA256}</code></li><li>Metadata SHA‑256: <code>{EXPECTED_METADATA_SHA256}</code></li><li>Processamento do cache: <code>{html.escape(metadata["processingVersion"])}</code>; serviço <code>{html.escape(metadata["serviceVersion"])}</code>.</li>{product_items}<li>Visualização: <code>{PROCESSOR_VERSION}</code>, sem dependências externas.</li></ul></details>
</main></body></html>"""
    lineage = {
        "artifact_type": "derived_visual_preview",
        "processor_version": PROCESSOR_VERSION,
        "source": {
            "relative_path": str(SOURCE_TIFF.relative_to(ROOT)),
            "sha256": EXPECTED_TIFF_SHA256,
            "metadata_relative_path": str(SOURCE_METADATA.relative_to(ROOT)),
            "metadata_sha256": EXPECTED_METADATA_SHA256,
            "sensor_product": "Sentinel-2 L2A",
            "acquisition_date": "2026-07-29",
            "source_status": "real_provider_response",
            "cache_status": "partially_cached",
        },
        "spatial_scope_status": "prepared_estimated_aoi",
        "result_status": "inconclusive",
        "operational_eligibility": False,
        "eligible_for_model_training": False,
        "eligible_for_official_reporting": False,
        "statistics": {
            "width": width,
            "height": height,
            "valid_pixels": len(valid),
            "nodata_pixels": width * height - len(valid),
            "minimum_ndvi": min(valid),
            "maximum_ndvi": max(valid),
            "mean_ndvi_cached_geotiff": mean,
            "related_statistical_api_mean_ndvi": 0.097354,
        },
    }
    return report, lineage


def main() -> None:
    report, lineage = render()
    OUTPUT_HTML.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_HTML.write_text(report, encoding="utf-8")
    lineage["artifact"] = {
        "relative_path": str(OUTPUT_HTML.relative_to(ROOT)),
        "sha256": sha256(OUTPUT_HTML),
    }
    OUTPUT_MANIFEST.write_text(
        json.dumps(lineage, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(OUTPUT_HTML.relative_to(ROOT))
    print(OUTPUT_MANIFEST.relative_to(ROOT))


if __name__ == "__main__":
    main()
