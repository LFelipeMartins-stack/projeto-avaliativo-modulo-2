import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from sqlalchemy import create_engine
from src import config

# ==========================================
# 1. CONFIGURAÇÃO DE UX (DESIGN SYSTEM)
# ==========================================
st.set_page_config(
    page_title="Inteligência PNCP 2025",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Estilização CSS para métricas (Contraste e Alinhamento - CRAP)
st.markdown("""
    <style>
    .metric-card {
        background-color: #1e293b;
        border-radius: 8px;
        padding: 20px;
        border-left: 5px solid #38bdf8;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
    }
    .metric-title { color: #94a3b8; font-size: 0.9rem; font-weight: 600; text-transform: uppercase; }
    .metric-value { color: #f8fafc; font-size: 1.8rem; font-weight: bold; margin-top: 5px; }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 2. CONEXÃO E CARGA DE DADOS
# ==========================================
@st.cache_resource
def obter_conexao():
    url = f"postgresql+psycopg2://{config.PG_CONFIG['user']}:{config.PG_CONFIG['password']}@{config.PG_CONFIG['host']}:{config.PG_CONFIG['port']}/{config.PG_DATABASE}"
    return create_engine(url)

engine = obter_conexao()

@st.cache_data
def carregar_dados():
    f = pd.read_sql("SELECT * FROM fato_item_contratado", engine)
    o = pd.read_sql("SELECT * FROM dim_orgao", engine)
    fo = pd.read_sql("SELECT * FROM dim_fornecedor", engine)
    m = pd.read_sql("SELECT * FROM dim_modalidade", engine)
    l = pd.read_sql("SELECT * FROM dim_localidade", engine)
    return f, o, fo, m, l

fato_bruta, dim_orgao, dim_fornecedor, dim_modalidade, dim_localidade = carregar_dados()

# ==========================================
# 3. NAVEGAÇÃO E FILTROS GLOBAIS (SIDEBAR)
# ==========================================
with st.sidebar:
    st.image("https://upload.wikimedia.org/wikipedia/commons/thumb/1/11/Coat_of_arms_of_Brazil.svg/200px-Coat_of_arms_of_Brazil.svg.png", width=80)
    st.title("Controladoria Federal")
    st.markdown("---")
    
    # Navegação Executiva
    st.subheader("Navegação")
    pagina = st.radio(
        "Selecione o Painel:",
        ["🏠 Visão Geral (Home)", 
         "1️⃣ Economia Global", 
         "2️⃣ Fornecedores e Risco", 
         "3️⃣ Eficácia por Modalidade", 
         "4️⃣ Tempo de Ciclo", 
         "5️⃣ Distribuição Regional", 
         "6️⃣ Perfil dos Gastos"]
    )
    
    st.markdown("---")
    
    # Interatividade: Filtro Global
    st.subheader("Filtros Dinâmicos")
    filtro_perfil = st.selectbox(
        "Filtrar por Perfil de Gasto:",
        ["Todos", "Obras e engenharia", "Serviços", "Bens"]
    )
    
    # Aplicação do Filtro
    if filtro_perfil != "Todos":
        fato = fato_bruta[fato_bruta["perfil_gasto"] == filtro_perfil]
    else:
        fato = fato_bruta

# Pré-cálculos globais baseados na base filtrada
vol_homologado = fato["valor_total_homologado"].sum()
comp = fato[fato["comparavel"] == 1]
est_comp = comp["valor_total_estimado"].sum()
hom_comp = comp["valor_total_homologado"].sum()
economia_rs = est_comp - hom_comp
economia_pct = (economia_rs / est_comp * 100) if est_comp > 0 else 0

# ==========================================
# 4. PÁGINAS DO DASHBOARD
# ==========================================

if pagina == "🏠 Visão Geral (Home)":
    st.title("🏛️ Auditoria de Contratações Públicas (PNCP 2025)")
    st.markdown("Painel executivo (*Sala de Situação*) para monitoramento de contratos, riscos e conformidade financeira.")
    
    # Cards de KPI (Proximidade e Alinhamento)
    c1, c2, c3, c4 = st.columns(4)
    c1.markdown(f"<div class='metric-card'><div class='metric-title'>Total Homologado</div><div class='metric-value'>R$ {vol_homologado/1e9:.2f} Bi</div></div>", unsafe_allow_html=True)
    c2.markdown(f"<div class='metric-card'><div class='metric-title'>Economia Obtida</div><div class='metric-value'>R$ {economia_rs/1e6:.2f} Mi</div></div>", unsafe_allow_html=True)
    c3.markdown(f"<div class='metric-card'><div class='metric-title'>Deságio Médio</div><div class='metric-value'>{economia_pct:.2f}%</div></div>", unsafe_allow_html=True)
    c4.markdown(f"<div class='metric-card'><div class='metric-title'>Itens Auditados</div><div class='metric-value'>{len(fato):,}</div></div>", unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Gráficos de Resumo
    colA, colB = st.columns(2)
    with colA:
        resumo_perfil = fato.groupby("perfil_gasto")["valor_total_homologado"].sum().reset_index()
        fig1 = px.pie(resumo_perfil, values='valor_total_homologado', names='perfil_gasto', title='Orçamento por Perfil', hole=0.4, color_discrete_sequence=px.colors.qualitative.Prism)
        st.plotly_chart(fig1, use_container_width=True)
        
    with colB:
        df_loc = fato.merge(dim_localidade, on="sk_localidade")
        resumo_reg = df_loc.groupby("regiao")["valor_total_homologado"].sum().reset_index().sort_values("valor_total_homologado")
        fig2 = px.bar(resumo_reg, x='valor_total_homologado', y='regiao', orientation='h', title='Orçamento por Região (R$)', text_auto='.2s')
        st.plotly_chart(fig2, use_container_width=True)

elif pagina == "1️⃣ Economia Global":
    st.header("Pergunta 1: Quanto o governo economizou?")
    pct_comp = (len(comp) / len(fato) * 100) if len(fato) > 0 else 0

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Volume Homologado", f"R$ {vol_homologado/1e6:,.1f} Mi")
    col2.metric("Economia Nominal", f"R$ {economia_rs/1e6:,.1f} Mi")
    col3.metric("Deságio (Economia %)", f"{economia_pct:.2f}%")
    col4.metric("% Itens Comparáveis", f"{pct_comp:.2f}%")
    
    st.info("**Conclusão:** O governo assegurou deságio estrutural robusto, evidenciando a efetividade das fases de lances competitivos sobre a base comparável.")

elif pagina == "2️⃣ Fornecedores e Risco":
    st.header("Pergunta 2: Quem concentra o orçamento? É um risco?")
    df_forn = fato.merge(dim_fornecedor, on="sk_fornecedor")
    top_forn = df_forn.groupby(["nome_fornecedor"])["valor_total_homologado"].sum().reset_index().sort_values(by="valor_total_homologado", ascending=False).head(10)
    top_forn["pct_participacao"] = (top_forn["valor_total_homologado"] / vol_homologado) * 100
    concentracao_top10 = top_forn["pct_participacao"].sum()

    st.metric("Concentração do Orçamento no Top 10", f"{concentracao_top10:.2f}%")
    fig = px.bar(top_forn, x="valor_total_homologado", y="nome_fornecedor", orientation="h", title="Top 10 Fornecedores", text=top_forn["valor_total_homologado"].apply(lambda x: f"R$ {x/1e6:.1f}M"))
    fig.update_layout(yaxis={'categoryorder': 'total ascending'})
    st.plotly_chart(fig, use_container_width=True)
    st.warning(f"**Risco de Concentração:** Apenas 10 empresas detêm {concentracao_top10:.2f}% dos recursos homologados. Sugere-se auditoria de dependência contratual.")

elif pagina == "3️⃣ Eficácia por Modalidade":
    st.header("Pergunta 3: Qual modalidade economiza mais e qual movimenta mais?")
    df_mod = fato.merge(dim_modalidade, on="sk_modalidade")
    df_mod["est_comp"] = df_mod["valor_total_estimado"].where(df_mod["comparavel"] == 1, 0.0)
    df_mod["eco_comp"] = df_mod["economia_valor"].where(df_mod["comparavel"] == 1, 0.0)
    
    res_mod = df_mod.groupby("nome_modalidade").agg(vol=("valor_total_homologado", "sum"), est=("est_comp", "sum"), eco=("eco_comp", "sum")).reset_index()
    res_mod["desagio"] = (res_mod["eco"] / res_mod["est"] * 100).where(res_mod["est"] > 0, None)
    
    c1, c2 = st.columns(2)
    c1.plotly_chart(px.pie(res_mod, values="vol", names="nome_modalidade", title="Orçamento por Modalidade"), use_container_width=True)
    c2.plotly_chart(px.bar(res_mod.dropna(subset=["desagio"]), x="nome_modalidade", y="desagio", title="Deságio (%) por Modalidade"), use_container_width=True)
    st.info("**Conclusão:** O Credenciamento não possui deságio (teto fixo). O Pregão Eletrônico desponta como a ferramenta mais agressiva para redução de preços públicos.")

elif pagina == "4️⃣ Tempo de Ciclo":
    st.header("Pergunta 4: Onde as compras demoram mais?")
    ciclo_valido = fato.dropna(subset=["dias_ciclo"])
    c1, c2, c3 = st.columns(3)
    c1.metric("Ciclo Médio", f"{ciclo_valido['dias_ciclo'].mean():.1f} dias")
    c2.metric("Ciclo Máximo", f"{ciclo_valido['dias_ciclo'].max():.0f} dias")
    c3.metric("Certames Anômalos (Sem Ciclo)", f"{fato['dias_ciclo'].isna().sum()}")

    df_org = fato.merge(dim_orgao, on="sk_orgao")
    org_ciclo = df_org.groupby("nome_orgao").agg(qtd=("dias_ciclo", "count"), media=("dias_ciclo", "mean")).reset_index()
    lentos = org_ciclo[org_ciclo["qtd"] >= 5].sort_values("media", ascending=False).head(10)
    
    fig = px.bar(lentos, x="media", y="nome_orgao", orientation="h", title="Top 10 Órgãos Lentos (≥ 5 certames)", text_auto='.1f')
    fig.update_layout(yaxis={'categoryorder': 'total ascending'})
    st.plotly_chart(fig, use_container_width=True)
    st.info("**Conclusão:** Gargalos temporais severos localizados prioritariamente em conselhos de classe e universidades, demandando revisão de fluxos internos de compras.")

elif pagina == "5️⃣ Distribuição Regional":
    st.header("Pergunta 5: Onde se gasta mais e onde se consegue mais desconto?")
    df_loc = fato.merge(dim_localidade, on="sk_localidade")
    df_loc["est_comp"] = df_loc["valor_total_estimado"].where(df_loc["comparavel"] == 1, 0.0)
    df_loc["eco_comp"] = df_loc["economia_valor"].where(df_loc["comparavel"] == 1, 0.0)
    
    reg = df_loc.groupby("regiao").agg(vol=("valor_total_homologado", "sum"), est=("est_comp", "sum"), eco=("eco_comp", "sum")).reset_index()
    reg["desagio"] = (reg["eco"] / reg["est"]) * 100
    
    c1, c2 = st.columns(2)
    c1.plotly_chart(px.bar(reg.sort_values("vol"), x="vol", y="regiao", orientation="h", title="Volume por Região"), use_container_width=True)
    c2.plotly_chart(px.bar(reg.sort_values("desagio"), x="regiao", y="desagio", title="Deságio (%) por Região", color="desagio", color_continuous_scale="Blues"), use_container_width=True)
    st.info("**Conclusão:** Concentração maciça de capital em Brasília (Centro-Oeste), mas a região Norte lidera a eficiência em desconto.")

elif pagina == "6️⃣ Perfil dos Gastos":
    st.header("Pergunta 6: Em que o dinheiro público é gasto?")
    perfil = fato.groupby("perfil_gasto").agg(itens=("numero_item", "count"), vol=("valor_total_homologado", "sum")).reset_index()
    perfil["ticket"] = perfil["vol"] / perfil["itens"]
    
    c1, c2 = st.columns(2)
    c1.plotly_chart(px.pie(perfil, values="vol", names="perfil_gasto", title="Divisão do Orçamento"), use_container_width=True)
    c2.plotly_chart(px.bar(perfil, x="perfil_gasto", y="ticket", title="Ticket Médio por Contrato (R$)", text=perfil["ticket"].apply(lambda x: f"R$ {x/1e6:.2f}M")), use_container_width=True)
    st.info("**Conclusão:** Obras de infraestrutura dominam o capital empenhado, enquanto a aquisição de Bens movimenta o maior volume operacional de itens.")