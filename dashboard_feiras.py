import os
import pandas as pd
import streamlit as st
import folium
from streamlit_folium import st_folium
from geopy.geocoders import Nominatim
from geopy.extra.rate_limiter import RateLimiter
import io

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(layout="wide", page_title="Dashboard de Feiras Agro", page_icon="🗺️")
st.title("🗺️ Dashboard de Feiras e Eventos Agro")

# --- FUNÇÕES DE PROCESSAMENTO ---
@st.cache_data
def carregar_e_limpar_dados():
    """
    Carrega os dados diretamente do código, eliminando a necessidade de um arquivo externo.
    """
    # Dados da planilha inseridos diretamente no código
    dados_string = """
    Mês,Evento,Foco,Data,Cidade,UF
    Janeiro,AgroShow Copagril 2026,Agronegócio,14 a 16,Marechal Cândido Rondon,PR
    Janeiro,COOLACER 2026,Tecnologia,28 e 29,Lacerdópolis,SC
    Janeiro,Dinetec,Tecnologia,,Canarana,MT
    Janeiro,Fertilizer Latino Americano,Fertilizantes,,Rio de Janeiro,RJ
    Fevereiro,Sealba Show 2026,Agronegócio,04 a 07,Itabaiana,SE
    Fevereiro,Show Safra BR 163,Tecnologia,18 a 21,Lucas do Rio Verde,MT
    Fevereiro,Show Tecnológico de Verão,Tecnologia,20 a 22,Ponta Grossa,PR
    Fevereiro,Copla Campo,Agronegócio,21 a 23,Piracicaba,SP
    Fevereiro,Show Rural Coopavel,Tecnologia,,"Cascavel",PR
    Março,Expodireto Cotrijal,Agronegócio,03 a 07,Não-Me-Toque,RS
    Março,Expo-Uva,Fruticultura,06 a 09,Jundiaí,SP
    Março,Farm Show,Tecnologia,11 a 14,Primavera do Leste,MT
    Março,Show Safra,Tecnologia,18 a 21,Lucas do Rio Verde,MT
    Março,Força Campo,Agronegócio,20 e 21,Arapoti,PR
    Março,Super Campo,Agronegócio,21 a 23,Londrina,PR
    Abril,Tecnoshow Comigo,Tecnologia,07 a 11,Rio Verde,GO
    Abril,ExpoLondrina,Pecuária,04 a 14,Londrina,PR
    Abril,Norte Show,Agronegócio,16 a 19,Sinop,MT
    Abril,Digital Agro,Tecnologia,23 e 24,Carambeí,PR
    Abril,Agrishow,Tecnologia,28 a 03/05,Ribeirão Preto,SP
    Maio,AgroBrasília,Agronegócio,20 a 24,Brasília,DF
    Maio,Bahia Farm Show,Tecnologia,10 a 14,Luís Eduardo Magalhães,BA
    Maio,Expointer,Pecuária,24 a 01/09,Esteio,RS
    Junho,Hortitec,Horticultura,19 a 21,Holambra,SP
    Julho,Feacoop,Cooperativismo,29 a 01/08,Bebedouro,SP
    Agosto,Show de Inverno,Agronegócio,14 a 16,Ponta Grossa,PR
    Agosto,Agroshow,Agronegócio,21 a 24,Arapoti,PR
    Setembro,Agropec,Pecuária,10 a 13,Paragominas,PA
    Outubro,Frutal,Fruticultura,22 a 24,Fortaleza,CE
    Novembro,Fenacana,Cana-de-açúcar,19 a 21,Sertãozinho,SP
    """
    
    # Usamos io.StringIO para que o pandas leia a string como se fosse um arquivo
    df = pd.read_csv(io.StringIO(dados_string))

    # Limpeza e formatação
    df_cleaned = df.dropna(subset=['Evento'])
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
    geolocator = Nominatim(user_agent="streamlit-app-studio-data-v5")
    geocode = RateLimiter(geolocator.geocode, min_delay_seconds=1)
    location_coords = {}
    
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
            
    df['Latitude'] = df['Localizacao'].map(lambda x: location_coords.get(x, (None, None))[0])
    df['Longitude'] = df['Localizacao'].map(lambda x: location_coords.get(x, (None, None))[1])
    return df

# --- EXECUÇÃO PRINCIPAL DO DASHBOARD ---
try:
    df_limpo = carregar_e_limpar_dados()
    
    if df_limpo.empty:
        st.error("O DataFrame está vazio. Verifique os dados no código.")
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
                popup_text = f"<b>Evento:</b> {row['Nome']}<br><b>Data:</b> {row.get('Datas', 'N/A')}<br><b>Segmento:</b> {row['Segmento']}"
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

except Exception as e:
    st.error(f"Ocorreu um erro inesperado durante a execução: {e}")
    st.error("Se o erro persistir, pode haver um problema com a geocodificação ou com os dados inseridos no código.")

