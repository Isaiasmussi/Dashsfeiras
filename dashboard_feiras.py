import pandas as pd
import streamlit as st
import folium
from streamlit_folium import st_folium
from geopy.geocoders import Nominatim
from geopy.extra.rate_limiter import RateLimiter

# --- Configuração da Página do Streamlit ---
st.set_page_config(
    page_title="Dashboard de Feiras Agro",
    page_icon="🗺️",
    layout="wide"
)

st.title("🗺️ Dashboard de Feiras e Eventos Agro")

# --- Funções de Processamento de Dados ---

@st.cache_data # Cache para não reprocessar os arquivos a cada interação
def carregar_e_limpar_dados(caminho_arquivo):
    """
    Carrega o CSV original e faz toda a limpeza necessária.
    """
    df = pd.read_csv(caminho_arquivo)
    
    # 1. Limpeza dos dados
    cols_to_drop = ['Vendedor', 'Cobert', 'Viagem']
    df_cleaned = df.drop(columns=cols_to_drop, errors='ignore') # errors='ignore' evita erro se as colunas já foram removidas
    df_cleaned = df_cleaned.dropna(subset=['Evento'])
    df_cleaned['Mês'] = df_cleaned['Mês'].fillna(method='ffill')
    
    # 2. Criação da coluna 'Localizacao' (A correção principal está aqui!)
    df_cleaned['Localizacao'] = df_cleaned['Cidade'] + ', ' + df_cleaned['UF']
    
    # 3. Renomeia colunas
    df_cleaned.rename(columns={
        'Mês': 'Mes',
        'Evento': 'Nome',
        'Foco': 'Segmento',
        'Data': 'Datas'
    }, inplace=True)
    
    return df_cleaned.reset_index(drop=True)


@st.cache_data # Cache para não refazer a geocodificação
def geocode_dataframe(df):
    """
    Adiciona colunas de Latitude e Longitude a um DataFrame.
    """
    # A função de geocodificação continua a mesma...
    geolocator = Nominatim(user_agent="streamlit-app-studio-data-v2")
    geocode = RateLimiter(geolocator.geocode, min_delay_seconds=1)

    location_coords = {}
    
    st.info("Iniciando geocodificação... Isso só será executado na primeira vez. Pode levar um minuto.")
    progress_bar = st.progress(0)
    unique_locations = df['Localizacao'].unique()
    total_locations = len(unique_locations)
    
    for i, location in enumerate(unique_locations):
        try:
            location_data = geocode(location)
            if location_data:
                location_coords[location] = (location_data.latitude, location_data.longitude)
            else:
                location_coords[location] = (None, None)
        except Exception:
            location_coords[location] = (None, None)
        progress_bar.progress((i + 1) / total_locations)
    
    df['Latitude'] = df['Localizacao'].map(lambda x: location_coords.get(x)[0] if location_coords.get(x) else None)
    df['Longitude'] = df['Localizacao'].map(lambda x: location_coords.get(x)[1] if location_coords.get(x) else None)
    
    st.success("Geocodificação concluída!")
    return df

# --- Execução Principal do Dashboard ---

# Defina o nome do seu arquivo CSV original aqui
NOME_ARQUIVO_ORIGINAL = "Feiras Agro para impressão-2.xlsx - Tabela_de_Feiras_Agro_2025.csv"

try:
    # 1. Carrega e limpa os dados do arquivo original
    df_limpo = carregar_e_limpar_dados(NOME_ARQUIVO_ORIGINAL)

    # 2. Executa a geocodificação
    df_geocoded = geocode_dataframe(df_limpo.copy())

    # Remove eventos que não puderam ser localizados para o mapa
    df_mapa = df_geocoded.dropna(subset=['Latitude', 'Longitude'])

    # --- Layout do Dashboard ---
    col1, col2 = st.columns([3, 2])

    with col1:
        st.subheader("Mapa Interativo dos Eventos")
        map_center = [-14.2350, -51.9253]
        m = folium.Map(location=map_center, zoom_start=4)

        for idx, row in df_mapa.iterrows():
            popup_text = f"<b>Evento:</b> {row['Nome']}<br><b>Data:</b> {row['Datas']}<br><b>Segmento:</b> {row['Segmento']}"
            folium.Marker(
                location=[row['Latitude'], row['Longitude']],
                popup=folium.Popup(popup_text, max_width=300),
                tooltip=row['Nome']
            ).add_to(m)
        st_folium(m, use_container_width=True)

    with col2:
        st.subheader("Tabela de Dados")
        df_display = df_geocoded[['Nome', 'Datas', 'Segmento', 'Cidade', 'UF']]
        st.dataframe(df_display, use_container_width=True, height=500)

except FileNotFoundError:
    st.error(f"Erro: O arquivo '{NOME_ARQUIVO_ORIGINAL}' não foi encontrado. Certifique-se de que ele está na mesma pasta que o script do dashboard.")
except Exception as e:
    st.error(f"Ocorreu um erro inesperado: {e}")
