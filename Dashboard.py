import pandas as pd
import streamlit as st
import folium
from streamlit_folium import st_folium
from geopy.geocoders import Nominatim
from geopy.extra.rate_limiter import RateLimiter
import time

# --- Configuração da Página do Streamlit ---
st.set_page_config(
    page_title="Dashboard de Feiras Agro 2025",
    page_icon="🗺️",
    layout="wide"
)

st.title("🗺️ Dashboard de Feiras e Eventos Agro 2025")

# --- Função de Cache para Geocodificação ---
# O cache evita que o app execute a geocodificação toda vez que é recarregado
@st.cache_data
def geocode_dataframe(df):
    """
    Adiciona colunas de Latitude e Longitude a um DataFrame com base na coluna 'Localizacao'.
    """
    geolocator = Nominatim(user_agent="streamlit-app-studio-data")
    geocode = RateLimiter(geolocator.geocode, min_delay_seconds=1, error_wait_seconds=10, max_retries=2)

    # Dicionário para guardar as coordenadas já encontradas
    location_coords = {}
    latitudes = []
    longitudes = []

    st.info("Iniciando geocodificação... Isso só será executado na primeira vez. Pode levar um minuto.")
    
    progress_bar = st.progress(0)
    total_locations = len(df['Localizacao'].unique())
    
    # Itera sobre as localizações únicas para evitar chamadas repetidas
    for i, location in enumerate(df['Localizacao'].unique()):
        if location not in location_coords:
            try:
                location_data = geocode(location)
                if location_data:
                    location_coords[location] = (location_data.latitude, location_data.longitude)
                else:
                    location_coords[location] = (None, None)
            except Exception as e:
                print(f"Erro ao geocodificar '{location}': {e}")
                location_coords[location] = (None, None)
        progress_bar.progress((i + 1) / total_locations)

    # Mapeia as coordenadas para o DataFrame
    df['Latitude'] = df['Localizacao'].map(lambda x: location_coords.get(x, (None, None))[0])
    df['Longitude'] = df['Localizacao'].map(lambda x: location_coords.get(x, (None, None))[1])
    
    st.success("Geocodificação concluída!")
    return df

# --- Carregamento dos Dados ---
try:
    df = pd.read_csv('feiras_agro_2025_limpo.csv')

    # Executa a geocodificação
    df_geocoded = geocode_dataframe(df.copy()) # Usa uma cópia para evitar problemas de cache

    # Remove eventos que não puderam ser localizados no mapa
    df_mapa = df_geocoded.dropna(subset=['Latitude', 'Longitude'])

    # --- Layout do Dashboard ---
    col1, col2 = st.columns([3, 2]) # Mapa maior, tabela menor

    with col1:
        st.subheader("Mapa Interativo dos Eventos")
        
        # Cria o mapa centrado no Brasil
        map_center = [-14.2350, -51.9253]
        m = folium.Map(location=map_center, zoom_start=4)

        # Adiciona um pino para cada evento
        for idx, row in df_mapa.iterrows():
            popup_text = f"""
            <b>Evento:</b> {row['Nome']}<br>
            <b>Data:</b> {row['Datas']}<br>
            <b>Segmento:</b> {row['Segmento']}
            """
            folium.Marker(
                location=[row['Latitude'], row['Longitude']],
                popup=folium.Popup(popup_text, max_width=300),
                tooltip=row['Nome']
            ).add_to(m)

        # Exibe o mapa no Streamlit
        st_folium(m, use_container_width=True)

    with col2:
        st.subheader("Tabela de Dados")
        
        # Formata a tabela para exibição
        df_display = df_geocoded[['Nome', 'Datas', 'Segmento', 'Cidade', 'UF']]
        st.dataframe(df_display, height=500) # Mostra a tabela com barra de rolagem


except FileNotFoundError:
    st.error("Erro: O arquivo 'feiras_agro_2025_limpo.csv' não foi encontrado. Certifique-se de que ele está na mesma pasta que o script do dashboard.")
