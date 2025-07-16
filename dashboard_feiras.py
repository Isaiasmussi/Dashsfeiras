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

# Injetando CSS para os ajustes visuais do mapa
st.markdown("""
    <style>
        /* Arredonda as bordas do container do mapa */
        div[data-testid="stHorizontalBlock"] > div:first-child > div[data-testid="stVerticalBlock"] > div:nth-child(2) {
            border-radius: 15px;
            overflow: hidden; /* Essencial para que o conteúdo (mapa) respeite as bordas */
        }
        /* Oculta a caixa de atribuição do Leaflet */
        .leaflet-control-attribution {
            display: none !important;
        }
    </style>
    """, unsafe_allow_html=True)


st.title("Dashboard de Feiras e Eventos Agro")

# --- BASE DE DADOS DOS EXPOSITORES ---
# Esta estrutura irá guardar as listas de expositores para cada evento.
expositores_db = {
    "Congresso Andav 2025": [
        "ADAMA", "AGRO.ALL", "AGROCP", "AGROFIT", "AGROPLAN", "AGROPLANT", "AGROSYSTEM",
        "AGROVANT", "ALBAUGH", "AMIPAR", "ARAG", "ARYSTA", "ASCENZA", "ATAR", "AUDACES",
        "BASF", "BAYER", "BEVAP", "BIOTROP", "BOM FUTURO", "BRA Agroquímica", "BRENNTAG",
        "BUNGE", "COMPASS MINERALS", "CORTEVA", "CROPFIELD", "CURA CAMPO", "DECAL", "DINAMICA",
        "DISAM", "DVA", "ECOSORB", "EUROCHEM", "EXACTA", "FMC", "FOLTRON", "GAFOR", "GALEN",
        "GIRO AGRO", "GOWAN", "GRAO DE OURO", "GRUPO ATUAL", "GRUPO FERTIPAR", "HELM",
        "IHARABRAS", "IHARA", "IMETAME", "INNOVA", "JACTO", "KOPPERT", "LABORATÓRIO FARROUPILHA",
        "LONZA", "LOUIS DREYFUS", "MICROQUIMICA", "MILLENNIUM", "NORTENE", "NORTOX",
        "NUTRIPLAN", "OUROFINO", "OXIQUIMICA", "PERFINOR", "PETROBRAS", "PIONEER",
        "PIRECAL", "PLANALTO", "PLANT DEFENDER", "PRODETER", "ROTAM", "SANDEZ", "SANDEZ AGRO",
        "SANTA CLARA", "SIPCAM NICHINO", "SPEED AGRO", "STOCKOSORB", "SUMITOMO CHEMICAL",
        "SYNGENTA", "TAGRO", "TECNOMYL", "TERRA DE CULTIVO", "TRADE CORP", "UPL", "VERDE",
        "VIAMÃ", "VIGNIS", "VITTIA", "YARA"
    ],
    "Victam Latam 2025": [
        # A lista de expositores da Victam será adicionada aqui quando você a enviar.
    ]
}


# --- INICIALIZAÇÃO DO ESTADO DA SESSÃO ---
if 'selected_event_index' not in st.session_state:
    st.session_state.selected_event_index = None

# --- FUNÇÕES DE PROCESSAMENTO ---
@st.cache_data
def carregar_e_limpar_dados():
    """
    Carrega os dados dos eventos diretamente do código.
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
Julho,Expomontes 2025,Feiras Agro,02 a 11 de julho,Montes Claros,MG
Julho,Fenagen,Genética,02 a 06 de julho,Pelotas,RS
Julho,Agripesi 2025,Agronegócio,03 a 06 de julho,São Gabriel do Oeste,MT
Julho,Conferência Anual ABRAVEQ 2025,Veterinária,03 a 06 de julho,Rio Grande do Sul,RS
Julho,EXPOVALE 2025,Feiras Agro,03 a 06 de julho,Mato Grosso,MT
Julho,ACRICORTE 2025,Feiras Agro,10 e 11 de julho,Cuiabá,MT
Julho,95ª Semana do Fazendeiro da UFV,Geral,12 a 18 de julho,Viçosa,MG
Julho,Enflor Garden Fair 2025,Flores e Jardinagem,13 a 15 de julho,Holambra,SP
Julho,Meeting Up Herb 2025,Plantas Daninhas,15 a 17 de julho,Passo Fundo,RS
Julho,Superleite 2025,Pecuária Leiteira,15 a 18 de julho,Pompéu,MG
Julho,IV Feira da Agricultura Familiar do Ceará 2025,Agricultura Familiar,17 a 19 de julho,Mucambo,CE
Julho,EXPOBEL 2025,Pecuária e Agricultura,18 a 27 de julho,Bela Vista,MS
Julho,CBSoja e Mercosoja 2025,Soja,21 a 24 de julho,Campinas,SP
Julho,TECNOALTA 2025,Tecnologia Agrícola,23 a 26 de julho,Alta Floresta,MT
Julho,Bom Jesus Agrotec Show 2025,Tecnologia Agrícola,23 a 26 de julho,Bom Jesus,PI
Julho,BATATEC 2025,Batata-doce,24 a 27 de julho,Presidente Prudente,SP
Julho,AGROCHAPADA 2025,Pecuária e Agricultura,25 a 27 de julho,Chapada Gaúcha,MG
Julho,Congresso da Sober 2025,Economia Rural,27 a 31 de julho,Passo Fundo,RS
Julho,Biocontrol & Biostimulants LATAM 2025,Biológicos,28 de julho,São Paulo,SP
Julho,Bioeconomy Amazon Summit 2025,Bioeconomia,30 a 31 de julho,Manaus,AM
Julho,Comdor 2025,Saúde Animal,31 de julho a 02 de agosto,Campinas,SP
Agosto,18ª Feira de Sementes Crioulas,Agroecologia,01 a 03 de agosto,Juti,MS
Agosto,Congresso Brasileiro de Fitopatologia 2025,Fitopatologia,03 a 08 de agosto,Lavras,MG
Agosto,Congresso Brasileiro de Fruticultura 2025,Fruticultura,04 a 08 de agosto,Campinas,SP
Agosto,EXPOSUL 2025,Pecuária e Agricultura,04 a 09 de agosto,Rondonópolis,MT
Agosto,Congresso Andav 2025,Distribuição de Insumos,05 a 07 de agosto,São Paulo,SP
Agosto,Agro Leite 2025,Pecuária Leiteira,05 a 08 de agosto,Castro,PR
Agosto,The Brazil Conference & Expo (IFPA),FFLV,06 e 07 de agosto,São Paulo,SP
Agosto,Congresso Brasileiro do Agronegócio 2025,Política e Economia,11 de agosto,São Paulo,SP
Agosto,Agro Ponte 2025,Agronegócio,13 a 17 de agosto,Criciúma,SC
Agosto,Congresso de Aviação Agrícola 2025,Aviação Agrícola,19 a 21 de agosto,Santo Antônio do Leverger,MT
Agosto,Expointer 2025,Pecuária e Máquinas,30 de agosto a 07 de setembro,Esteio,RS
Agosto,56ª EXPOFAC,Feiras Agro,30 de agosto a 07 de setembro,Parauapebas,PA
Setembro,Congresso Brasileiro de Melhoramento de Plantas 2025,Melhoramento de Plantas,02 a 05 de setembro,Luís Correia,PI
Setembro,IFC Brasil 2025,Congressos Internacionais,02 a 04 de setembro,Foz do Iguaçu,PR
Setembro,15ª edição do Citros de Mesa,Fruticultura,04 e 05 de setembro,Cordeirópolis,SP
Setembro,SIM - Expominas BH,Indústria,09 a 12 de setembro,Belo Horizonte,MG
Setembro,II Simpósio Soja Max,Soja,10 e 11 de setembro,Londrina,PR
Setembro,Agrotech Expo 2025,Tecnologia,10 a 14 de setembro,São José dos Campos,SP
Setembro,Congresso Paranaense de Zootecnia 2025,Zootecnia,10 a 13 de setembro,Paraná,PR
Setembro,SICONBIOL 2025,Controle Biológico,14 a 18 de setembro,Gramado,RS
Setembro,Conferência Bienal WDA–LA 2025,Saúde Animal,15 de setembro,Minas Gerais,MG
Setembro,Victam Latam 2025,Rações e Grãos,16 a 18 de setembro,São Paulo,SP
Setembro,Fórum Pecuária Brasil 2025,Pecuária,17 de setembro,São Paulo,SP
Setembro,III SIMPOHERBI 2025,Controle de Plantas Daninhas,24 a 26 de setembro,Jaboticabal,SP
Setembro,WSAVA World Congress 2025,Medicina Veterinária,25 a 27 de setembro,Rio de Janeiro,RJ
Setembro,Encontro Abelheiro 2025,Apicultura,26 a 28 de setembro,Carazinho,RS
Setembro,Semana Agronômica MS 2025,Agronomia,29 de setembro a 04 de outubro,Aquidauana,MS
Outubro,Rio + Agro,Tecnologia,01 a 03 de outubro,Rio de Janeiro,RJ
Outubro,ZOOTEC 2025,Zootecnia,07 a 10 de outubro,Salvador,BA
Outubro,Congresso Brasileiro de Agronomia (CBA) 2025,Agronomia,14 a 17 de outubro,Maceió,AL
Outubro,FENASAN 2025,Saneamento e Meio Ambiente,21 a 23 de outubro,São Paulo,SP
Outubro,Congresso Nacional das Mulheres do Agronegócio (CNMA),Liderança Feminina,22 e 23 de outubro,São Paulo,SP
Outubro,II Fórum Abisolo + III Simpósio Biofertilizantes,Fertilizantes,22 e 23 de outubro,Campinas,SP
Outubro,COMCIR 2025,Cirurgia Veterinária,30 de outubro a 01 de novembro,Foz do Iguaçu,PR
Novembro,Conf. Int. Agric. Inteligente para o Clima,Agricultura e Clima,05 de novembro,Brasília,DF
Novembro,COP30,Clima e Sustentabilidade,10 de novembro,Belém,PA
Novembro,FENACAM 2025,Aquicultura,11 a 14 de novembro,Natal,RN
Novembro,SIMLEITE,Pecuária Leiteira,13 a 15 de novembro,Minas Gerais,MG
Novembro,FIMAN 2025,Agricultura,25 a 27 de novembro,Paranavaí,PR
Novembro,AveSummit & AveExpo 2025,Avicultura,26 a 28 de novembro,Campinas,SP
Novembro,Congresso Nordestino de Produção Animal (CNPA),Produção Animal,26 de novembro,Maceió,AL
Novembro,FENAGRO 2025,Pecuária e Agricultura Familiar,28 de novembro a 07 de dezembro,Salvador,BA
Dezembro,Prêmio Visão Agro Brasil 2025,Bioenergia,04 de dezembro,Ribeirão Preto,SP
Dezembro,Planejamento estratégico Agrolink,Estratégia,29 e 30 de dezembro,Porto Alegre,RS
"""
    df = pd.read_csv(io.StringIO(dados_string))
    df['Cidade'] = df['Cidade'].str.strip()
    df['UF'] = df['UF'].str.strip()
    df.dropna(subset=['Evento', 'Cidade', 'UF'], inplace=True)
    df = df[~df['Cidade'].str.contains('A definir|Online', na=False)]
    df['Mês'] = df['Mês'].ffill()
    df['Localizacao'] = df['Cidade'] + ', ' + df['UF']
    df.rename(columns={'Mês': 'Mes', 'Evento': 'Nome', 'Foco': 'Segmento', 'Data': 'Datas'}, inplace=True)
    return df.reset_index()

@st.cache_data
def geocode_dataframe(df):
    geolocator = Nominatim(user_agent="studio-data-dashboard-v13")
    location_coords = {}
    with st.spinner("A geocodificar localizações... (executado apenas uma vez)"):
        for index, row in df.iterrows():
            try:
                location_data = geolocator.geocode(row['Localizacao'])
                if location_data:
                    location_coords[row['Localizacao']] = (location_data.latitude, location_data.longitude)
                time.sleep(1)
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
        st.dataframe(df_filtrado[['Nome', 'Datas', 'Segmento', 'Cidade', 'UF']], use_container_width=True, hide_index=True, height=250) # Altura ajustada

        # --- NOVA SEÇÃO DE EXPOSITORES ---
        if selected_event_name and selected_event_name in expositores_db:
            with st.expander(f"Ver Expositores de {selected_event_name}", expanded=True):
                lista_expositores = expositores_db[selected_event_name]
                
                # Barra de pesquisa para os expositores
                search_term = st.text_input("Pesquisar expositor:", key=f"search_{selected_event_name}")
                if search_term:
                    lista_expositores = [exp for exp in lista_expositores if search_term.lower() in exp.lower()]
                
                # Exibe a lista em colunas para melhor aproveitamento do espaço
                num_cols = 3
                cols = st.columns(num_cols)
                for i, expositor in enumerate(sorted(lista_expositores)):
                    with cols[i % num_cols]:
                        st.markdown(f"- {expositor}")

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
        
        m.get_root().html.add_child(folium.Element("<style>.leaflet-control-attribution {display: none !important;}</style>"))

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

