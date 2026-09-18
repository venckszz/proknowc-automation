import datetime

import pandas as pd


def split_authors(authors_field):
    """Separa uma string de autores em uma lista normalizada de nomes individuais."""
    if not authors_field or str(authors_field).lower() == "nan":
        return []
    parts = str(authors_field).replace(" and ", ";").split(";")
    return [p.strip().lower() for p in parts if p.strip()]


def filter_by_citation_representativeness(df, cutoff=0.8):
    """
    Ordena os artigos por número de citações e separa os que, somados,
    representam `cutoff` (ex.: 0.8 = 80%) do total de citações do portfólio.
    Retorna (reconhecidos, nao_reconhecidos).
    """
    ordered = df.sort_values("cited_by", ascending=False).reset_index(drop=True)
    total_citations = ordered["cited_by"].sum()

    if total_citations == 0:
        return ordered.iloc[0:0], ordered

    cumulative_share = ordered["cited_by"].cumsum() / total_citations
    cutoff_index = cumulative_share.searchsorted(cutoff)
    recognized = ordered.iloc[: cutoff_index + 1]
    not_recognized = ordered.iloc[cutoff_index + 1 :]
    return recognized, not_recognized


def recover_by_author(recognized, not_recognized):
    """Resgata artigos cujos autores já aparecem no grupo reconhecido por citação."""
    recognized_authors = set()
    for authors_field in recognized["authors"]:
        recognized_authors.update(split_authors(authors_field))

    def has_recognized_author(authors_field):
        return bool(recognized_authors & set(split_authors(authors_field)))

    # .astype(bool) evita que uma base vazia (nenhum artigo fora do corte de citações)
    # produza uma máscara com dtype "object", que o pandas não trata como seleção de linhas.
    mask = not_recognized["authors"].apply(has_recognized_author).astype(bool)
    return not_recognized[mask], not_recognized[~mask]


def recover_by_recency(remaining, current_year, max_age_years=2):
    """Resgata artigos recentes demais para terem tido tempo de acumular citações."""
    mask = remaining["year"] >= (current_year - max_age_years)
    return remaining[mask], remaining[~mask]


def build_final_portfolio(df, cutoff=0.8, max_age_years=2, current_year=None):
    """Aplica os filtros do ProKnow-C na ordem citação -> autor -> recência e monta o portfólio final."""
    if current_year is None:
        current_year = datetime.date.today().year

    recognized, not_recognized = filter_by_citation_representativeness(df, cutoff)
    recognized = recognized.copy()
    recognized["motivo_inclusao"] = "Representatividade de citações"

    recovered_by_author, still_out = recover_by_author(recognized, not_recognized)
    recovered_by_author = recovered_by_author.copy()
    recovered_by_author["motivo_inclusao"] = "Autor com reconhecimento científico"

    recovered_by_recency, discarded = recover_by_recency(still_out, current_year, max_age_years)
    recovered_by_recency = recovered_by_recency.copy()
    recovered_by_recency["motivo_inclusao"] = "Publicação recente (sem tempo de acumular citações)"

    final_portfolio = pd.concat(
        [recognized, recovered_by_author, recovered_by_recency], ignore_index=True
    )
    final_portfolio = final_portfolio.sort_values("cited_by", ascending=False).reset_index(drop=True)
    return final_portfolio, discarded
