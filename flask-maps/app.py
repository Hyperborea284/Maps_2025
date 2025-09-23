#!/usr/bin/env python3
# app.py — Flask + Mapa do Brasil (Folium + geobr)
import os
from flask import Flask, render_template, render_template_string
from dotenv import load_dotenv, find_dotenv

# carrega .env da raiz do projeto (procura automaticamente para cima)
load_dotenv(find_dotenv())

import folium
import geopandas as gpd
import pandas as pd
import requests

import DadosAbertosBrasil  # hub comunitário

try:
    from dados_gov_sdk import ApiClient, Settings
except Exception:
    ApiClient = None
    Settings = None

import brazilian_data  # noqa

import bcb  # python-bcb
import sgs as sgs_bcb
import sidrapy
import geobr
import pysus  # noqa
import ckanapi

app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev-secret-key")

@app.route("/")
def index():
    return render_template("base.html", title="Flask Maps – Brasil",
                           content="""
                           <h2>Bem-vindo</h2>
                           <p>Ambiente Flask pronto com bibliotecas brasileiras públicas instaladas.</p>
                           <ul>
                             <li><a href="/mapa/brasil">Mapa do Brasil (Folium + GeoBR)</a></li>
                           </ul>
                           <h3>APIs & bibliotecas disponíveis</h3>
                           <pre style="white-space: pre-wrap; font-size: 0.95em;">
                           - DadosAbertosBrasil, dados-gov-sdk, brazilian-data
                           - python-bcb (bcb), sgs (SGS Bacen)
                           - sidrapy (IBGE/SIDRA), geobr (geodados oficiais), PySUS (DATASUS)
                           - ckanapi (portais CKAN), requests (BrasilAPI, Portal da Transparência, etc.)
                           </pre>
                           """)

@app.route("/mapa/brasil")
def mapa_brasil():
    gdf = geobr.read_state(year=2020)
    m = folium.Map(location=[-14.235004, -51.92528], zoom_start=4, control_scale=True)
    folium.GeoJson(
        gdf.to_json(),
        name="Estados (IBGE/GeoBR)",
        tooltip=folium.GeoJsonTooltip(fields=["name_state", "abbrev_state"],
                                      aliases=["Estado", "UF"], sticky=False)
    ).add_to(m)
    folium.LayerControl().add_to(m)
    html = m._repr_html_()
    return render_template_string(
        """{% extends 'base.html' %}
           {% block content %}
             <h2>Mapa do Brasil</h2>
             <div>{{ folium_map|safe }}</div>
           {% endblock %}""",
        folium_map=html
    )

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)
