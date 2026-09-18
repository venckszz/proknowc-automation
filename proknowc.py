import argparse
import sys

import pandas as pd

from filters import build_final_portfolio
from normalize import load_database, merge_databases

_SELECTED_VALUES = {"sim", "s", "yes", "y", "1", "x"}


def cmd_bank(args):
    databases = [load_database(path) for path in args.inputs]
    combined = merge_databases(databases)
    combined["selecionado"] = ""
    combined.to_excel(args.output, index=False)

    print(f"Banco bruto com {len(combined)} artigos únicos salvo em {args.output}.")
    print("Abra o arquivo, marque 'sim' na coluna 'selecionado' para os artigos alinhados ao tema e rode o comando 'select'.")


def cmd_select(args):
    df = pd.read_excel(args.input)
    if "selecionado" not in df.columns:
        sys.exit("A planilha não tem a coluna 'selecionado'. Gere o banco bruto com o comando 'bank' primeiro.")

    mask = df["selecionado"].astype(str).str.strip().str.lower().isin(_SELECTED_VALUES)
    selected = df[mask].drop(columns="selecionado").reset_index(drop=True)

    if selected.empty:
        sys.exit("Nenhum artigo marcado como selecionado na coluna 'selecionado'.")

    selected.to_excel(args.output, index=False)
    print(f"{len(selected)} artigos selecionados salvos em {args.output}.")


def cmd_filter(args):
    df = pd.read_excel(args.input)
    final_portfolio, discarded = build_final_portfolio(
        df, cutoff=args.citation_cutoff, max_age_years=args.recent_years
    )

    final_portfolio["link_doi"] = final_portfolio["doi"].apply(
        lambda doi: f"https://doi.org/{doi}" if pd.notna(doi) and str(doi).strip() else ""
    )

    with pd.ExcelWriter(args.output) as writer:
        final_portfolio.to_excel(writer, sheet_name="Portfolio Final", index=False)
        discarded.to_excel(writer, sheet_name="Descartados", index=False)

    print(f"Portfólio final com {len(final_portfolio)} artigos salvo em {args.output}.")
    print(f"{len(discarded)} artigos descartados na aba 'Descartados' (sem citação representativa, autor reconhecido ou recência).")


def build_parser():
    parser = argparse.ArgumentParser(
        description="Automação do processo ProKnow-C: exports do WoS/Scopus -> portfólio bibliográfico final."
    )
    subparsers = parser.add_subparsers(required=True)

    bank = subparsers.add_parser(
        "bank", help="Combina exports do WoS/Scopus em um banco bruto para seleção manual de títulos."
    )
    bank.add_argument("inputs", nargs="+", help="Arquivos de export do WoS e/ou Scopus (.xlsx ou .csv).")
    bank.add_argument("-o", "--output", default="banco_bruto_selecao.xlsx")
    bank.set_defaults(func=cmd_bank)

    select = subparsers.add_parser(
        "select", help="Extrai os artigos marcados como selecionados na planilha de banco bruto."
    )
    select.add_argument("input", help="Planilha gerada pelo comando 'bank', já preenchida na coluna 'selecionado'.")
    select.add_argument("-o", "--output", default="banco_selecionado.xlsx")
    select.set_defaults(func=cmd_select)

    filter_cmd = subparsers.add_parser(
        "filter", help="Aplica os filtros de citação, autor e recência e gera o portfólio final."
    )
    filter_cmd.add_argument("input", help="Planilha de artigos selecionados (saída do comando 'select').")
    filter_cmd.add_argument("-o", "--output", default="portfolio_final.xlsx")
    filter_cmd.add_argument(
        "--citation-cutoff", type=float, default=0.8,
        help="Percentual de representatividade de citações (padrão 0.8 = 80%%).",
    )
    filter_cmd.add_argument(
        "--recent-years", type=int, default=2,
        help="Idade máxima em anos para resgatar artigos recentes sem citações (padrão 2).",
    )
    filter_cmd.set_defaults(func=cmd_filter)

    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
