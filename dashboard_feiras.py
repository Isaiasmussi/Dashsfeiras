import pandas as pd
import streamlit as st
import folium
from streamlit_folium import st_folium
from geopy.geocoders import Nominatim
import io
import time

# --- CONFIGURAÇÃO DA PÁGINA E ESTILOS ---
st.set_page_config(
    layout="wide",
    page_title="Dashboard de Feiras Agro"
)

# Injetando CSS com um seletor mais robusto para o mapa
st.markdown("""
    <style>
        /* Usa um seletor estável para encontrar o mapa */
        div[data-testid="stHorizontalBlock"] > div:first-child iframe {
            border-radius: 15px;
        }
        
        /* Diminui a caixa de atribuição do Leaflet */
        .leaflet-control-attribution {
            font-size: 0.7rem !important;
            padding: 2px 4px !important;
            background-color: rgba(255, 255, 255, 0.7) !important;
        }
    </style>
    """, unsafe_allow_html=True)


st.title("Dashboard de Feiras e Eventos Agro")

# --- INICIALIZAÇÃO DO ESTADO DA SESSÃO ---
if 'selected_event_index' not in st.session_state:
    st.session_state.selected_event_index = None

# --- FUNÇÕES DE PROCESSAMENTO ---
@st.cache_data
def carregar_e_limpar_dados():
    """
    Carrega os dados diretamente do código.
    """
    dados_string = """Mês,Evento,Foco,Data,Cidade,UF
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
    df = pd.read_csv(io.StringIO(dados_string))
    df_cleaned = df.dropna(subset=['Evento'])
    df_cleaned['Mês'] = df_cleaned['Mês'].ffill()
    df_cleaned['Localizacao'] = df_cleaned['Cidade'] + ', ' + df_cleaned['UF']
    df_cleaned.rename(columns={'Mês': 'Mes', 'Evento': 'Nome', 'Foco': 'Segmento', 'Data': 'Datas'}, inplace=True)
    return df_cleaned.reset_index()

@st.cache_data
def geocode_dataframe(df):
    geolocator = Nominatim(user_agent="studio-data-dashboard-v12")
    location_coords = {}
    with st.spinner("Geocodificando localizações... (executado apenas uma vez)"):
        for index, row in df.iterrows():
            try:
                # Usando o geocode diretamente, sem o RateLimiter
                location_data = geolocator.geocode(row['Localizacao'])
                if location_data:
                    location_coords[row['Localizacao']] = (location_data.latitude, location_data.longitude)
                time.sleep(1) # Pausa manual para não sobrecarregar o serviço
            except Exception:
                pass
    df['Latitude'] = df['Localizacao'].map(lambda x: location_coords.get(x, (None, None))[0])
    df['Longitude'] = df['Localizacao'].map(lambda x: location_coords.get(x, (None, None))[1])
    return df

# --- EXECUÇÃO PRINCIPAL ---
try:
    df_completo = carregar_e_limpar_dados()
    df_geocoded = geocode_dataframe(df_completo.copy())
    df_base = df_geocoded.dropna(subset=['Latitude', 'Longitude']).copy()

    col1, col2 = st.columns([3, 2])

    with col2:
        st.subheader("Filtros e Controles")
        selected_meses = st.multiselect("Filtrar por Mês:", options=sorted(df_base['Mes'].unique()))
        selected_ufs = st.multiselect("Filtrar por Estado (UF):", options=sorted(df_base['UF'].unique()))
        cidades_disponiveis = sorted(df_base[df_base['UF'].isin(selected_ufs)]['Cidade'].unique()) if selected_ufs else sorted(df_base['Cidade'].unique())
        selected_cidades = st.multiselect("Filtrar por Cidade:", options=cidades_disponiveis)

        df_filtrado = df_base.copy()
        if selected_meses:
            df_filtrado = df_filtrado[df_filtrado['Mes'].isin(selected_meses)]
        if selected_ufs:
            df_filtrado = df_filtrado[df_filtrado['UF'].isin(selected_ufs)]
        if selected_cidades:
            df_filtrado = df_filtrado[df_filtrado['Cidade'].isin(selected_cidades)]

        event_list = df_filtrado['Nome'].tolist()
        event_list.insert(0, "Limpar seleção e resetar mapa")
        
        selected_event_name = st.selectbox("Selecione um evento para destacar no mapa:", options=event_list, index=0)

        if selected_event_name != "Limpar seleção e resetar mapa":
            st.session_state.selected_event_index = df_filtrado[df_filtrado['Nome'] == selected_event_name].index[0]
        else:
            st.session_state.selected_event_index = None
        
        st.subheader("Dados dos Eventos")
        st.dataframe(df_filtrado[['Nome', 'Datas', 'Segmento', 'Cidade', 'UF']], use_container_width=True, hide_index=True, height=350)

    with col1:
        st.subheader("Mapa Interativo dos Eventos")
        
        if st.session_state.selected_event_index is not None and st.session_state.selected_event_index in df_filtrado.index:
            selected_row = df_filtrado.loc[st.session_state.selected_event_index]
            map_center = [selected_row['Latitude'], selected_row['Longitude']]
            map_zoom = 12
        else:
            map_center = [-14.2350, -51.9253]
            map_zoom = 4

        m = folium.Map(location=map_center, zoom_start=map_zoom, tiles="CartoDB dark_matter")

        for idx, row in df_filtrado.iterrows():
            is_selected = (st.session_state.selected_event_index == idx)
            folium.CircleMarker(
                location=[row['Latitude'], row['Longitude']],
                radius=8,
                color="red" if is_selected else "#2ECC71",
                fill=True,
                fill_color="red" if is_selected else "#2ECC71",
                fill_opacity=0.7 if is_selected else 0.4,
                popup=f"<b>{row['Nome']}</b><br>{row['Cidade']}, {row['UF']}",
                tooltip=row['Nome']
            ).add_to(m)
        
        st_folium(m, use_container_width=True, returned_objects=[])

except Exception as e:
    st.error(f"Ocorreu um erro inesperado durante a execução: {e}")

