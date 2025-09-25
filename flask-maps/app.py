#!/usr/bin/env python3
# app.py — Flask + Mapa genérico do Brasil (Folium + geobr)
import os
from flask import Flask, render_template, render_template_string, jsonify, request
from dotenv import load_dotenv

# Carrega .env
load_dotenv()

# Imports de bibliotecas públicas
import folium
import geopandas as gpd
import pandas as pd
import requests

# Hubs/SDKs e libs brasileiras citadas
import DadosAbertosBrasil  # hub comunitário
try:
    from dados_gov_sdk import ApiClient, Settings
except Exception:
    ApiClient = None
    Settings = None
import brazilian_data  # noqa

# Bacen
import bcb
import sgs as sgs_bcb

# IBGE / SIDRA
import sidrapy

# Geo oficial
import geobr

# Saúde pública
import pysus  # noqa

# CKAN
import ckanapi

# Integrações (namespace pacote)
from integrations import transparency_headers, transparencia_get, brasilapi_get  # noqa

# Base paths (permite override via .env)
DATA_ROOT = os.getenv("MAPS_DATA_ROOT", "/opt/mapas-dev")
DATA_DIR = os.path.join(DATA_ROOT, "Territorios_e_IDF_Pres_Prudente")
TERR_SHP = os.path.join(DATA_DIR, "Territorios_SAS_PP (2010).shp")
IDF_TAB = os.path.join(DATA_DIR, "IDF (geocodificados).TAB")

app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev-secret-key")

@app.route("/health")
def health():
    return jsonify({"status": "ok"}), 200

@app.route("/")
def index():
    return render_template(
        "base.html",
        title="Flask Maps – Brasil",
        content="""
        <h2>Bem-vindo</h2>
        <p>Ambiente Flask pronto com bibliotecas brasileiras públicas instaladas.</p>
        <ul>
          <li><a href="/mapa/brasil">Mapa do Brasil (Folium + GeoBR)</a></li>
          <li><a href="/mapa/territorios-idf">Territórios (SAS 2010) + IDF (geocodificado)</a></li>
          <li><a href="/api/brasilapi/cep/01311000">Exemplo BrasilAPI (CEP)</a></li>
          <li><a href="/api/sgs/serie/433?last=10">Exemplo SGS (Bacen) – série 433 (Selic)</a></li>
        </ul>
        <h3>APIs & bibliotecas disponíveis</h3>
        <pre style="white-space: pre-wrap; font-size: 0.95em;">
        - DadosAbertosBrasil, dados-gov-sdk, brazilian-data
        - python-bcb (bcb), sgs (SGS Bacen)
        - sidrapy (IBGE/SIDRA), geobr (geodados oficiais), PySUS (DATASUS)
        - ckanapi (portais CKAN, ex.: TSE/ISP-RJ)
        - requests (BrasilAPI, Portal da Transparência, Brasil.IO, RENAEST, etc.)
        </pre>
        """,
    )

@app.route("/mapa/brasil")
def mapa_brasil():
    gdf = geobr.read_state(year=2020)
    m = folium.Map(location=[-14.235004, -51.92528], zoom_start=4, control_scale=True)
    folium.GeoJson(
        gdf.to_json(),
        name="Estados (IBGE/GeoBR)",
        tooltip=folium.GeoJsonTooltip(
            fields=["name_state", "abbrev_state"],
            aliases=["Estado", "UF"],
            sticky=False
        ),
    ).add_to(m)
    folium.LayerControl().add_to(m)
    html = m._repr_html_()
    return render_template_string(
        """{% extends 'base.html' %}
           {% block content %}
             <h2>Mapa do Brasil</h2>
             <div>{{ folium_map|safe }}</div>
           {% endblock %}""",
        folium_map=html,
    )

def _pick_fields_exist(df, candidates, fallback_n=2):
    cols_lower = {c.lower(): c for c in df.columns}
    chosen = []
    for c in candidates:
        cl = c.lower()
        if cl in cols_lower:
            chosen.append(cols_lower[cl])
    if not chosen:
        chosen = [c for c in df.columns if c != getattr(df, "geometry", pd.Series("geometry")).name][:fallback_n]
    return chosen

def _pick_idf_column(df):
    preferred = ["IDF", "IDF_GERAL", "IDF_TOTAL", "IDFG", "IDFGERAL"]
    for name in preferred:
        for c in df.columns:
            if c.lower() == name.lower():
                return c
    num_cols = df.select_dtypes(include="number").columns.tolist()
    for c in num_cols:
        s = df[c].dropna()
        if len(s) and s.min() >= 0 and s.max() <= 1:
            return c
    return None

@app.route("/mapa/territorios-idf")
def mapa_territorios_idf():
    """
    Visualiza:
      - Polígonos: Territórios SAS (2010) (Shapefile)
      - IDF geocodificado (MapInfo TAB/MAP)
    Ambos esperados em: DATA_ROOT/Territorios_e_IDF_Pres_Prudente/
    """
    if not os.path.exists(TERR_SHP):
        raise RuntimeError(f"Shapefile não encontrado: {TERR_SHP}")
    if not os.path.exists(IDF_TAB):
        raise RuntimeError(f"MapInfo TAB não encontrado: {IDF_TAB}")

    terr = gpd.read_file(TERR_SHP)
    idf = gpd.read_file(IDF_TAB)  # requer .MAP presente (no mesmo diretório)

    # Harmonizar CRS em WGS84
    if terr.crs is not None and terr.crs.to_string() != "EPSG:4326":
        terr = terr.to_crs(epsg=4326)
    if hasattr(idf, "crs") and idf.crs is not None and idf.crs.to_string() != "EPSG:4326":
        idf = idf.to_crs(epsg=4326)

    # Centro do envelope dos territórios
    if hasattr(terr, "total_bounds"):
        minx, miny, maxx, maxy = terr.total_bounds
        center = [(miny + maxy) / 2.0, (minx + maxx) / 2.0]
        zoom = 12
    else:
        center = [-22.121, -51.393]
        zoom = 11

    m = folium.Map(location=center, zoom_start=zoom, control_scale=True)

    # --- Territórios (polígonos)
    terr_fields = _pick_fields_exist(terr, ["NOME", "NOME_TERR", "TERRITORIO", "DESCR"])
    terr_gj = folium.GeoJson(
        terr.to_json(),
        name="Territórios (SAS 2010)",
        style_function=lambda feat: {
            "fillColor": "#4CAF50",
            "color": "#1B5E20",
            "weight": 1,
            "fillOpacity": 0.25,
        },
        tooltip=folium.GeoJsonTooltip(fields=terr_fields, aliases=terr_fields, sticky=False),
        highlight_function=lambda feat: {"weight": 3, "color": "#2E7D32"},
    )
    terr_gj.add_to(m)

    # --- IDF (pontos/polígonos) com coloração por IDF (0..1) quando possível
    idf_col = _pick_idf_column(idf)
    try:
        import branca.colormap as cm
        cmap = cm.LinearColormap(["#440154", "#21908C", "#FDE725"], vmin=0, vmax=1)
    except Exception:
        cmap = None

    if idf_col is None:
        idf_fields = _pick_fields_exist(idf, ["ID", "COD", "NOME"], fallback_n=4)
        folium.GeoJson(
            idf.to_json(),
            name="IDF (atributos)",
            tooltip=folium.GeoJsonTooltip(fields=idf_fields, aliases=idf_fields, sticky=False),
        ).add_to(m)
    else:
        def style_fun(feat):
            v = feat["properties"].get(idf_col)
            color = "#1976D2"
            fill = "#90CAF9"
            if cmap and isinstance(v, (int, float)):
                color = cmap(v)
                fill = cmap(v)
            return {
                "fillColor": fill,
                "color": color,
                "weight": 1,
                "fillOpacity": 0.6,
            }

        idf_fields = _pick_fields_exist(idf, [idf_col], fallback_n=4)
        folium.GeoJson(
            idf.to_json(),
            name=f"IDF (coluna: {idf_col})",
            style_function=style_fun,
            tooltip=folium.GeoJsonTooltip(fields=idf_fields, aliases=idf_fields, sticky=False),
            highlight_function=lambda feat: {"weight": 3, "color": "#0D47A1"},
        ).add_to(m)

        if cmap:
            cmap.caption = f"IDF (0 → 1) — campo '{idf_col}'"
            cmap.add_to(m)

    folium.LayerControl(collapsed=False).add_to(m)

    html = m._repr_html_()
    return render_template_string(
        """{% extends 'base.html' %}
           {% block content %}
             <h2>Territórios (SAS 2010) + IDF geocodificado</h2>
             <p>Dados locais em: <code>{{ data_dir }}</code></p>
             <div>{{ folium_map|safe }}</div>
           {% endblock %}""",
        folium_map=html,
        data_dir=DATA_DIR,
    )

@app.route("/api/brasilapi/cep/<cep>")
def api_brasilapi_cep(cep: str):
    try:
        data = brasilapi_get(f"cep/v1/{cep}")
        return jsonify(data), 200
    except requests.HTTPError as e:
        return jsonify({"error": "upstream_error", "detail": str(e)}), 502
    except Exception as e:
        return jsonify({"error": "internal_error", "detail": str(e)}), 500

@app.route("/api/sgs/serie/<int:codigo>")
def api_sgs_serie(codigo: int):
    try:
        last = int(request.args.get("last", "1"))
        series = sgs_bcb.time_serie(codigo, last=last)
        items = [{"date": k, "value": v} for k, v in series.items()]
        items.sort(key=lambda x: x["date"])
        return jsonify({"code": codigo, "count": len(items), "data": items}), 200
    except Exception as e:
        return jsonify({"error": "internal_error", "detail": str(e)}), 500

if __name__ == "__main__":
    # Dev local:
    # FLASK_ENV=development python app.py
    app.run(host="0.0.0.0", port=8000, debug=True)
