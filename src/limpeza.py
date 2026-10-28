"""
limpeza.py  -  FUNCOES DE LIMPEZA
============================================================================
"""

from datetime import datetime

# Textos que significam "sem valor" num campo de TEXTO (sempre comparados em MAIUSCULAS)
NULOS = {"N/A", "NULL", "NONE", "NAN", "-", "0", "SEM INFORMAÇÃO", "SEM INFORMACAO",
         "NÃO INFORMADO", "NAO INFORMADO", "NÃO SE APLICA", "NAO SE APLICA"}

# Formatos de data que aparecem nos arquivos (a letra %d e dia, %m e mes, %Y e ano com 4 digitos)
FORMATOS_DATA = ["%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%d.%m.%Y", "%Y/%m/%d", "%Y%m%d"]


# ---------------------------------------------------------------------------------------------
# 1) TEXTO  (nulos disfarcados, espacos, acento quebrado)
# ---------------------------------------------------------------------------------------------
def remover_invisiveis(texto):
    """PRONTA. Apaga caracteres invisiveis de largura zero que vem de sistemas antigos."""
    for c in ["​", "‌", "‍", ""]:
        texto = texto.replace(c, "")
    return texto


def consertar_acento(texto):
    """PRONTA. 'AquisiÃ§Ã£o' -> 'Aquisição': texto UTF-8 que foi lido como Latin-1.
    Se o texto nao tem esse problema, o try falha e devolvemos o texto como estava."""
    try:
        return texto.encode("latin-1").decode("utf-8")
    except (UnicodeEncodeError, UnicodeDecodeError):
        return texto


def tirar_espacos(texto):
    """Tira espacos das pontas e espacos repetidos. '  Ana   Maria ' -> 'Ana Maria'."""
    return " ".join(texto.split())


def eh_nulo(texto, zero_eh_nulo=True):
    """True se o texto significa 'sem valor': vazio, N/A, NULL, -, SEM INFORMACAO...
    O "0" so e nulo em campo de TEXTO. Em campo de numero, 0 e um valor de verdade (zero_eh_nulo=False)."""
    chave = texto.upper()
    if chave == "":
        return True
    if chave == "0":
        return zero_eh_nulo
    return chave in NULOS


def limpar_texto(texto, zero_eh_nulo=True):
    """Limpa um texto: tira invisiveis e espacos, conserta o acento e devolve None se for 'nulo disfarcado'."""
    if texto is None:
        return None
    texto = remover_invisiveis(texto)
    texto = consertar_acento(texto.strip(" "))
    texto = tirar_espacos(texto)
    if eh_nulo(texto, zero_eh_nulo):
        return None
    return texto


def padronizar_nome(texto):
    """Nome de orgao / fornecedor / item: limpo e em MAIUSCULAS."""
    texto = limpar_texto(texto)
    if texto is None:
        return None
    texto = texto.upper()
    texto = texto.replace("-", " - ")
    return tirar_espacos(texto)


# ---------------------------------------------------------------------------------------------
# 2) DOCUMENTOS  (CNPJ = 14 digitos, CPF = 11)
# ---------------------------------------------------------------------------------------------
def limpar_documento(texto, tipo_pessoa=None):
    """Deixa so os digitos do CNPJ/CPF, com os zeros da esquerda de volta."""
    texto = limpar_texto(texto)
    if texto is None:
        return None
    if tipo_pessoa == "PE":
        return texto.upper()
    digitos = "".join(c for c in texto if c.isdigit())
    if digitos == "":
        return None
    if tipo_pessoa == "PJ":
        tamanho = 14
    elif tipo_pessoa == "PF":
        tamanho = 11
    else:                                    # sem o tipo: mais de 11 digitos e CNPJ, senao CPF
        tamanho = 14 if len(digitos) > 11 else 11
    if len(digitos) > tamanho:               # digitos demais: documento impossivel
        return None
    return digitos.zfill(tamanho)


# ---------------------------------------------------------------------------------------------
# 3) DINHEIRO E NUMEROS EM TEXTO
# ---------------------------------------------------------------------------------------------
def converter_numero(texto):
    """'R$ 1.234,56' -> 1234.56      '1,234.56' -> 1234.56      '0,754' -> 0.754      '(1.500,00)' -> -1500.0
    REGRA DESTA BASE: ponto OU virgula SOZINHO e sempre o DECIMAL ('1.234' -> 1.234; '746.815' -> 746.815).
    So o simbolo REPETIDO e milhar ('1.234.567' -> 1234567). Quando aparecem os dois, o ULTIMO e o decimal."""
    texto = limpar_texto(texto, zero_eh_nulo=False)     # False: aqui o 0 e valor, nao nulo
    if texto is None:
        return None
    texto = texto.replace("R$", "").replace(" ", "")
    negativo = texto.startswith("(") or texto.startswith("-") or texto.endswith("-")
    texto = texto.strip("()-")
    if "." in texto and "," in texto:
        if texto.rfind(",") > texto.rfind("."):
            texto = texto.replace(".", "").replace(",", ".")
        else:
            texto = texto.replace(",", "")
    elif "," in texto:
        if texto.count(",") > 1:
            texto = texto.replace(",", "")
        else:
            texto = texto.replace(",", ".")
    elif texto.count(".") > 1:
        texto = texto.replace(".", "")
    try:
        numero = float(texto)
    except ValueError:
        return None
    return -numero if negativo else numero


# ---------------------------------------------------------------------------------------------
# 4) DATAS  (varios formatos no mesmo campo)
# ---------------------------------------------------------------------------------------------
def converter_data(texto):
    """'2025-03-10T08:30:00', '10/03/2025 14:20', '10.03.2025', '20250310' -> a data 2025-03-10 (sem hora)."""
    texto = limpar_texto(texto)
    if texto is None:
        return None
    texto = texto[:10]
    for formato in FORMATOS_DATA:
        try:
            data = datetime.strptime(texto, formato).date()
        except ValueError:
            continue
        if 2000 <= data.year <= 2030:
            return data
        return None
    return None


# =============================================================================================
# AUTOTESTE: python -m src.limpeza
# =============================================================================================
from datetime import date  # noqa: E402

CASOS = [
    ("tirar_espacos", ("  Ana   Maria ",), "Ana Maria"),
    ("eh_nulo", ("N/A",), True), ("eh_nulo", ("SEM INFORMAÇÃO",), True), ("eh_nulo", ("",), True),
    ("eh_nulo", ("Ana",), False), ("eh_nulo", ("0", True), True), ("eh_nulo", ("0", False), False),
    ("limpar_texto", ("AquisiÃ§Ã£o de mÃ³veis",), "Aquisição de móveis"),
    ("limpar_texto", ("Aquisição",), "Aquisição"),
    ("limpar_texto", ("  Ministério  da   Saúde  ",), "Ministério da Saúde"),
    ("limpar_texto", ("n/a",), None), ("limpar_texto", (" ",), None), ("limpar_texto", ("0",), None),
    ("padronizar_nome", ("  Ministério  da   Saúde  ",), "MINISTÉRIO DA SAÚDE"),
    ("padronizar_nome", ("Pregão-Eletrônico",), "PREGÃO - ELETRÔNICO"),
    ("limpar_documento", ("11.222.333/0001-81", "PJ"), "11222333000181"),
    ("limpar_documento", ("11222333000181", None), "11222333000181"),
    ("limpar_documento", ("1222333000181", "PJ"), "01222333000181"),
    ("limpar_documento", ("360305000104", "PJ"), "00360305000104"),
    ("limpar_documento", ("111.444.777-35", "PF"), "11144477735"),
    ("limpar_documento", ("1234567890", "PF"), "01234567890"),
    ("limpar_documento", (" 11222333000181 ", "PJ"), "11222333000181"),
    ("limpar_documento", ("N/A", "PJ"), None), ("limpar_documento", ("-", "PJ"), None),
    ("limpar_documento", ("ABC123", "PE"), "ABC123"),
    ("limpar_documento", ("123456789012345", "PJ"), None),
    ("converter_numero", ("R$ 1.234,56",), 1234.56), ("converter_numero", ("1,234.56",), 1234.56),
    ("converter_numero", ("1234.56",), 1234.56), ("converter_numero", ("1.234",), 1.234),
    ("converter_numero", ("0,754",), 0.754), ("converter_numero", ("746.815",), 746.815),
    ("converter_numero", ("1.234.567",), 1234567.0), ("converter_numero", ("12,5",), 12.5),
    ("converter_numero", ("1.234.567,89",), 1234567.89), ("converter_numero", ("R$ -12,50",), -12.5),
    ("converter_numero", ("(1.500,00)",), -1500.0), ("converter_numero", ("1.500,00-",), -1500.0),
    ("converter_numero", ("R$ 2.000,00",), 2000.0), ("converter_numero", ("493231.6000",), 493231.6),
    ("converter_numero", ("0",), 0.0), ("converter_numero", ("N/A",), None), ("converter_numero", ("",), None),
    ("converter_data", ("2025-03-10T08:30:00",), date(2025, 3, 10)), ("converter_data", ("10/03/2025",), date(2025, 3, 10)),
    ("converter_data", ("10-03-2025",), date(2025, 3, 10)), ("converter_data", ("2025/03/10",), date(2025, 3, 10)),
    ("converter_data", ("20250310",), date(2025, 3, 10)), ("converter_data", ("10/03/2025 14:20",), date(2025, 3, 10)),
    ("converter_data", ("10.03.2025",), date(2025, 3, 10)), ("converter_data", ("31/02/2025",), None),
    ("converter_data", ("0001-01-01",), None), ("converter_data", ("-",), None), ("converter_data", ("",), None),
]


def testar():
    import sys
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass
    acertos = 0
    for nome, args, esperado in CASOS:
        try:
            obtido = globals()[nome](*args)
            ok = obtido == esperado
        except Exception as erro:
            obtido, ok = f"erro: {type(erro).__name__}", False
        acertos += ok
        if not ok:
            print(f"✘ {nome}{args}  esperado {esperado!r}  obtido {obtido!r}")
    print(f"\n{acertos} de {len(CASOS)} exemplos certos" + ("  ✔ tudo certo, pode ir para a proxima etapa!" if acertos == len(CASOS) else "  -> continue completando"))
    return acertos == len(CASOS)


if __name__ == "__main__":
    raise SystemExit(0 if testar() else 1)