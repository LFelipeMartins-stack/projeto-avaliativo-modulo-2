-- =============================================================================
-- 02_perguntas.sql
-- =============================================================================

-- =============================================================================
-- PERGUNTA 1: ECONOMIA GLOBAL DO PODER PÚBLICO
-- Qual é o percentual e o valor financeiro nominal economizado pelo governo?
-- Regra 6: Apenas itens comparáveis (comparavel = 1) entram no cálculo.
-- Prova Real: 6.126 itens, R$ 8.044.498.805,74 homologados, 5.457 comparáveis,
--             R$ 992.861.686,95 de economia nominal e 14,46% de deságio.
-- =============================================================================
SELECT 
    COUNT(*) AS total_itens_fato,
    SUM(valor_total_homologado) AS volume_homologado_total,
    SUM(CASE WHEN comparavel = 1 THEN valor_total_estimado ELSE 0 END) AS valor_estimado_comparavel,
    SUM(CASE WHEN comparavel = 1 THEN valor_total_homologado ELSE 0 END) AS valor_homologado_comparavel,
    SUM(CASE WHEN comparavel = 1 THEN economia_valor ELSE 0 END) AS economia_nominal_total,
    ROUND(
        100.0 * SUM(CASE WHEN comparavel = 1 THEN economia_valor ELSE 0 END) / 
        NULLIF(SUM(CASE WHEN comparavel = 1 THEN valor_total_estimado ELSE 0 END), 0), 
        2
    ) AS economia_percentual,
    SUM(comparavel) AS total_itens_comparaveis,
    ROUND(100.0 * SUM(comparavel) / COUNT(*), 2) AS pct_itens_comparaveis
FROM fato_item_contratado;


-- =============================================================================
-- PERGUNTA 2: CONCENTRAÇÃO E RISCO DE FORNECEDORES
-- Quem são os maiores fornecedores em volume financeiro e qual percentual do 
-- orçamento público está concentrado neles?
-- =============================================================================
-- 2.1. Top 10 Maiores Fornecedores
SELECT 
    d.ni_fornecedor,
    d.nome_fornecedor,
    d.tipo_pessoa,
    d.porte,
    COUNT(f.numero_item) AS total_itens_vencidos,
    SUM(f.valor_total_homologado) AS volume_fornecedor,
    ROUND(
        100.0 * SUM(f.valor_total_homologado) / 
        (SELECT SUM(valor_total_homologado) FROM fato_item_contratado), 
        2
    ) AS pct_participacao_orcamento
FROM fato_item_contratado f
JOIN dim_fornecedor d ON f.sk_fornecedor = d.sk_fornecedor
GROUP BY d.ni_fornecedor, d.nome_fornecedor, d.tipo_pessoa, d.porte
ORDER BY volume_fornecedor DESC
LIMIT 10;

-- 2.2. Concentração Acumulada do Top 10 Fornecedores
WITH top10 AS (
    SELECT 
        f.sk_fornecedor,
        SUM(f.valor_total_homologado) AS volume_top
    FROM fato_item_contratado f
    GROUP BY f.sk_fornecedor
    ORDER BY volume_top DESC
    LIMIT 10
)
SELECT 
    SUM(volume_top) AS volume_acumulado_top10,
    ROUND(
        100.0 * SUM(volume_top) / 
        (SELECT SUM(valor_total_homologado) FROM fato_item_contratado), 
        2
    ) AS concentracao_top10_percentual
FROM top10;


-- =============================================================================
-- PERGUNTA 3: EFICÁCIA POR MODALIDADE LICITATÓRIA
-- Quais modalidades trazem maior deságio/economia e quais concentram mais volume?
-- =============================================================================
WITH base_modalidades AS (
    SELECT 
        m.modalidade_id,
        m.nome_modalidade,
        COUNT(f.numero_item) AS qtd_itens,
        SUM(f.valor_total_homologado) AS volume_homologado,
        SUM(CASE WHEN f.comparavel = 1 THEN f.valor_total_estimado ELSE 0 END) AS estimado_comp,
        SUM(CASE WHEN f.comparavel = 1 THEN f.economia_valor ELSE 0 END) AS economia_comp
    FROM fato_item_contratado f
    JOIN dim_modalidade m ON f.sk_modalidade = m.sk_modalidade
    GROUP BY m.modalidade_id, m.nome_modalidade
)
SELECT 
    modalidade_id,
    nome_modalidade,
    qtd_itens,
    volume_homologado,
    ROUND(100.0 * volume_homologado / (SELECT SUM(valor_total_homologado) FROM fato_item_contratado), 2) AS pct_volume,
    economia_comp AS economia_nominal,
    ROUND(100.0 * economia_comp / NULLIF(estimado_comp, 0), 2) AS desagio_percentual,
    ROUND(
        (100.0 * economia_comp / NULLIF(estimado_comp, 0)) - 
        (100.0 * (SELECT SUM(CASE WHEN comparavel = 1 THEN economia_valor ELSE 0 END) FROM fato_item_contratado) / 
                 (SELECT SUM(CASE WHEN comparavel = 1 THEN valor_total_estimado ELSE 0 END) FROM fato_item_contratado)),
        2
    ) AS desagio_vs_media_geral_pp
FROM base_modalidades
ORDER BY volume_homologado DESC;


-- =============================================================================
-- PERGUNTA 4: TEMPO DO CICLO DE COMPRAS POR ÓRGÃO
-- Qual a duração média (em dias) entre edital e homologação por órgão?
-- Regra 10: Agrupamento por nome padronizado de órgão e filtro HAVING >= 5 itens com ciclo.
-- =============================================================================
SELECT 
    o.nome_orgao,
    COUNT(DISTINCT o.cnpj_orgao) AS qtd_unidades_compradoras,
    COUNT(*) AS total_itens,
    COUNT(f.dias_ciclo) AS itens_com_ciclo,
    COUNT(*) - COUNT(f.dias_ciclo) AS itens_sem_ciclo,
    ROUND(AVG(f.dias_ciclo), 1) AS ciclo_medio_dias,
    MAX(f.dias_ciclo) AS ciclo_maximo_dias,
    MIN(f.dias_ciclo) AS ciclo_minimo_dias
FROM fato_item_contratado f
JOIN dim_orgao o ON f.sk_orgao = o.sk_orgao
GROUP BY o.nome_orgao
HAVING COUNT(f.dias_ciclo) >= 5
ORDER BY ciclo_medio_dias DESC;


-- =============================================================================
-- PERGUNTA 5: DISTRIBUIÇÃO REGIONAL
-- Quais estados e regiões concentram as maiores despesas e melhores descontos?
-- =============================================================================
-- 5.1. Agrupamento por Região
SELECT 
    l.regiao,
    COUNT(DISTINCT f.sk_orgao) AS qtd_unidades_compradoras,
    COUNT(f.numero_item) AS qtd_itens,
    SUM(f.valor_total_homologado) AS volume_homologado,
    ROUND(100.0 * SUM(f.valor_total_homologado) / (SELECT SUM(valor_total_homologado) FROM fato_item_contratado), 2) AS pct_volume,
    SUM(CASE WHEN f.comparavel = 1 THEN f.economia_valor ELSE 0 END) AS economia_nominal,
    ROUND(
        100.0 * SUM(CASE WHEN f.comparavel = 1 THEN f.economia_valor ELSE 0 END) / 
        NULLIF(SUM(CASE WHEN f.comparavel = 1 THEN f.valor_total_estimado ELSE 0 END), 0), 
        2
    ) AS desagio_percentual
FROM fato_item_contratado f
JOIN dim_localidade l ON f.sk_localidade = l.sk_localidade
GROUP BY l.regiao
ORDER BY volume_homologado DESC;

-- 5.2. Agrupamento por Estado (UF)
SELECT 
    l.uf_sigla,
    l.uf_nome,
    l.regiao,
    COUNT(DISTINCT f.sk_orgao) AS qtd_unidades_compradoras,
    COUNT(f.numero_item) AS qtd_itens,
    SUM(f.valor_total_homologado) AS volume_homologado,
    ROUND(100.0 * SUM(f.valor_total_homologado) / (SELECT SUM(valor_total_homologado) FROM fato_item_contratado), 2) AS pct_volume,
    SUM(CASE WHEN f.comparavel = 1 THEN f.economia_valor ELSE 0 END) AS economia_nominal,
    ROUND(
        100.0 * SUM(CASE WHEN f.comparavel = 1 THEN f.economia_valor ELSE 0 END) / 
        NULLIF(SUM(CASE WHEN f.comparavel = 1 THEN f.valor_total_estimado ELSE 0 END), 0), 
        2
    ) AS desagio_percentual
FROM fato_item_contratado f
JOIN dim_localidade l ON f.sk_localidade = l.sk_localidade
GROUP BY l.uf_sigla, l.uf_nome, l.regiao
ORDER BY volume_homologado DESC;


-- =============================================================================
-- PERGUNTA 6: PERFIL DOS GASTOS
-- Como os recursos se distribuem entre bens, serviços e obras e engenharia?
-- Prova Real: Obras e engenharia 60,8% (967 itens) · Serviços 36,6% (1.849 itens) · Bens 2,6% (3.310 itens)
-- =============================================================================
SELECT 
    perfil_gasto,
    COUNT(*) AS total_itens,
    SUM(valor_total_homologado) AS volume_homologado,
    ROUND(
        100.0 * SUM(valor_total_homologado) / 
        (SELECT SUM(valor_total_homologado) FROM fato_item_contratado), 
        1
    ) AS pct_volume,
    ROUND(SUM(valor_total_homologado) / COUNT(*), 2) AS ticket_medio_por_item,
    SUM(CASE WHEN comparavel = 1 THEN economia_valor ELSE 0 END) AS economia_nominal,
    ROUND(
        100.0 * SUM(CASE WHEN comparavel = 1 THEN economia_valor ELSE 0 END) / 
        NULLIF(SUM(CASE WHEN comparavel = 1 THEN valor_total_estimado ELSE 0 END), 0), 
        2
    ) AS desagio_percentual
FROM fato_item_contratado
GROUP BY perfil_gasto
ORDER BY volume_homologado DESC;