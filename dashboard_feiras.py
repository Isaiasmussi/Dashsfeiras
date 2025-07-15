import pandas as pd
import streamlit as st
import folium
from streamlit_folium import st_folium
from geopy.geocoders import Nominatim
from geopy.extra.rate_limiter import RateLimiter
import io

# --- CONFIGURAÇÃO DA PÁGINA ---
# Aplicando o tema "Dark Forest"
st.set_page_config(
    layout="wide",
    page_title="Dashboard de Feiras Agro",
    page_icon="🗺️"
)

# Injetando CSS para o tema escuro (opcional, mas melhora a aparência)
st.markdown("""
    <style>
        .main {
            background-color: #1a1a1a;
        }
        .st-emotion-cache-16txtl3 {
            color: #f0f2f6;
        }
    </style>
    """, unsafe_allow_html=True)

st.title("🌲 Dashboard de Feiras e Eventos Agro")

# --- INICIALIZAÇÃO DO ESTADO DA SESSÃO ---
# Usado para "lembrar" qual evento foi clicado
if 'selected_event' not in st.session_state:
    st.session_state.selected_event = None
if 'map_center' not in st.session_state:
    st.session_state.map_center = [-14.2350, -51.9253] # Centro do Brasil
if 'map_zoom' not in st.session_state:
    st.session_state.map_zoom = 4


# --- FUNÇÕES DE PROCESSAMENTO ---
@st.cache_data
def carregar_e_limpar_dados():
    """
    Carrega os dados diretamente do código, eliminando a necessidade de um arquivo externo.
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
    return df_cleaned.reset_index() # Adiciona o index para seleção

@st.cache_data
def geocode_dataframe(df):
    geolocator = Nominatim(user_agent="streamlit-app-studio-data-v7")
    geocode = RateLimiter(geolocator.geocode, min_delay_seconds=1)
    location_coords = {}
    with st.spinner("Geocodificando localizações... (executado apenas uma vez)"):
        for index, row in df.iterrows():
            try:
                location_data = geocode(row['Localizacao'])
                if location_data:
                    location_coords[row['Localizacao']] = (location_data.latitude, location_data.longitude)
            except Exception:
                pass
    df['Latitude'] = df['Localizacao'].map(lambda x: location_coords.get(x, (None, None))[0])
    df['Longitude'] = df['Localizacao'].map(lambda x: location_coords.get(x, (None, None))[1])
    return df

# --- EXECUÇÃO PRINCIPAL ---
try:
    df_limpo = carregar_e_limpar_dados()
    df_geocoded = geocode_dataframe(df_limpo.copy())
    df_mapa = df_geocoded.dropna(subset=['Latitude', 'Longitude'])

    col1, col2 = st.columns([3, 2])

    with col1:
        st.subheader("Mapa Interativo dos Eventos")
        # Usando tiles "CartoDB dark_matter" para o tema escuro
        m = folium.Map(
            location=st.session_state.map_center,
            zoom_start=st.session_state.map_zoom,
            tiles="CartoDB dark_matter"
        )

        for idx, row in df_mapa.iterrows():
            is_selected = (st.session_state.selected_event == row['index'])
            
            # Ícone verde para padrão, vermelho para selecionado
            icon_color = "red" if is_selected else "green"
            
            popup_text = f"<b>Evento:</b> {row['Nome']}<br><b>Data:</b> {row.get('Datas', 'N/A')}<br><b>Segmento:</b> {row['Segmento']}"
            folium.Marker(
                location=[row['Latitude'], row['Longitude']],
                popup=folium.Popup(popup_text, max_width=300),
                tooltip=row['Nome'],
                icon=folium.Icon(color=icon_color, icon="leaf", prefix="fa")
            ).add_to(m)
        
        st_folium(m, use_container_width=True, returned_objects=[])

    with col2:
        st.subheader("Lista de Eventos")
        st.write("Clique em um evento para destacá-lo no mapa.")

        for index, row in df_mapa.iterrows():
            if st.button(f"{row['Nome']} - {row['Cidade']}, {row['UF']}", key=f"event_{row['index']}"):
                st.session_state.selected_event = row['index']
                st.session_state.map_center = [row['Latitude'], row['Longitude']]
                st.session_state.map_zoom = 12 # Zoom mais próximo ao selecionar
                st.rerun() # Força a atualização do app para refletir a seleção

except Exception as e:
    st.error(f"Ocorreu um erro inesperado durante a execução: {e}")

