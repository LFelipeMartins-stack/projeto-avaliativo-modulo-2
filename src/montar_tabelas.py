"""
montar_tabelas.py  -  DOS CSVs BRUTOS ATE A FATO E AS 4 DIMENSOES
========================================================================================================
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import pandas as pd
from src import config, limpeza

# Tabelas de apoio (estao no anexo do enunciado, secao 7)
MODALIDADES = {4: "Concorrência - Eletrônica", 5: "Concorrência - Presencial", 6: "Pregão - Eletrônico",
               7: "Pregão - Presencial", 8: "Dispensa", 9: "Inexigibilidade", 12: "Credenciamento"}
REGIAO = {"AC": "Norte", "AM": "Norte", "AP": "Norte", "PA": "Norte", "RO": "Norte", "RR": "Norte", "TO": "Norte",
          "AL": "Nordeste", "BA": "Nordeste", "CE": "Nordeste", "MA": "Nordeste", "PB": "Nordeste", "PE": "Nordeste",
          "PI": "Nordeste", "RN": "Nordeste", "SE": "Nordeste", "DF": "Centro-Oeste", "GO": "Centro-Oeste",
          "MS": "Centro-Oeste", "MT": "Centro-Oeste", "ES": "Sudeste", "MG": "Sudeste", "RJ": "Sudeste", "SP": "Sudeste",
          "PR": "Sul", "RS": "Sul", "SC": "Sul"}
PODER = {"E": "Executivo", "L": "Legislativo", "J": "Judiciário", "N": "Não informado"}


def ler(nome):
    """PRONTA. Le o CSV TUDO COMO TEXTO (dtype=str): assim o CNPJ nao perde o zero da esquerda e nada vira NaN sozinho."""
    return pd.read_csv(config.PASTA_RAW / f"{nome}.csv", dtype=str, keep_default_na=False)


def main():
    compras, itens, resultados = ler("compras"), ler("itens"), ler("resultados")
    print(f"Linhas lidas: compras={len(compras)}  itens={len(itens)}  resultados={len(resultados)}   (prova real: 2042 / 7077 / 15896)")

    # =========================================================================================
    # ETAPA 1 - LIMPAR OS 3 ARQUIVOS  (use as funcoes do src/limpeza.py com .map)
    # =========================================================================================
    # --- compras.csv ---
    compras["cnpj_orgao"] = compras["cnpj_orgao"].map(lambda v: limpeza.limpar_documento(v, "PJ"))
    compras["nome_orgao"] = compras["razao_social_orgao"].map(limpeza.padronizar_nome)
    compras["uf_sigla"] = compras["uf_sigla"].map(limpeza.padronizar_nome)
    compras["uf_nome"] = compras["uf_nome"].map(limpeza.padronizar_nome)
    compras["regiao"] = compras["uf_sigla"].map(REGIAO)
    compras["poder"] = compras["poder_id"].map(PODER).fillna("Não informado")
    compras["modalidade_id"] = compras["modalidade_id"].astype(int)
    compras["nome_modalidade"] = compras["modalidade_id"].map(MODALIDADES)
    compras["data_publicacao"] = compras["data_publicacao"].map(limpeza.converter_data)
    compras["objeto_compra"] = compras["objeto_compra"].map(limpeza.limpar_texto)

    # --- itens.csv ---
    itens["descricao_item"] = itens["descricao"].map(limpeza.padronizar_nome)
    itens["material_ou_servico"] = itens["material_ou_servico"].map(limpeza.limpar_texto)
    for coluna in ["quantidade", "valor_unitario_estimado"]:
        itens[coluna] = itens[coluna].map(limpeza.converter_numero)
    itens["sigiloso"] = itens["sigiloso"].str.lower() == "true"
    itens["numero_item"] = itens["numero_item"].astype(int)

    # --- resultados.csv ---
    resultados["numero_item"] = resultados["numero_item"].astype(int)
    resultados["nome_fornecedor"] = resultados["nome_fornecedor"].map(limpeza.padronizar_nome)
    resultados["porte"] = resultados["porte"].map(limpeza.limpar_texto)
    resultados["ni_fornecedor"] = [limpeza.limpar_documento(ni, tipo)
                                   for ni, tipo in zip(resultados["ni_fornecedor"], resultados["tipo_pessoa"])]
    for coluna in ["quantidade_homologada", "valor_unitario_homologado"]:
        resultados[coluna] = resultados[coluna].map(limpeza.converter_numero)
    resultados["data_resultado"] = resultados["data_resultado"].map(limpeza.converter_data)
    resultados["cancelado"] = resultados["data_cancelamento"].str.strip() != ""

    # =========================================================================================
    # ETAPA 2 - UM VENCEDOR POR ITEM  (regra 2)
    # =========================================================================================
    resultados = resultados[~resultados["cancelado"]].copy()
    resultados["ordem"] = pd.to_numeric(resultados["ordem_classificacao_srp"], errors="coerce").fillna(1)
    resultados["sequencial"] = pd.to_numeric(resultados["sequencial_resultado"], errors="coerce").fillna(1)
    resultados = resultados.sort_values(["numero_controle_pncp", "numero_item", "ordem", "sequencial"])
    resultados = resultados.drop_duplicates(["numero_controle_pncp", "numero_item"])

    # =========================================================================================
    # ETAPA 3 - JUNTAR OS 3 ARQUIVOS: SO ENTRAM ITENS COM RESULTADO  (regra 3)
    # =========================================================================================
    fato = itens.merge(resultados, on=["numero_controle_pncp", "numero_item"], how="inner")
    fato = fato.merge(compras, on="numero_controle_pncp")
    print(f"Itens com resultado, antes de rejeitar: {len(fato)}")

    # =========================================================================================
    # ETAPA 4 - VALORES  (regra 5)
    # =========================================================================================
    qtd_homologada = fato["quantidade_homologada"]
    fato["quantidade"] = qtd_homologada.where(qtd_homologada > 0, fato["quantidade"])
    fato["valor_total_estimado"] = (fato["valor_unitario_estimado"] * fato["quantidade"]).round(2)
    fato["valor_total_homologado"] = (fato["valor_unitario_homologado"] * fato["quantidade"]).round(2)

    # =========================================================================================
    # ETAPA 5 - ITENS REJEITADOS  (regra 4)
    # =========================================================================================
    est, hom = fato["valor_total_estimado"], fato["valor_total_homologado"]
    rejeitado = (
        ~(fato["quantidade"] > 0)
        | ~(fato["valor_unitario_estimado"] > 0)
        | ~(fato["valor_unitario_homologado"] > 0)
        | fato["sigiloso"]
        | (est < 1)
        | (hom > 1000 * est)
        | (est > 1e12) | (hom > 1e12)
    )
    print(f"Itens rejeitados (nao entram na fato): {rejeitado.sum()}   (prova real: 99)")
    fato = fato[~rejeitado].copy()

    # =========================================================================================
    # ETAPA 6 - COMPARAVEL E ECONOMIA  (regra 6)
    # =========================================================================================
    est, hom = fato["valor_total_estimado"], fato["valor_total_homologado"]
    razao = hom / est
    fato["comparavel"] = ((fato["modalidade_id"] != 12) & razao.between(0.1, 10)).astype(int)
    fato["economia_valor"] = (est - hom).where(fato["comparavel"] == 1, 0.0).round(2)

    # =========================================================================================
    # ETAPA 7 - CRONOLOGIA  (regra 7)
    # =========================================================================================
    fato["data_homologacao"] = fato["data_resultado"]
    # Compara apenas quando ambas as datas sao validas (evita excecoes com None)
    antes = [
        (h is not None and p is not None and not pd.isna(h) and not pd.isna(p) and h < p)
        for h, p in zip(fato["data_homologacao"], fato["data_publicacao"])
    ]
    fato.loc[antes, "data_homologacao"] = None
    fato["dias_ciclo"] = [
        (h - p).days if h is not None and not pd.isna(h) and p is not None and not pd.isna(p) else None
        for h, p in zip(fato["data_homologacao"], fato["data_publicacao"])
    ]

    # =========================================================================================
    # ETAPA 8 - PERFIL DO GASTO  (regra 8)
    # =========================================================================================
    texto = fato["descricao_item"].fillna("") + " " + fato["objeto_compra"].fillna("").str.upper()
    eh_obra = texto.str.contains(r"\b(?:OBRAS?|CONSTRUÇÃO|CONSTRUCAO|REFORMA|ENGENHARIA)\b", regex=True)
    fato["perfil_gasto"] = "Bens"
    fato.loc[fato["material_ou_servico"].fillna("").str.upper().str.startswith("SERVI"), "perfil_gasto"] = "Serviços"
    fato.loc[eh_obra, "perfil_gasto"] = "Obras e engenharia"

    # =========================================================================================
    # ETAPA 9 - AS 4 DIMENSOES, COM CHAVE SUBSTITUTA (sk_)  (secao 4.3 do enunciado)
    # =========================================================================================
    dim_orgao = fato.drop_duplicates("cnpj_orgao")[["cnpj_orgao", "nome_orgao", "poder"]].reset_index(drop=True)
    dim_orgao.insert(0, "sk_orgao", dim_orgao.index + 1)

    fato["ni_fornecedor"] = fato["ni_fornecedor"].fillna("NAO-INFORMADO")
    dim_fornecedor = fato.drop_duplicates("ni_fornecedor")[["ni_fornecedor", "nome_fornecedor", "tipo_pessoa", "porte"]].reset_index(drop=True)
    dim_fornecedor.insert(0, "sk_fornecedor", dim_fornecedor.index + 1)

    dim_modalidade = fato.drop_duplicates("modalidade_id")[["modalidade_id", "nome_modalidade"]].reset_index(drop=True)
    dim_modalidade.insert(0, "sk_modalidade", dim_modalidade.index + 1)

    dim_localidade = fato.drop_duplicates("uf_sigla")[["uf_sigla", "uf_nome", "regiao"]].reset_index(drop=True)
    dim_localidade.insert(0, "sk_localidade", dim_localidade.index + 1)

    for dim, chave, sk in [(dim_orgao, "cnpj_orgao", "sk_orgao"), (dim_fornecedor, "ni_fornecedor", "sk_fornecedor"),
                           (dim_modalidade, "modalidade_id", "sk_modalidade"), (dim_localidade, "uf_sigla", "sk_localidade")]:
        fato[sk] = fato[chave].map(dict(zip(dim[chave], dim[sk])))

    colunas = ["numero_controle_pncp", "numero_item", "sk_orgao", "sk_fornecedor", "sk_modalidade", "sk_localidade",
               "data_publicacao", "data_homologacao", "descricao_item", "perfil_gasto", "quantidade",
               "valor_unitario_estimado", "valor_total_estimado", "valor_unitario_homologado", "valor_total_homologado",
               "comparavel", "economia_valor", "dias_ciclo"]
    fato = fato[colunas]

    # =========================================================================================
    # ETAPA 10 - SALVAR E CONFERIR (pronto)
    # =========================================================================================
    config.PASTA_PROCESSED.mkdir(parents=True, exist_ok=True)
    for nome, tabela in [("fato_item_contratado", fato), ("dim_orgao", dim_orgao), ("dim_fornecedor", dim_fornecedor),
                         ("dim_modalidade", dim_modalidade), ("dim_localidade", dim_localidade)]:
        tabela.to_csv(config.PASTA_PROCESSED / f"{nome}.csv", index=False, encoding="utf-8")

    comp = fato["comparavel"] == 1
    est_comp = fato.loc[comp, "valor_total_estimado"].sum()
    print("\n=== CONFERENCIA com o anexo 8 do enunciado (prova real) ===")
    print(f"itens na fato ............ {len(fato)}      (6126)")
    print(f"contratacoes distintas ... {fato['numero_controle_pncp'].nunique()}      (1962)")
    print(f"fornecedores ............. {len(dim_fornecedor)}      (2652)")
    print(f"orgaos (CNPJ) ............ {len(dim_orgao)}       (363)")
    print(f"volume homologado ........ R$ {fato['valor_total_homologado'].sum():,.2f}      (8.044.498.805,74 no formato brasileiro)")
    print(f"itens comparaveis ........ {comp.sum()}      (5457)")
    print(f"economia ................. {100 * fato['economia_valor'].sum() / est_comp:.2f}%      (14,46%)")
    print(f"ciclo medio / maximo ..... {fato['dias_ciclo'].mean():.1f} / {fato['dias_ciclo'].max():.0f} dias      (48,1 / 611)")
    print(f"itens sem ciclo .......... {fato['dias_ciclo'].isna().sum()}      (230)")
    print("perfil (% do volume) ..... ", (100 * fato.groupby("perfil_gasto")["valor_total_homologado"].sum()
                                         / fato["valor_total_homologado"].sum()).round(1).to_dict(), "    (referência: Obras 60,8 | Serviços 36,6 | Bens 2,6)")


if __name__ == "__main__":
    main()