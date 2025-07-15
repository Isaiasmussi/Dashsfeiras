import os
import pandas as pd
import streamlit as st
import folium
from streamlit_folium import st_folium
from geopy.geocoders import Nominatim
from geopy.extra.rate_limiter import RateLimiter

# --- FERRAMENTA DE DIAGNÓSTICO ---
# Este bloco nos ajuda a ver o que o Python está enxergando.
st.subheader("🕵️ Ferramenta de Diagnóstico")
try:
    # Mostra a pasta de trabalho atual
    st.write(f"**Pasta atual que o script está lendo:** `{os.getcwd()}`")
    # Lista os arquivos encontrados na pasta
    st.write("**Arquivos encontrados nesta pasta:**")
    files_in_directory = os.listdir('.')
    st.write(files_in_directory)
except Exception as e:
    st.error(f"Não foi possível listar os arquivos: {e}")
st.markdown("---")
# --- FIM DO DIAGNÓSTICO ---


# --- CONFIGURAÇÃO DA PÁGINA ---
st.title("🗺️ Dashboard de Feiras e Eventos Agro")

# --- FUNÇÕES DE PROCESSAMENTO ---
# O cache evita reprocessar os dados a cada interação, deixando o app mais rápido.
@st.cache_data
def carregar_e_limpar_dados(caminho_arquivo):
    """
    Carrega o arquivo CSV, faz a limpeza e prepara para o dashboard.
    """
    df = pd.read_csv(caminho_arquivo)
    
    # Remove colunas desnecessárias (errors='ignore' evita erro se já não existirem)
    cols_to_drop = ['Vendedor', 'Cobert', 'Viagem']
    df_cleaned = df.drop(columns=cols_to_drop, errors='ignore')
    
    # Limpeza e formatação
    df_cleaned = df_cleaned.dropna(subset=['Evento'])
    df_cleaned['Mês'] = df_cleaned['Mês'].ffill() # Preenche os meses para todas as linhas
    df_cleaned['Localizacao'] = df_cleaned['Cidade'] + ', ' + df_cleaned['UF']
    
    # Renomeia colunas para nomes mais amigáveis
    df_cleaned.rename(columns={
        'Mês': 'Mes', 
        'Evento': 'Nome', 
        'Foco': 'Segmento', 
        'Data': 'Datas'
    }, inplace=True)
    
    return df_cleaned.reset_index(drop=True)

# O cache evita refazer a geocodificação, que é um processo lento.
@st.cache_data
def geocode_dataframe(df):
    """
    Adiciona colunas de Latitude e Longitude ao DataFrame.
    """
    geolocator = Nominatim(user_agent="streamlit-app-studio-data-v3")
    geocode = RateLimiter(geolocator.geocode, min_delay_seconds=1)
    location_coords = {}
    
    # Mostra uma mensagem amigável enquanto o processo demorado acontece
    with st.spinner("Iniciando geocodificação... Isso só será executado na primeira vez e pode levar um minuto."):
        progress_bar = st.progress(0)
        unique_locations = df['Localizacao'].unique()
        total_locations = len(unique_locations)
        
        for i, location in enumerate(unique_locations):
            try:
                location_data = geocode(location)
                location_coords[location] = (location_data.latitude, location_data.longitude) if location_data else (None, None)
            except Exception:
                location_coords[location] = (None, None)
            progress_bar.progress((i + 1) / total_locations)
            
    # Mapeia as coordenadas encontradas para as colunas do DataFrame
    df['Latitude'] = df['Localizacao'].map(lambda x: location_coords.get(x, (None, None))[0])
    df['Longitude'] = df['Localizacao'].map(lambda x: location_coords.get(x, (None, None))[1])
    return df

# --- EXECUÇÃO PRINCIPAL DO DASHBOARD ---
NOME_ARQUIVO = "dados.csv" # Nome do arquivo de dados que está no GitHub

try:
    # 1. Carrega e limpa os dados
    df_limpo = carregar_e_limpar_dados(NOME_ARQUIVO)
    
    # 2. Geocodifica os dados
    df_geocoded = geocode_dataframe(df_limpo.copy())
    
    # 3. Prepara os dados para o mapa (remove linhas sem coordenadas)
    df_mapa = df_geocoded.dropna(subset=['Latitude', 'Longitude'])

    # --- MONTAGEM DO LAYOUT ---
    col1, col2 = st.columns([3, 2]) # Coluna do mapa 3x mais larga que a da tabela

    with col1:
        st.subheader("Mapa Interativo dos Eventos")
        map_center = [-14.2350, -51.9253] # Centro do Brasil
        m = folium.Map(location=map_center, zoom_start=4)

        # Adiciona um pino no mapa para cada evento
        for idx, row in df_mapa.iterrows():
            popup_text = f"<b>Evento:</b> {row['Nome']}<br><b>Data:</b> {row['Datas']}<br><b>Segmento:</b> {row['Segmento']}"
            folium.Marker(
                location=[row['Latitude'], row['Longitude']],
                popup=folium.Popup(popup_text, max_width=300),
                tooltip=row['Nome'] # Texto que aparece ao passar o mouse
            ).add_to(m)
            
        # Exibe o mapa no Streamlit
        st_folium(m, use_container_width=True)

    with col2:
        st.subheader("Tabela de Dados")
        # Seleciona e exibe as colunas mais importantes
        df_display = df_geocoded[['Nome', 'Datas', 'Segmento', 'Cidade', 'UF']]
        st.dataframe(df_display, use_container_width=True, height=500)

except FileNotFoundError:
    st.error(f"ERRO CRÍTICO: O Python não encontrou o arquivo '{NOME_ARQUIVO}'.")
    st.warning("Verifique na lista da 'Ferramenta de Diagnóstico' (acima) se o nome 'dados.csv' aparece.")
    st.info("Se não aparecer, significa que o arquivo não foi enviado para o GitHub ou o nome está incorreto.")
except Exception as e:
    st.error(f"Ocorreu um erro inesperado durante a execução: {e}")

