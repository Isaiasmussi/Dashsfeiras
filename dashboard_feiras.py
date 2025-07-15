import os
import pandas as pd
import streamlit as st
import folium
from streamlit_folium import st_folium
from geopy.geocoders import Nominatim
from geopy.extra.rate_limiter import RateLimiter

# --- FERRAMENTA DE DIAGNÓSTICO ---
# Este bloco ajuda a ver o que o Python está a ler.
st.subheader("🕵️ Ferramenta de Diagnóstico")
try:
    st.write(f"**Pasta atual que o script está a ler:** `{os.getcwd()}`")
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
@st.cache_data
def carregar_e_limpar_dados(caminho_arquivo):
    """
    Carrega o arquivo CSV, faz a limpeza e prepara para o dashboard.
    """
    # ALTERAÇÃO FINAL: Tornamos o leitor mais robusto para ignorar linhas com erros de formatação.
    df = pd.read_csv(caminho_arquivo, encoding='latin-1', on_bad_lines='skip', sep=',')
    
    # Remove colunas desnecessárias
    cols_to_drop = ['Vendedor', 'Cobert', 'Viagem']
    df_cleaned = df.drop(columns=cols_to_drop, errors='ignore')
    
    # Limpeza e formatação
    df_cleaned = df_cleaned.dropna(subset=['Evento'])
    df_cleaned['Mês'] = df_cleaned['Mês'].ffill()
    df_cleaned['Localizacao'] = df_cleaned['Cidade'] + ', ' + df_cleaned['UF']
    
    # Renomeia colunas
    df_cleaned.rename(columns={
        'Mês': 'Mes', 
        'Evento': 'Nome', 
        'Foco': 'Segmento', 
        'Data': 'Datas'
    }, inplace=True)
    
    return df_cleaned.reset_index(drop=True)

@st.cache_data
def geocode_dataframe(df):
    """
    Adiciona colunas de Latitude e Longitude ao DataFrame.
    """
    geolocator = Nominatim(user_agent="streamlit-app-studio-data-v4") # user_agent atualizado
    geocode = RateLimiter(geolocator.geocode, min_delay_seconds=1)
    location_coords = {}
    
    with st.spinner("A iniciar geocodificação... Isto só será executado na primeira vez e pode levar um minuto."):
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
            
    df['Latitude'] = df['Localizacao'].map(lambda x: location_coords.get(x, (None, None))[0])
    df['Longitude'] = df['Localizacao'].map(lambda x: location_coords.get(x, (None, None))[1])
    return df

# --- EXECUÇÃO PRINCIPAL DO DASHBOARD ---
NOME_ARQUIVO = "dados.csv"

try:
    df_limpo = carregar_e_limpar_dados(NOME_ARQUIVO)
    
    if df_limpo.empty:
        st.error("O DataFrame está vazio após a limpeza. Verifique o conteúdo do ficheiro 'dados.csv'.")
    else:
        df_geocoded = geocode_dataframe(df_limpo.copy())
        df_mapa = df_geocoded.dropna(subset=['Latitude', 'Longitude'])

        # --- MONTAGEM DO LAYOUT ---
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
    st.error(f"ERRO CRÍTICO: O Python não encontrou o ficheiro '{NOME_ARQUIVO}'.")
    st.warning("Verifique na lista da 'Ferramenta de Diagnóstico' (acima) se o nome 'dados.csv' aparece.")
except Exception as e:
    st.error(f"Ocorreu um erro inesperado durante a execução: {e}")

