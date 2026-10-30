-- =============================================================================
-- DDL: MODELAGEM DIMENSIONAL ESTRELA (POSTGRESQL)
-- =============================================================================

-- -----------------------------------------------------------------------------
-- 1. DIMENSÕES (Criadas primeiro para suportar as FKs da Fato)
-- -----------------------------------------------------------------------------

-- Dimensão Órgão: Quem comprou (Unidade compradora)
CREATE TABLE dim_orgao (
    sk_orgao        INTEGER PRIMARY KEY,
    cnpj_orgao      VARCHAR(14) NOT NULL UNIQUE,
    nome_orgao      VARCHAR(255) NOT NULL,
    poder           VARCHAR(50) NOT NULL
);

-- Dimensão Fornecedor: Quem vendeu (PJ, PF ou PE)
CREATE TABLE dim_fornecedor (
    sk_fornecedor   INTEGER PRIMARY KEY,
    ni_fornecedor   VARCHAR(20) NOT NULL UNIQUE,
    nome_fornecedor VARCHAR(255),
    tipo_pessoa     VARCHAR(10),
    porte           VARCHAR(50)
);

-- Dimensão Modalidade: Como comprou (Enquadramento legal do certame)
CREATE TABLE dim_modalidade (
    sk_modalidade   INTEGER PRIMARY KEY,
    modalidade_id   INTEGER NOT NULL UNIQUE,
    nome_modalidade VARCHAR(100) NOT NULL
);

-- Dimensão Localidade: Onde comprou (Unidade Federativa e Macrorregião)
CREATE TABLE dim_localidade (
    sk_localidade   INTEGER PRIMARY KEY,
    uf_sigla        VARCHAR(2) NOT NULL UNIQUE,
    uf_nome         VARCHAR(50) NOT NULL,
    regiao          VARCHAR(30) NOT NULL
);

-- -----------------------------------------------------------------------------
-- 2. TABELA FATO: O que foi comprado (Grão: 1 linha por item com vencedor)
-- -----------------------------------------------------------------------------

CREATE TABLE fato_item_contratado (
    sk_fato                     SERIAL PRIMARY KEY,
    numero_controle_pncp        VARCHAR(50) NOT NULL,
    numero_item                 INTEGER NOT NULL,
    
    -- Chaves Estrangeiras (Integridade Referencial Estrita)
    sk_orgao                    INTEGER NOT NULL REFERENCES dim_orgao(sk_orgao),
    sk_fornecedor               INTEGER NOT NULL REFERENCES dim_fornecedor(sk_fornecedor),
    sk_modalidade               INTEGER NOT NULL REFERENCES dim_modalidade(sk_modalidade),
    sk_localidade               INTEGER NOT NULL REFERENCES dim_localidade(sk_localidade),
    
    -- Atributos Temporais
    data_publicacao             DATE NOT NULL,
    data_homologacao            DATE, -- Nulo quando há violação cronológica (Regra 7)
    
    -- Descrição e Classificação
    descricao_item              TEXT,
    perfil_gasto                VARCHAR(50) NOT NULL,
    
    -- Métricas e Valores
    quantidade                  DECIMAL(18,4) NOT NULL,
    valor_unitario_estimado     DECIMAL(18,4) NOT NULL,
    valor_total_estimado        DECIMAL(18,2) NOT NULL,
    valor_unitario_homologado   DECIMAL(18,4) NOT NULL,
    valor_total_homologado      DECIMAL(18,2) NOT NULL,
    
    -- Métricas Derivadas
    comparavel                  SMALLINT NOT NULL, -- 1 ou 0
    economia_valor              DECIMAL(18,2),    -- Nulo ou 0.0 quando não comparável
    dias_ciclo                  INTEGER,          -- Nulo quando não há homologação válida
    
    -- Restrições de Unicidade e Barreira de Qualidade (CHECKs)
    CONSTRAINT uq_fato_item UNIQUE (numero_controle_pncp, numero_item),
    CONSTRAINT chk_quantidade CHECK (quantidade > 0),
    CONSTRAINT chk_precos_unitarios CHECK (valor_unitario_estimado > 0 AND valor_unitario_homologado > 0),
    CONSTRAINT chk_totais_nao_negativos CHECK (valor_total_estimado >= 0 AND valor_total_homologado >= 0)
);

-- -----------------------------------------------------------------------------
-- 3. ÍNDICES DE PERFORMANCE (Otimização para Joins e Consultas Analíticas)
-- -----------------------------------------------------------------------------
CREATE INDEX idx_fato_orgao ON fato_item_contratado(sk_orgao);
CREATE INDEX idx_fato_fornecedor ON fato_item_contratado(sk_fornecedor);
CREATE INDEX idx_fato_modalidade ON fato_item_contratado(sk_modalidade);
CREATE INDEX idx_fato_localidade ON fato_item_contratado(sk_localidade);
CREATE INDEX idx_fato_data_pub ON fato_item_contratado(data_publicacao);
CREATE INDEX idx_fato_data_hom ON fato_item_contratado(data_homologacao);