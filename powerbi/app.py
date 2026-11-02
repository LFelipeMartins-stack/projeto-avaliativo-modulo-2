import sys
from pathlib import Path

# Adiciona a raiz do projeto ao path de importação
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import streamlit as st
import pandas as pd
import plotly.express as px
from sqlalchemy import create_engine
from src import config

# Configuração da página executiva
st.set_page_config(
    page_title="Painel de Auditoria PNCP 2025",
    page_icon="⚖️",
    layout="wide"
)

# Conexão com o banco local PostgreSQL via psycopg2
@st.cache_resource
def obter_conexao():
    url = (
        f"postgresql+psycopg2://{config.PG_CONFIG['user']}:{config.PG_CONFIG['password']}@"
        f"{config.PG_CONFIG['host']}:{config.PG_CONFIG['port']}/{config.PG_DATABASE}"
    )
    return create_engine(url)

engine = obter_conexao()

@st.cache_data
def carregar_dados():
    fato = pd.read_sql("SELECT * FROM fato_item_contratado", engine)
    orgaos = pd.read_sql("SELECT * FROM dim_orgao", engine)
    fornecedores = pd.read_sql("SELECT * FROM dim_fornecedor", engine)
    modalidades = pd.read_sql("SELECT * FROM dim_modalidade", engine)
    localidades = pd.read_sql("SELECT * FROM dim_localidade", engine)
    return fato, orgaos, fornecedores, modalidades, localidades

fato, dim_orgao, dim_fornecedor, dim_modalidade, dim_localidade = carregar_dados()

st.title("🏛️ Auditoria de Contratações Públicas Federais (PNCP 2025)")
st.markdown("Painel de inteligência governamental para controle externo e auditoria contínua.")

# Navegação por Abas (Storytelling das 6 Perguntas da Controladoria)
abas = st.tabs([
    "1. Economia Global", 
    "2. Fornecedores e Risco", 
    "3. Eficácia por Modalidade", 
    "4. Ciclo de Compras", 
    "5. Distribuição Regional", 
    "6. Perfil dos Gastos"
])

# -----------------------------------------------------------------------------
# ABA 1: ECONOMIA GLOBAL
# -----------------------------------------------------------------------------
with abas[0]:
    st.header("Pergunta 1: Quanto o governo economizou?")
    
    comp = fato[fato["comparavel"] == 1]
    vol_homologado = fato["valor_total_homologado"].sum()
    est_comp = comp["valor_total_estimado"].sum()
    hom_comp = comp["valor_total_homologado"].sum()
    economia_rs = est_comp - hom_comp
    economia_pct = (economia_rs / est_comp) * 100
    pct_comp = (len(comp) / len(fato)) * 100

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Volume Homologado", f"R$ {vol_homologado:,.2f}")
    col2.metric("Economia Nominal", f"R$ {economia_rs:,.2f}")
    col3.metric("Economia %", f"{economia_pct:.2f}%")
    col4.metric("% Itens Comparáveis", f"{pct_comp:.2f}%")

    st.info(
        "**Conclusão da Controladoria:** A Administração Federal obteve economia de R$ 992,86 mi "
        "(14,46% de deságio) sobre a base comparável (89,08% dos itens), evidenciando a eficácia "
        "dos certames concorrenciais."
    )

# -----------------------------------------------------------------------------
# ABA 2: FORNECEDORES
# -----------------------------------------------------------------------------
with abas[1]:
    st.header("Pergunta 2: Quem concentra o orçamento? É um risco?")
    
    df_forn = fato.merge(dim_fornecedor, on="sk_fornecedor")
    top_forn = (
        df_forn.groupby(["ni_fornecedor", "nome_fornecedor", "porte"])["valor_total_homologado"]
        .sum()
        .reset_index()
        .sort_values(by="valor_total_homologado", ascending=False)
    )
    top_forn["pct_participacao"] = (top_forn["valor_total_homologado"] / vol_homologado) * 100
    top10 = top_forn.head(10)
    concentracao_top10 = top10["pct_participacao"].sum()

    st.metric("Concentração Top 10 Fornecedores", f"{concentracao_top10:.2f}%")

    fig_forn = px.bar(
        top10,
        x="valor_total_homologado",
        y="nome_fornecedor",
        orientation="h",
        labels={"valor_total_homologado": "Volume Homologado (R$)", "nome_fornecedor": "Fornecedor"},
        title="Top 10 Fornecedores por Volume Financeiro"
    )
    fig_forn.update_layout(yaxis={'categoryorder': 'total ascending'})
    st.plotly_chart(fig_forn, width="stretch")

    st.warning(
        f"**Conclusão da Controladoria:** Risco de concentração elevado: apenas 10 grupos econômicos "
        f"detêm {concentracao_top10:.2f}% do montante total homologado (R$ 3,33 bi), exigindo "
        f"monitoramento preventivo de dependência contratual."
    )

# -----------------------------------------------------------------------------
# ABA 3: MODALIDADES
# -----------------------------------------------------------------------------
with abas[2]:
    st.header("Pergunta 3: Qual modalidade economiza mais e qual movimenta mais?")
    
    df_mod = fato.merge(dim_modalidade, on="sk_modalidade")
    df_mod["est_comp"] = df_mod["valor_total_estimado"].where(df_mod["comparavel"] == 1, 0.0)
    df_mod["eco_comp"] = df_mod["economia_valor"].where(df_mod["comparavel"] == 1, 0.0)

    res_mod = df_mod.groupby("nome_modalidade").agg(
        volume_homologado=("valor_total_homologado", "sum"),
        itens=("numero_item", "count"),
        estimado_comp=("est_comp", "sum"),
        economia_rs=("eco_comp", "sum")
    ).reset_index()

    res_mod["pct_volume"] = (res_mod["volume_homologado"] / vol_homologado) * 100
    res_mod["desagio_pct"] = (res_mod["economia_rs"] / res_mod["estimado_comp"]).where(res_mod["estimado_comp"] > 0, None) * 100

    col_m1, col_m2 = st.columns(2)
    with col_m1:
        fig_mod_vol = px.pie(res_mod, values="volume_homologado", names="nome_modalidade", title="Volume por Modalidade")
        st.plotly_chart(fig_mod_vol, width="stretch")
    with col_m2:
        res_mod_val = res_mod.dropna(subset=["desagio_pct"])
        fig_mod_des = px.bar(res_mod_val, x="nome_modalidade", y="desagio_pct", title="Deságio (%) por Modalidade")
        st.plotly_chart(fig_mod_des, width="stretch")

    st.info(
        "**Conclusão da Controladoria:** A Concorrência Eletrônica absorve 58,43% dos recursos, "
        "mas o Pregão Eletrônico traz maior eficiência relativa com 24,02% de deságio."
    )

# -----------------------------------------------------------------------------
# ABA 4: CICLO DE COMPRAS
# -----------------------------------------------------------------------------
with abas[3]:
    st.header("Pergunta 4: Onde as compras demoram mais?")
    
    ciclo_valido = fato.dropna(subset=["dias_ciclo"])
    c1, c2, c3 = st.columns(3)
    c1.metric("Ciclo Médio Geral", f"{ciclo_valido['dias_ciclo'].mean():.1f} dias")
    c2.metric("Ciclo Máximo", f"{ciclo_valido['dias_ciclo'].max():.0f} dias")
    c3.metric("Itens sem Ciclo (Invertidos/Nulos)", f"{fato['dias_ciclo'].isna().sum()}")

    df_org = fato.merge(dim_orgao, on="sk_orgao")
    org_ciclo = df_org.groupby("nome_orgao").agg(
        itens_com_ciclo=("dias_ciclo", "count"),
        ciclo_medio=("dias_ciclo", "mean")
    ).reset_index()

    org_lentos = org_ciclo[org_ciclo["itens_com_ciclo"] >= 5].sort_values(by="ciclo_medio", ascending=False).head(10)
    fig_org = px.bar(org_lentos, x="ciclo_medio", y="nome_orgao", orientation="h", title="Top 10 Órgãos com Maior Ciclo Médio (≥ 5 certames)")
    fig_org.update_layout(yaxis={'categoryorder': 'total ascending'})
    st.plotly_chart(fig_org, width="stretch")

    st.info(
        "**Conclusão da Controladoria:** Ciclo médio federal de 48,1 dias; universidades federais "
        "e conselhos de classe lideram o tempo de tramitação, superando 200 dias."
    )

# -----------------------------------------------------------------------------
# ABA 5: REGIONAL
# -----------------------------------------------------------------------------
with abas[4]:
    st.header("Pergunta 5: Onde se gasta mais e onde se consegue mais desconto?")
    
    df_loc = fato.merge(dim_localidade, on="sk_localidade")
    df_loc["est_comp"] = df_loc["valor_total_estimado"].where(df_loc["comparavel"] == 1, 0.0)
    df_loc["eco_comp"] = df_loc["economia_valor"].where(df_loc["comparavel"] == 1, 0.0)

    reg_analise = df_loc.groupby("regiao").agg(
        volume=("valor_total_homologado", "sum"),
        estimado_comp=("est_comp", "sum"),
        economia_nominal=("eco_comp", "sum")
    ).reset_index()

    reg_analise["desagio"] = (reg_analise["economia_nominal"] / reg_analise["estimado_comp"]) * 100
    reg_analise = reg_analise.sort_values(by="volume", ascending=False)

    col_r1, col_r2 = st.columns(2)
    with col_r1:
        st.plotly_chart(px.bar(reg_analise, x="regiao", y="volume", title="Volume Homologado por Região"), width="stretch")
    with col_r2:
        st.plotly_chart(px.bar(reg_analise, x="regiao", y="desagio", title="Deságio Médio (%) por Região"), width="stretch")

    st.info(
        "**Conclusão da Controladoria:** Centro-Oeste e Nordeste somam 67,25% dos gastos totais. "
        "A Região Norte apresentou o maior índice de desconto (21,43%)."
    )

# -----------------------------------------------------------------------------
# ABA 6: PERFIL DE GASTO
# -----------------------------------------------------------------------------
with abas[5]:
    st.header("Pergunta 6: Em que o dinheiro público é gasto?")
    
    perfil = fato.groupby("perfil_gasto").agg(
        total_itens=("numero_item", "count"),
        volume_homologado=("valor_total_homologado", "sum")
    ).reset_index()
    perfil["pct_volume"] = (perfil["volume_homologado"] / vol_homologado) * 100
    perfil["ticket_medio"] = perfil["volume_homologado"] / perfil["total_itens"]

    col_p1, col_p2 = st.columns(2)
    with col_p1:
        st.plotly_chart(px.pie(perfil, values="volume_homologado", names="perfil_gasto", title="Divisão Orçamentária por Perfil"), width="stretch")
    with col_p2:
        st.plotly_chart(px.bar(perfil, x="perfil_gasto", y="ticket_medio", title="Ticket Médio por Item (R$)"), width="stretch")

    st.info(
        "**Conclusão da Controladoria:** Obras e Engenharia representam 60,8% do volume financeiro "
        "com ticket médio de R$ 5,06 mi, enquanto Bens respondem por 54% dos itens licitados."
    )