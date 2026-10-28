import pandas as pd
import re

print("=" * 70)
print("SPRINT 0 & 1: AUDITORIA EXPLORATÓRIA DOS DADOS BRUTOS (data/raw/)")
print("=" * 70)

caminho_compras = "data/raw/compras.csv"
caminho_itens = "data/raw/itens.csv"
caminho_resultados = "data/raw/resultados.csv"

df_compras = pd.read_csv(caminho_compras, dtype=str, keep_default_na=False)
df_itens = pd.read_csv(caminho_itens, dtype=str, keep_default_na=False)
df_resultados = pd.read_csv(caminho_resultados, dtype=str, keep_default_na=False)

print("\n--- 1. VOLUMETRIA E UNICIDADE DE CHAVES ---")
print(f"Linhas em compras.csv:    {len(df_compras):,} | Esperado: 2.042")
print(f"Linhas em itens.csv:      {len(df_itens):,} | Esperado: 7.077")
print(f"Linhas em resultados.csv: {len(df_resultados):,} | Esperado: 15.896")

dup_compras = df_compras["numero_controle_pncp"].duplicated().sum()
print(f"Chaves duplicadas em compras (numero_controle_pncp): {dup_compras}")

chaves_itens = df_itens["numero_controle_pncp"] + "_" + df_itens["numero_item"]
dup_itens = chaves_itens.duplicated().sum()
print(f"Chaves duplicadas em itens (pncp + numero_item): {dup_itens}")

print("\n--- 2. PADRÕES MONETÁRIOS E NUMÉRICOS ---")
cols_monetarias = [
    ("itens", df_itens, ["valor_unitario_estimado", "valor_total_estimado", "quantidade"]),
    ("resultados", df_resultados, ["valor_unitario_homologado", "valor_total_homologado", "quantidade_homologada"])
]

for arquivo, df, cols in cols_monetarias:
    print(f"\nArquivo: {arquivo}.csv")
    for col in cols:
        amostra_cifrao = df[col].str.contains(r"R\$", regex=True).sum()
        amostra_virgula = df[col].str.contains(r",", regex=True).sum()
        amostra_ponto = df[col].str.contains(r"\.", regex=True).sum()
        pontos_multiplos = df[col].str.count(r"\.").gt(1).sum()
        virgulas_multiplas = df[col].str.count(r",").gt(1).sum()
        parenteses = df[col].str.contains(r"\(|\)", regex=True).sum()
        
        print(f"  Coluna '{col}':")
        print(f"    - Contém 'R$': {amostra_cifrao:,} | Entre parênteses: {parenteses:,}")
        print(f"    - Contém vírgula: {amostra_virgula:,} (Múltiplas: {virgulas_multiplas:,})")
        print(f"    - Contém ponto: {amostra_ponto:,} (Múltiplos: {pontos_multiplos:,})")

print("\n--- 3. IDENTIFICADORES (CNPJ / CPF) ---")
cnpj_orgao_limpo = df_compras["cnpj_orgao"].str.replace(r"\D", "", regex=True)
orgao_menos_14 = cnpj_orgao_limpo.str.len().lt(14).sum()
orgao_com_mascara = df_compras["cnpj_orgao"].str.contains(r"[./-]", regex=True).sum()
print(f"Órgão - Com máscara gráfica: {orgao_com_mascara:,}")
print(f"Órgão - Menos de 14 dígitos (zero à esquerda perdido): {orgao_menos_14:,}")

ni_limpo = df_resultados["ni_fornecedor"].str.replace(r"\D", "", regex=True)
fornec_com_mascara = df_resultados["ni_fornecedor"].str.contains(r"[./-]", regex=True).sum()
fornec_cpf_curto = ni_limpo.str.len().gt(0) & ni_limpo.str.len().lt(11)
fornec_cnpj_curto = ni_limpo.str.len().gt(11) & ni_limpo.str.len().lt(14)
print(f"Fornecedor - Com máscara: {fornec_com_mascara:,}")
print(f"Fornecedor - CPF sem zeros (< 11 dígitos): {fornec_cpf_curto.sum():,}")
print(f"Fornecedor - CNPJ sem zeros (< 14 dígitos): {fornec_cnpj_curto.sum():,}")

print("\n--- 4. NULOS DISFARÇADOS E STRINGS ZUMBIS ---")
zumbis_alvo = ["N/A", "NULL", "-", "0", "SEM INFORMAÇÃO", "NÃO SE APLICA", ""]
for nome, df in [("compras", df_compras), ("itens", df_itens), ("resultados", df_resultados)]:
    print(f"\nContagem de Nulos no arquivo {nome}.csv:")
    for col in df.columns:
        contagem = df[col].isin(zumbis_alvo).sum()
        if contagem > 0:
            print(f"  - {col}: {contagem:,} campos vazios ou zumbis")

print("\n--- 5. CRONOLOGIA TEMPORAL (data_resultado vs data_publicacao) ---")
df_datas = df_resultados[["numero_controle_pncp", "numero_item", "data_resultado"]].merge(
    df_compras[["numero_controle_pncp", "data_publicacao"]], on="numero_controle_pncp"
)
df_datas = df_datas[(df_datas["data_resultado"] != "") & (df_datas["data_publicacao"] != "")]
datas_invalidas = df_datas[df_datas["data_resultado"].str[:10] < df_datas["data_publicacao"].str[:10]]
print(f"Itens com data de homologação ANTERIOR à data de publicação: {len(datas_invalidas):,}")
print("=" * 70)