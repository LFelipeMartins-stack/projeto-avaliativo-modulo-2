import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from sqlalchemy import create_engine
from src import config

# =============================================================================
# 1. DESIGN SYSTEM, TIPOGRAFIA & DESIGN TOKENS DINÂMICOS
# =============================================================================
st.set_page_config(
    page_title="Inteligência PNCP 2025",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Paletas Categóricas Globais de Alto Contraste (Cores com boa leitura em ambos os temas)
COLOR_MAP_MODALIDADE = {
    "Concorrência - Eletrônica": "#0284c7",     # Azul Royal
    "Credenciamento": "#6366f1",                # Índigo
    "Pregão - Eletrônico": "#0ea5e9",           # Azul Oceano
    "Concorrência - Presencial": "#ea580c",      # Laranja Queimado
    "Inexigibilidade": "#059669",               # Esmeralda
    "Dispensa": "#9333ea",                      # Roxo
    "Pregão - Presencial": "#e11d48"            # Carmesim
}

COLOR_MAP_PERFIL = {
    "Obras e engenharia": "#d97706",            # Âmbar Médio
    "Serviços": "#0284c7",                      # Azul Corporativo
    "Bens": "#7c3aed"                           # Violeta
}

# Rótulos externos sem cor fixa: herdam automaticamente o tema (Light ou Dark)
FONT_LABELS = dict(size=11, family="sans-serif")

def aplicar_layout_executivo(fig):
    """Garante fundo transparente e delega contraste de texto ao tema ativo."""
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=10, r=50, t=40, b=20)
    )
    # cliponaxis apenas em barras para não cortar números externos
    fig.update_traces(cliponaxis=False, selector=dict(type='bar'))
    return fig

# CSS Adaptativo via Variáveis Nativas do Streamlit
st.markdown("""
    <style>
    .metric-card {
        background-color: var(--secondary-background-color, #1e293b);
        border-radius: 8px;
        padding: 18px 22px;
        border-left: 5px solid #0284c7;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
    }
    .metric-title { 
        color: var(--text-color, #94a3b8); 
        opacity: 0.75;
        font-size: 0.82rem; 
        font-weight: 600; 
        text-transform: uppercase; 
        letter-spacing: 0.6px; 
    }
    .metric-value { 
        color: var(--text-color, #f8fafc); 
        font-size: 1.75rem; 
        font-weight: 700; 
        margin-top: 5px; 
    }
    .filter-badge {
        display: inline-block;
        background-color: #0284c7;
        color: #ffffff;
        padding: 4px 10px;
        border-radius: 12px;
        font-size: 0.8rem;
        font-weight: 600;
        margin-bottom: 15px;
    }
    </style>
""", unsafe_allow_html=True)

# =============================================================================
# 2. CONEXÃO E CARGA DE DADOS (HÍBRIDO COM FALLBACK)
# =============================================================================
@st.cache_resource
def obter_conexao():
    try:
        url = (
            f"postgresql+psycopg2://{config.PG_CONFIG['user']}:{config.PG_CONFIG['password']}@"
            f"{config.PG_CONFIG['host']}:{config.PG_CONFIG['port']}/{config.PG_DATABASE}"
        )
        return create_engine(url)
    except Exception:
        return None

engine = obter_conexao()

@st.cache_data
def carregar_dados():
    modo_origem = "PostgreSQL"
    try:
        # 1. Tentativa primária: Banco de Dados Relacional
        if engine is None:
            raise ConnectionError("Engine PostgreSQL não inicializada.")
        
        f = pd.read_sql("SELECT * FROM fato_item_contratado", engine)
        o = pd.read_sql("SELECT * FROM dim_orgao", engine)
        fo = pd.read_sql("SELECT * FROM dim_fornecedor", engine)
        m = pd.read_sql("SELECT * FROM dim_modalidade", engine)
        l = pd.read_sql("SELECT * FROM dim_localidade", engine)
    except Exception:
        # 2. Fallback de alta disponibilidade: Base processada em data/processed/
        modo_origem = "CSVs Processados (Fallback)"
        dir_proc = Path(__file__).resolve().parent.parent / "data" / "processed"
        f = pd.read_csv(dir_proc / "fato_item_contratado.csv")
        o = pd.read_csv(dir_proc / "dim_orgao.csv")
        fo = pd.read_csv(dir_proc / "dim_fornecedor.csv")
        m = pd.read_csv(dir_proc / "dim_modalidade.csv")
        l = pd.read_csv(dir_proc / "dim_localidade.csv")
    
    # Padronização temporal
    f["data_publicacao"] = pd.to_datetime(f["data_publicacao"])
    f["ano_mes"] = f["data_publicacao"].dt.to_period("M").astype(str)
    
    return f, o, fo, m, l, modo_origem

fato_bruta, dim_orgao, dim_fornecedor, dim_modalidade, dim_localidade, modo_origem = carregar_dados()

# =============================================================================
# 3. BARRA LATERAL: NAVEGAÇÃO E FILTROS DINÂMICOS
# =============================================================================
with st.sidebar:
    st.markdown("## 🏛️ Controladoria Geral")
    st.caption("Inteligência em Compras Públicas • PNCP 2025")
    
    # Telemetria da fonte de dados (Produção vs Fallback)
    if "PostgreSQL" in modo_origem:
        st.success("● Fonte: PostgreSQL 16 (Online)", icon="🗄️")
    else:
        st.warning("● Fonte: Base Processada (Fallback)", icon="📂")
        
    st.markdown("---")
    
    st.subheader("Navegação Executiva")
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
    st.subheader("Filtros Dinâmicos")
    filtro_perfil = st.selectbox(
        "Filtrar por Perfil de Gasto:",
        ["Todos", "Obras e engenharia", "Serviços", "Bens"]
    )
    
    if filtro_perfil != "Todos":
        fato = fato_bruta[fato_bruta["perfil_gasto"] == filtro_perfil]
    else:
        fato = fato_bruta

# Métricas da base ativa
vol_homologado = fato["valor_total_homologado"].sum()
comp = fato[fato["comparavel"] == 1]
est_comp = comp["valor_total_estimado"].sum()
hom_comp = comp["valor_total_homologado"].sum()
economia_rs = est_comp - hom_comp
economia_pct = (economia_rs / est_comp * 100) if est_comp > 0 else 0
pct_comp = (len(comp) / len(fato) * 100) if len(fato) > 0 else 0

# =============================================================================
# 4. PÁGINAS DO DASHBOARD
# =============================================================================

# --- PÁGINA: HOME ---
if pagina == "🏠 Visão Geral (Home)":
    st.title("🏛️ Sala de Situação — Compras Públicas Federais (2025)")
    st.markdown("Painel executivo consolidado para controle externo, auditoria contínua e mitigação de riscos.")
    
    if filtro_perfil != "Todos":
        st.markdown(f"<span class='filter-badge'>Filtro Ativo: {filtro_perfil}</span>", unsafe_allow_html=True)
    
    c1, c2, c3, c4 = st.columns(4)
    c1.markdown(f"<div class='metric-card'><div class='metric-title'>Total Homologado</div><div class='metric-value'>R$ {vol_homologado/1e9:.2f} Bi</div></div>", unsafe_allow_html=True)
    c2.markdown(f"<div class='metric-card'><div class='metric-title'>Economia Nominal</div><div class='metric-value'>R$ {economia_rs/1e6:.2f} Mi</div></div>", unsafe_allow_html=True)
    c3.markdown(f"<div class='metric-card'><div class='metric-title'>Deságio Médio</div><div class='metric-value'>{economia_pct:.2f}%</div></div>", unsafe_allow_html=True)
    c4.markdown(f"<div class='metric-card'><div class='metric-title'>Itens Auditados</div><div class='metric-value'>{len(fato):,}</div></div>", unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    colA, colB = st.columns(2)
    
    with colA:
        resumo_perfil = fato.groupby("perfil_gasto")["valor_total_homologado"].sum().reset_index()
        fig1 = px.pie(
            resumo_perfil,
            values='valor_total_homologado',
            names='perfil_gasto',
            title='Distribuição Orçamentária por Perfil',
            hole=0.45,
            color='perfil_gasto',
            color_discrete_map=COLOR_MAP_PERFIL
        )
        fig1.update_traces(
            textposition='inside',
            textinfo='percent+label',
            insidetextfont=dict(color="#ffffff", size=11, family="sans-serif")
        )
        aplicar_layout_executivo(fig1)
        st.plotly_chart(fig1, use_container_width=True)
        
    with colB:
        df_loc = fato.merge(dim_localidade, on="sk_localidade")
        resumo_reg = df_loc.groupby("regiao")["valor_total_homologado"].sum().reset_index().sort_values("valor_total_homologado")
        max_v = resumo_reg['valor_total_homologado'].max()
        fig2 = px.bar(
            resumo_reg,
            x='valor_total_homologado',
            y='regiao',
            orientation='h',
            title='Orçamento Homologado por Macrorregião',
            labels={"valor_total_homologado": "Volume Homologado (R$)", "regiao": "Região"},
            text=resumo_reg['valor_total_homologado'].apply(lambda x: f"R$ {x/1e9:.2f} Bi"),
            color='valor_total_homologado',
            color_continuous_scale=["#0369a1", "#0284c7", "#38bdf8"]
        )
        fig2.update_traces(textposition='outside', textfont=FONT_LABELS)
        fig2.update_layout(coloraxis_showscale=False, yaxis={'categoryorder': 'total ascending'})
        fig2.update_xaxes(range=[0, max_v * 1.25])
        aplicar_layout_executivo(fig2)
        st.plotly_chart(fig2, use_container_width=True)

# --- PÁGINA 1: ECONOMIA GLOBAL ---
elif pagina == "1️⃣ Economia Global":
    st.header("Pergunta 1: Quanto o governo economizou?")
    
    if filtro_perfil != "Todos":
        st.markdown(f"<span class='filter-badge'>Filtro Ativo: {filtro_perfil}</span>", unsafe_allow_html=True)

    c1, c2, c3, c4 = st.columns(4)
    c1.markdown(f"<div class='metric-card'><div class='metric-title'>Volume Homologado</div><div class='metric-value'>R$ {vol_homologado/1e9:.2f} Bi</div></div>", unsafe_allow_html=True)
    c2.markdown(f"<div class='metric-card'><div class='metric-title'>Economia Nominal</div><div class='metric-value'>R$ {economia_rs/1e6:.2f} Mi</div></div>", unsafe_allow_html=True)
    c3.markdown(f"<div class='metric-card'><div class='metric-title'>Deságio Médio</div><div class='metric-value'>{economia_pct:.2f}%</div></div>", unsafe_allow_html=True)
    c4.markdown(f"<div class='metric-card'><div class='metric-title'>Itens Comparáveis</div><div class='metric-value'>{pct_comp:.2f}%</div></div>", unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    mensal = comp.groupby("ano_mes").agg(
        estimado=("valor_total_estimado", "sum"),
        homologado=("valor_total_homologado", "sum"),
        economia=("economia_valor", "sum")
    ).reset_index().sort_values("ano_mes")
    
    fig_temp = go.Figure()
    fig_temp.add_trace(go.Bar(
        x=mensal["ano_mes"], 
        y=mensal["estimado"], 
        name="Estimado Comparável", 
        marker_color="#64748b"
    ))
    fig_temp.add_trace(go.Bar(
        x=mensal["ano_mes"], 
        y=mensal["homologado"], 
        name="Homologado Comparável", 
        marker_color="#0284c7"
    ))
    fig_temp.add_trace(go.Scatter(
        x=mensal["ano_mes"], 
        y=mensal["economia"], 
        name="Economia Obtida (R$)", 
        mode="lines+markers", 
        line=dict(color="#10b981", width=3)
    ))
    fig_temp.update_layout(
        title="Evolução Mensal: Valor Estimado vs. Homologado e Economia (2025)",
        barmode="group",
        xaxis_title="Mês de Publicação",
        yaxis_title="Montante Financeiro (R$)",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    aplicar_layout_executivo(fig_temp)
    st.plotly_chart(fig_temp, use_container_width=True)

    if filtro_perfil == "Todos":
        st.info(f"**Conclusão da Controladoria:** A Administração Federal obteve economia nominal de R$ {economia_rs/1e6:,.2f} milhões ({economia_pct:.2f}% de deságio) sobre a base comparável ({pct_comp:.2f}% dos itens), atestando a eficácia dos certames concorrenciais.")
    else:
        st.info(f"**Conclusão da Controladoria ({filtro_perfil}):** No recorte de {filtro_perfil}, a economia nominal apurada atingiu R$ {economia_rs/1e6:,.2f} milhões ({economia_pct:.2f}% de deságio), com índice de comparabilidade de {pct_comp:.2f}%.")

# --- PÁGINA 2: FORNECEDORES E RISCO ---
elif pagina == "2️⃣ Fornecedores e Risco":
    st.header("Pergunta 2: Quem concentra o orçamento? É um risco?")
    
    if filtro_perfil != "Todos":
        st.markdown(f"<span class='filter-badge'>Filtro Ativo: {filtro_perfil}</span>", unsafe_allow_html=True)
        
    df_forn = fato.merge(dim_fornecedor, on="sk_fornecedor")
    top_forn = df_forn.groupby(["nome_fornecedor"])["valor_total_homologado"].sum().reset_index().sort_values(by="valor_total_homologado", ascending=False).head(10)
    top_forn["pct_participacao"] = (top_forn["valor_total_homologado"] / vol_homologado) * 100
    concentracao_top10 = top_forn["pct_participacao"].sum()
    max_v = top_forn["valor_total_homologado"].max()

    c1, c2 = st.columns([1, 3])
    with c1:
        st.markdown(f"<div class='metric-card'><div class='metric-title'>Concentração Top 10</div><div class='metric-value'>{concentracao_top10:.2f}%</div></div>", unsafe_allow_html=True)
        st.markdown(f"<div class='metric-card' style='margin-top:15px;'><div class='metric-title'>Volume do Top 10</div><div class='metric-value'>R$ {top_forn['valor_total_homologado'].sum()/1e9:.2f} Bi</div></div>", unsafe_allow_html=True)
    with c2:
        fig = px.bar(
            top_forn, 
            x="valor_total_homologado", 
            y="nome_fornecedor", 
            orientation="h", 
            title="Top 10 Fornecedores por Volume Financeiro", 
            labels={"valor_total_homologado": "Volume Homologado (R$)", "nome_fornecedor": "Fornecedor"},
            text=top_forn["valor_total_homologado"].apply(lambda x: f"R$ {x/1e6:.1f}M"),
            color="valor_total_homologado", 
            color_continuous_scale=["#0f766e", "#14b8a6", "#2dd4bf"]
        )
        fig.update_traces(textposition='outside', textfont=FONT_LABELS)
        fig.update_layout(yaxis={'categoryorder': 'total ascending'}, coloraxis_showscale=False)
        fig.update_xaxes(range=[0, max_v * 1.20])
        aplicar_layout_executivo(fig)
        st.plotly_chart(fig, use_container_width=True)

    st.warning(f"**Risco de Concentração:** Apenas 10 empresas detêm {concentracao_top10:.2f}% dos recursos homologados (R$ {top_forn['valor_total_homologado'].sum()/1e9:.2f} Bi). Recomenda-se acompanhamento de auditoria contra risco de dependência e concentração.")

# --- PÁGINA 3: EFICÁCIA POR MODALIDADE ---
elif pagina == "3️⃣ Eficácia por Modalidade":
    st.header("Pergunta 3: Qual modalidade economiza mais e qual movimenta mais?")
    
    if filtro_perfil != "Todos":
        st.markdown(f"<span class='filter-badge'>Filtro Ativo: {filtro_perfil}</span>", unsafe_allow_html=True)
        
    df_mod = fato.merge(dim_modalidade, on="sk_modalidade")
    df_mod["est_comp"] = df_mod["valor_total_estimado"].where(df_mod["comparavel"] == 1, 0.0)
    df_mod["eco_comp"] = df_mod["economia_valor"].where(df_mod["comparavel"] == 1, 0.0)
    
    res_mod = df_mod.groupby("nome_modalidade").agg(
        vol=("valor_total_homologado", "sum"), 
        est=("est_comp", "sum"), 
        eco=("eco_comp", "sum")
    ).reset_index()
    res_mod["desagio"] = (res_mod["eco"] / res_mod["est"] * 100).where(res_mod["est"] > 0, None)
    
    c1, c2 = st.columns(2)
    with c1:
        fig_mod_pie = px.pie(
            res_mod, 
            values="vol", 
            names="nome_modalidade", 
            title="Volume Financeiro por Modalidade", 
            hole=0.45,
            color="nome_modalidade",
            color_discrete_map=COLOR_MAP_MODALIDADE
        )
        fig_mod_pie.update_traces(
            textposition='inside',
            textinfo='percent+label',
            insidetextfont=dict(color="#ffffff", size=11, family="sans-serif")
        )
        aplicar_layout_executivo(fig_mod_pie)
        st.plotly_chart(fig_mod_pie, use_container_width=True)
        
    with c2:
        val_mod = res_mod.dropna(subset=["desagio"]).sort_values("desagio")
        max_d = val_mod["desagio"].max()
        fig_mod_bar = px.bar(
            val_mod, 
            x="desagio", 
            y="nome_modalidade", 
            orientation="h", 
            title="Deságio Médio (%) por Modalidade Licitatória", 
            labels={"desagio": "Deságio (%)", "nome_modalidade": "Modalidade"},
            text=val_mod["desagio"].apply(lambda x: f"{x:.2f}%"), 
            color="nome_modalidade",
            color_discrete_map=COLOR_MAP_MODALIDADE
        )
        fig_mod_bar.update_traces(textposition='outside', textfont=FONT_LABELS)
        fig_mod_bar.update_layout(yaxis={'categoryorder': 'total ascending'}, showlegend=False)
        fig_mod_bar.update_xaxes(range=[0, max_d * 1.20])
        aplicar_layout_executivo(fig_mod_bar)
        st.plotly_chart(fig_mod_bar, use_container_width=True)

    st.info("**Conclusão da Controladoria:** A Concorrência Eletrônica absorve 58,43% do montante total homologado, porém o Pregão Eletrônico atua como a ferramenta de maior eficácia concorrencial (24,02% de deságio). O Credenciamento opera com deságio nulo em conformidade com sua regra de teto de remuneração fixa.")

# --- PÁGINA 4: TEMPO DE CICLO ---
elif pagina == "4️⃣ Tempo de Ciclo":
    st.header("Pergunta 4: Onde as compras demoram mais?")
    
    if filtro_perfil != "Todos":
        st.markdown(f"<span class='filter-badge'>Filtro Ativo: {filtro_perfil}</span>", unsafe_allow_html=True)
        
    ciclo_valido = fato.dropna(subset=["dias_ciclo"])
    c1, c2, c3 = st.columns(3)
    c1.markdown(f"<div class='metric-card'><div class='metric-title'>Ciclo Médio Federal</div><div class='metric-value'>{ciclo_valido['dias_ciclo'].mean():.1f} dias</div></div>", unsafe_allow_html=True)
    c2.markdown(f"<div class='metric-card'><div class='metric-title'>Ciclo Máximo</div><div class='metric-value'>{ciclo_valido['dias_ciclo'].max():.0f} dias</div></div>", unsafe_allow_html=True)
    c3.markdown(f"<div class='metric-card'><div class='metric-title'>Certames Sem Ciclo (Invertidos)</div><div class='metric-value'>{fato['dias_ciclo'].isna().sum()}</div></div>", unsafe_allow_html=True)

    df_org = fato.merge(dim_orgao, on="sk_orgao")
    org_ciclo = df_org.groupby("nome_orgao").agg(qtd=("dias_ciclo", "count"), media=("dias_ciclo", "mean")).reset_index()
    lentos = org_ciclo[org_ciclo["qtd"] >= 5].sort_values("media", ascending=False).head(10)
    max_m = lentos["media"].max()
    
    st.markdown("<br>", unsafe_allow_html=True)
    fig_ciclo = px.bar(
        lentos, 
        x="media", 
        y="nome_orgao", 
        orientation="h", 
        title="Top 10 Órgãos com Maior Duração Média (Mínimo de 5 certames)", 
        labels={"media": "Duração Média (dias)", "nome_orgao": "Órgão Licitante"},
        text=lentos["media"].apply(lambda x: f"{x:.1f} dias"), 
        color="media", 
        color_continuous_scale=["#b91c1c", "#dc2626", "#ef4444"]
    )
    fig_ciclo.update_traces(textposition='outside', textfont=FONT_LABELS)
    fig_ciclo.update_layout(yaxis={'categoryorder': 'total ascending'}, coloraxis_showscale=False)
    fig_ciclo.update_xaxes(range=[0, max_m * 1.20])
    aplicar_layout_executivo(fig_ciclo)
    st.plotly_chart(fig_ciclo, use_container_width=True)

    st.info("**Conclusão da Controladoria:** A duração média federal situa-se em 48,1 dias; todavia, instituições de ensino superior e conselhos de fiscalização superam 200 dias de tramitação interna, apontando gargalos processuais na fase preparatória dos editais.")

# --- PÁGINA 5: DISTRIBUIÇÃO REGIONAL ---
elif pagina == "5️⃣ Distribuição Regional":
    st.header("Pergunta 5: Onde se gasta mais e onde se consegue mais desconto?")
    
    if filtro_perfil != "Todos":
        st.markdown(f"<span class='filter-badge'>Filtro Ativo: {filtro_perfil}</span>", unsafe_allow_html=True)
        
    df_loc = fato.merge(dim_localidade, on="sk_localidade")
    df_loc["est_comp"] = df_loc["valor_total_estimado"].where(df_loc["comparavel"] == 1, 0.0)
    df_loc["eco_comp"] = df_loc["economia_valor"].where(df_loc["comparavel"] == 1, 0.0)
    
    # 1. Visão por Macrorregião
    reg = df_loc.groupby("regiao").agg(vol=("valor_total_homologado", "sum"), est=("est_comp", "sum"), eco=("eco_comp", "sum")).reset_index()
    reg["desagio"] = (reg["eco"] / reg["est"]) * 100
    max_rv = reg["vol"].max()
    max_rd = reg["desagio"].max()
    
    c1, c2 = st.columns(2)
    with c1:
        fig_r1 = px.bar(
            reg.sort_values("vol"), 
            x="vol", 
            y="regiao", 
            orientation="h", 
            title="Volume Homologado por Macrorregião", 
            labels={"vol": "Volume (R$)", "regiao": "Região"},
            text=reg.sort_values("vol")["vol"].apply(lambda x: f"R$ {x/1e9:.2f} Bi"), 
            color="vol", 
            color_continuous_scale=["#0369a1", "#0284c7", "#38bdf8"]
        )
        fig_r1.update_traces(textposition='outside', textfont=FONT_LABELS)
        fig_r1.update_layout(coloraxis_showscale=False, yaxis={'categoryorder': 'total ascending'})
        fig_r1.update_xaxes(range=[0, max_rv * 1.25])
        aplicar_layout_executivo(fig_r1)
        st.plotly_chart(fig_r1, use_container_width=True)
        
    with c2:
        fig_r2 = px.bar(
            reg.sort_values("desagio"), 
            x="desagio", 
            y="regiao", 
            orientation="h", 
            title="Deságio Médio (%) por Macrorregião", 
            labels={"desagio": "Deságio Médio (%)", "regiao": "Região"},
            text=reg.sort_values("desagio")["desagio"].apply(lambda x: f"{x:.2f}%"), 
            color="desagio", 
            color_continuous_scale=["#047857", "#059669", "#10b981"]
        )
        fig_r2.update_traces(textposition='outside', textfont=FONT_LABELS)
        fig_r2.update_layout(coloraxis_showscale=False, yaxis={'categoryorder': 'total ascending'})
        fig_r2.update_xaxes(range=[0, max_rd * 1.25])
        aplicar_layout_executivo(fig_r2)
        st.plotly_chart(fig_r2, use_container_width=True)

    # 2. Visão por Unidade Federativa (UF)
    st.markdown("### Top 10 Estados (UFs) em Despesa Homologada")
    uf_df = df_loc.groupby(["uf_sigla", "regiao"]).agg(
        vol=("valor_total_homologado", "sum"),
        itens=("numero_item", "count"),
        est=("est_comp", "sum"),
        eco=("eco_comp", "sum")
    ).reset_index()
    uf_df["desagio"] = ((uf_df["eco"] / uf_df["est"]) * 100).where(uf_df["est"] > 0, 0.0)
    top10_uf = uf_df.sort_values("vol", ascending=False).head(10)
    max_uf = top10_uf["vol"].max()
    
    fig_uf = px.bar(
        top10_uf, 
        x="uf_sigla", 
        y="vol", 
        color="regiao", 
        title="Volume Homologado nos 10 Principais Estados (com Deságio no Tooltip)", 
        labels={"vol": "Volume Homologado (R$)", "uf_sigla": "Estado (UF)", "regiao": "Região"},
        text=top10_uf["vol"].apply(lambda x: f"R$ {x/1e6:.0f}M"),
        custom_data=["desagio", "itens"]
    )
    fig_uf.update_traces(
        textposition='outside',
        textfont=FONT_LABELS,
        hovertemplate="<b>UF: %{x}</b><br>Volume: R$ %{y:,.2f}<br>Deságio: %{customdata[0]:.2f}%<br>Itens: %{customdata[1]}"
    )
    fig_uf.update_layout(height=430)
    fig_uf.update_yaxes(range=[0, max_uf * 1.20])
    aplicar_layout_executivo(fig_uf)
    st.plotly_chart(fig_uf, use_container_width=True)

    st.info("**Conclusão da Controladoria:** O Distrito Federal centraliza 38,98% do orçamento federal em virtude das compras dos ministérios e órgãos superiores. Em termos de economicidade, a Região Norte alcançou o maior índice de desconto do país (21,43%).")

# --- PÁGINA 6: PERFIL DOS GASTOS ---
elif pagina == "6️⃣ Perfil dos Gastos":
    st.header("Pergunta 6: Em que o dinheiro público é gasto?")
    
    if filtro_perfil != "Todos":
        st.markdown(f"<span class='filter-badge'>Filtro Ativo: {filtro_perfil}</span>", unsafe_allow_html=True)
        
    perfil = fato.groupby("perfil_gasto").agg(itens=("numero_item", "count"), vol=("valor_total_homologado", "sum")).reset_index()
    perfil["ticket"] = perfil["vol"] / perfil["itens"]
    max_t = perfil["ticket"].max()
    
    c1, c2 = st.columns(2)
    with c1:
        fig_p1 = px.pie(
            perfil, 
            values="vol", 
            names="perfil_gasto", 
            title="Divisão do Orçamento por Categoria", 
            hole=0.45,
            color="perfil_gasto",
            color_discrete_map=COLOR_MAP_PERFIL
        )
        fig_p1.update_traces(
            textposition='inside',
            textinfo='percent+label',
            insidetextfont=dict(color="#ffffff", size=11, family="sans-serif")
        )
        aplicar_layout_executivo(fig_p1)
        st.plotly_chart(fig_p1, use_container_width=True)
        
    with c2:
        fig_p2 = px.bar(
            perfil, 
            x="perfil_gasto", 
            y="ticket", 
            title="Ticket Médio por Linha Contratual (R$)", 
            labels={"ticket": "Ticket Médio (R$)", "perfil_gasto": "Perfil"},
            text=perfil["ticket"].apply(lambda x: f"R$ {x/1e6:.2f}M"), 
            color="perfil_gasto", 
            color_discrete_map=COLOR_MAP_PERFIL
        )
        fig_p2.update_traces(textposition='outside', textfont=FONT_LABELS)
        fig_p2.update_layout(showlegend=False, yaxis_title="Ticket Médio (R$)")
        fig_p2.update_yaxes(range=[0, max_t * 1.20])
        aplicar_layout_executivo(fig_p2)
        st.plotly_chart(fig_p2, use_container_width=True)

    st.info("**Conclusão da Controladoria:** Obras e Engenharia concentram a maior parte do volume financeiro (60,8% do montante; ticket médio de R$ 5,06 mi), ao passo que a aquisição de Bens lidera em volume físico de contratações (54% dos itens da fato).")