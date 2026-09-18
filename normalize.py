import pandas as pd

_FIELD_CANDIDATES = {
    "title": ["Article Title", "Title", "TI"],
    "authors": ["Authors", "Author Full Names", "AU"],
    "year": ["Publication Year", "Year", "PY"],
    "cited_by": [
        "Times Cited, WoS Core",
        "Times Cited, All Databases",
        "Times Cited",
        "Cited by",
        "TC",
    ],
    "doi": ["DOI", "DI"],
    "source_title": ["Source Title", "Publication Title", "SO"],
}

_REQUIRED_FIELDS = ("title", "authors", "year", "cited_by")


def _find_column(df, candidates):
    lower_map = {c.lower(): c for c in df.columns}
    for candidate in candidates:
        match = lower_map.get(candidate.lower())
        if match:
            return match
    return None


def _clean_text(value):
    """Converte um valor de célula em texto seguro, tratando ausência de dado (NaN/NA/None) como string vazia."""
    if pd.isna(value):
        return ""
    return str(value).strip()


def normalize_columns(df):
    """Renomeia colunas de exports do WoS/Scopus para o esquema padrão do ProKnow-C."""
    rename_map = {}
    for standard_name, candidates in _FIELD_CANDIDATES.items():
        found = _find_column(df, candidates)
        if found:
            rename_map[found] = standard_name
    normalized = df.rename(columns=rename_map)

    missing = [f for f in _REQUIRED_FIELDS if f not in normalized.columns]
    if missing:
        raise ValueError(f"Colunas obrigatórias não encontradas na base: {missing}")

    if "doi" not in normalized.columns:
        normalized["doi"] = pd.NA
    if "source_title" not in normalized.columns:
        normalized["source_title"] = pd.NA

    normalized["cited_by"] = pd.to_numeric(normalized["cited_by"], errors="coerce").fillna(0).astype(int)
    normalized["year"] = pd.to_numeric(normalized["year"], errors="coerce").astype("Int64")
    normalized["title"] = normalized["title"].apply(_clean_text)
    normalized["authors"] = normalized["authors"].apply(_clean_text)

    # Linhas em branco no export (comuns em planilhas exportadas manualmente) não têm título
    # e não representam um artigo real, então são descartadas aqui em vez de virar uma linha vazia.
    normalized = normalized[normalized["title"] != ""].reset_index(drop=True)

    return normalized


def load_database(path):
    """Carrega um export do WoS ou Scopus (.xlsx ou .csv) e normaliza as colunas."""
    if str(path).lower().endswith(".csv"):
        df = pd.read_csv(path)
    else:
        df = pd.read_excel(path)
    return normalize_columns(df)


def _dedup_key(row):
    doi = _clean_text(row.get("doi")).lower()
    if doi:
        return f"doi:{doi}"
    return f"title:{_clean_text(row.get('title')).lower()}"


def merge_databases(dataframes):
    """Combina bases (ex.: WoS + Scopus) removendo duplicatas por DOI ou, na ausência dele, por título."""
    combined = pd.concat(dataframes, ignore_index=True)
    combined["_dedup_key"] = combined.apply(_dedup_key, axis=1)
    combined = combined.drop_duplicates(subset="_dedup_key", keep="first")
    return combined.drop(columns="_dedup_key").reset_index(drop=True)
