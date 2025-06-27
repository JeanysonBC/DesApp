# === Célula 1: instalar bibliotecas necessárias ===
pip install --quiet \
  streamlit \
  folium \
  geopandas \
  geobr \
  shapely==1.8.5 \
  streamlit-folium \
  pyngrok

import streamlit as st
import rasterio
import numpy as np
import folium
from streamlit_folium import st_folium
from geobr import read_municipality

st.title("Dashboard de Desmatamento")

# URL direta para download do arquivo TIF no Google Drive
tif_url = "https://drive.google.com/uc?export=download&id=1ElNwj-3RWUyUazCth2kiRMiyuKDVHR1C"

st.markdown(
    "**Dados de desmatamento (TIF):** "
    f"[Clique aqui para baixar]({tif_url})"
)

if tif_url:
    try:
        with rasterio.open(tif_url) as src:
            data = src.read(1)
            bounds = src.bounds
            m = folium.Map(
                location=[
                    (bounds.top + bounds.bottom) / 2,
                    (bounds.left + bounds.right) / 2
                ],
                zoom_start=8
            )
            folium.raster_layers.ImageOverlay(
                image=data,
                bounds=[[bounds.bottom, bounds.left], [bounds.top, bounds.right]],
                opacity=0.6
            ).add_to(m)
            st_folium(m, width=700, height=500)
    except Exception as e:
        st.error(f"Erro ao carregar o TIF: {e}")

st.header("Municípios - Exemplo de geobr")
try:
    gdf = read_municipality(code_muni=1100015)
    st.write(gdf.head())
except Exception as e:
    st.warning(f"Não foi possível carregar os municípios: {e}")
