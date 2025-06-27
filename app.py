import streamlit as st
import ee
import geemap.foliumap as geemap
import geopandas as gpd
import pandas as pd
import datetime

# Inicializar Earth Engine
ee.Initialize()

# =======================
# Função para carregar GeoJSON
# =======================


def load_geojson(geojson_path):
    gdf = gpd.read_file(geojson_path)
    coords = list(gdf.geometry[0].exterior.coords)
    return ee.Geometry.Polygon([coords])
# =======================
# Função para criar grades 800m x 800m
# =======================


def create_grid(geometry, cell_width=800, cell_height=800):
    bounds = geometry.bounds()
    coords = bounds.getInfo()['coordinates'][0]

    lons = [c[0] for c in coords]
    lats = [c[1] for c in coords]

    lon_min, lon_max = min(lons), max(lons)
    lat_min, lat_max = min(lats), max(lats)

    grids = []
    dx = cell_width / 111320  # graus
    dy = cell_height / 110540  # graus

    y = lat_min
    while y < lat_max:
        x = lon_min
        while x < lon_max:
            cell = ee.Geometry.Rectangle([x, y, x + dx, y + dy])
            if geometry.intersects(cell, 1).getInfo():
                grids.append(cell)
            x += dx
        y += dy

    return grids

# =======================
# Função para NDVI e estatísticas
# =======================


def get_ndvi_and_vegetation_stats(image, geometry):
    ndvi = image.normalizedDifference(['B8', 'B4']).rename('NDVI')
    ndvi_mask = ndvi.gt(0.3)  # NDVI > 0.3 = vegetação
    vegetation_area = ndvi_mask.multiply(ee.Image.pixelArea())

    total_area = ee.Image.pixelArea().reduceRegion(
        reducer=ee.Reducer.sum(),
        geometry=geometry,
        scale=10,
        maxPixels=1e13
    ).get('area')

    green_area = vegetation_area.reduceRegion(
        reducer=ee.Reducer.sum(),
        geometry=geometry,
        scale=10,
        maxPixels=1e13
    ).get('NDVI')

    total_area_val = total_area.getInfo()
    green_area_val = green_area.getInfo()

    pct = (green_area_val / total_area_val) * 100 if total_area_val > 0 else 0

    return ndvi, ndvi_mask, round(pct, 2)


# =======================
# Streamlit App
# =======================
st.set_page_config(layout='wide')
st.title("🌱 Análise de Vegetação com NDVI e GEE")

# Upload do arquivo GeoJSON
geojson_file = st.file_uploader(
    "📁 Envie um arquivo GeoJSON com o polígono:", type=["geojson"])

if geojson_file:
    geometry = load_geojson(geojson_file)

    # Mostrar mapa com polígono
    st.subheader("🗺️ Mapa da área de estudo")
    Map = geemap.Map(center=[0, 0], zoom=10)
    Map.addLayer(geometry, {'color': 'blue'}, "Área do polígono")
    Map.centerObject(geometry, 12)
    Map.to_streamlit(height=500)

    # Parâmetros de datas
    st.subheader("📅 Escolha a data para imagem Sentinel-2")
    start_date = st.date_input("Data inicial", datetime.date(2023, 7, 1))
    end_date = st.date_input("Data final", datetime.date(2023, 7, 31))

    # Botão para processar
    if st.button("🔍 Processar NDVI e Segmentação"):
        st.info("⏳ Processando, isso pode levar alguns segundos...")

        # Coleta de imagem Sentinel-2
        image = (ee.ImageCollection("COPERNICUS/S2_HARMONIZED")
                 .filterBounds(geometry)
                 .filterDate(str(start_date), str(end_date))
                 .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 10))
                 .median())

        # NDVI total da área original
        ndvi, ndvi_mask, total_pct = get_ndvi_and_vegetation_stats(
            image, geometry)

        # Geração das grades
        grids = create_grid(geometry)
        data = []

        st.subheader("📊 Porcentagem de vegetação por grade")

        # Mostrar mapa com cores por grade
        grid_map = geemap.Map()
        grid_map.addLayer(
            image, {'bands': ['B4', 'B3', 'B2'], 'min': 0, 'max': 3000}, "Imagem RGB")
        grid_map.addLayer(ndvi_mask.selfMask(), {
                          'palette': ['00FF00']}, "Vegetação")

        for i, grid in enumerate(grids):
            _, _, pct = get_ndvi_and_vegetation_stats(image, grid)
            data.append({'Grade': i + 1, 'Porcentagem de Vegetação (%)': pct})
            grid_map.addLayer(
                grid, {'color': 'green' if pct > 50 else 'orange'}, f'Grade {i+1}')

        grid_map.centerObject(geometry, 13)
        grid_map.to_streamlit(height=500)

        st.dataframe(pd.DataFrame(data))

        st.subheader("🌍 NDVI da área total")
        ndvi_map = geemap.Map()
        ndvi_map.addLayer(
            ndvi, {'min': 0, 'max': 1, 'palette': ['white', 'green']}, "NDVI")
        ndvi_map.addLayer(ndvi_mask.selfMask(), {
                          'palette': ['00FF00']}, "Máscara Vegetação")
        ndvi_map.centerObject(geometry, 13)
        ndvi_map.to_streamlit(height=500)

        st.success(
            f"✅ Porcentagem de vegetação na área total: **{total_pct}%**")

else:
    st.warning("👆 Envie um arquivo GeoJSON válido para começar.")
