import io

import pandas as pd
import streamlit as st

from filters import build_final_portfolio
from normalize import merge_databases, normalize_columns

st.set_page_config(page_title="ProKnow-C", page_icon="📚", layout="centered")

_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

html, body, [class*="css"] {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
}

.block-container {
    max-width: 1200px;
    padding-top: 3rem;
    padding-bottom: 4rem;
}

#MainMenu, footer, header { visibility: hidden; }

.hero-title {
    font-size: 2.6rem;
    font-weight: 700;
    letter-spacing: -0.03em;
    margin-bottom: 0.2rem;
}

.hero-subtitle {
    font-size: 1.05rem;
    color: #666666;
    margin-bottom: 2.2rem;
}

.step-label {
    display: inline-block;
    font-size: 0.75rem;
    font-weight: 600;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: #999999;
    margin-bottom: 0.3rem;
}

.step-title {
    font-size: 1.3rem;
    font-weight: 600;
    margin-bottom: 0.6rem;
}

[data-testid="stVerticalBlockBorderWrapper"] {
    border-radius: 14px !important;
}

div[data-testid="stMetric"] {
    background: #F7F7F5;
    border-radius: 12px;
    padding: 0.8rem 1rem;
}

.stButton > button, .stDownloadButton > button {
    border-radius: 999px;
    background-color: #111111;
    color: #ffffff;
    border: none;
    padding: 0.5rem 1.4rem;
    font-weight: 500;
}

.stButton > button:hover, .stDownloadButton > button:hover {
    background-color: #333333;
    color: #ffffff;
}

hr { margin: 2.2rem 0; border-color: #eeeeee; }
</style>
"""

_SESSION_DEFAULTS = {
    "raw_bank": None,
    "selected_bank": None,
    "final_portfolio": None,
    "discarded": None,
}


def init_session_state():
    for key, value in _SESSION_DEFAULTS.items():
        if key not in st.session_state:
            st.session_state[key] = value


def reset_pipeline():
    for key in _SESSION_DEFAULTS:
        st.session_state[key] = None


def render_header():
    st.markdown(_CSS, unsafe_allow_html=True)
    st.markdown('<div class="hero-title">ProKnow-C</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="hero-subtitle">Monte seu portfólio bibliográfico a partir do Web of Science '
        'ou Scopus, sem precisar mexer em fórmula de planilha.</div>',
        unsafe_allow_html=True,
    )


def read_uploaded_file(uploaded_file):
    if uploaded_file.name.lower().endswith(".csv"):
        df = pd.read_csv(uploaded_file)
    else:
        df = pd.read_excel(uploaded_file)
    return normalize_columns(df)


def render_step_upload():
    st.markdown('<div class="step-label">Passo 1</div>', unsafe_allow_html=True)
    st.markdown('<div class="step-title">Envie os exports do WoS e/ou Scopus</div>', unsafe_allow_html=True)
    st.caption("Aceita um ou mais arquivos .xlsx / .csv. Artigos duplicados (mesmo DOI) são unidos automaticamente.")

    uploaded_files = st.file_uploader(
        "Arquivos", type=["xlsx", "csv"], accept_multiple_files=True, label_visibility="collapsed"
    )

    if not uploaded_files:
        return

    if st.button("Gerar banco bruto", type="primary"):
        try:
            databases = [read_uploaded_file(f) for f in uploaded_files]
        except ValueError as error:
            st.error(f"Não consegui ler um dos arquivos: {error}")
            return

        st.session_state.raw_bank = merge_databases(databases)
        st.session_state.selected_bank = None
        st.session_state.final_portfolio = None
        st.rerun()


def render_step_selection():
    raw_bank = st.session_state.raw_bank
    if raw_bank is None:
        return

    st.divider()
    st.markdown('<div class="step-label">Passo 2</div>', unsafe_allow_html=True)
    st.markdown('<div class="step-title">Selecione os títulos alinhados ao tema</div>', unsafe_allow_html=True)
    st.caption(f"{len(raw_bank)} artigos únicos encontrados. Marque os que fazem sentido para a pesquisa.")

    if "selecionado" not in raw_bank.columns:
        raw_bank = raw_bank.copy()
        raw_bank.insert(0, "selecionado", False)

    with st.container(height=720):
        edited = st.data_editor(
            raw_bank,
            column_config={
                "selecionado": st.column_config.CheckboxColumn("Incluir?", pinned=True),
                "title": st.column_config.TextColumn("Título", width="large"),
                "authors": st.column_config.TextColumn("Autores", width="medium"),
                "year": st.column_config.NumberColumn("Ano", format="%d"),
                "cited_by": st.column_config.NumberColumn("Citações"),
                "doi": st.column_config.TextColumn("DOI"),
                "source_title": st.column_config.TextColumn("Fonte"),
            },
            disabled=["title", "authors", "year", "cited_by", "doi", "source_title"],
            hide_index=True,
            width="stretch",
            height="stretch",
            key="raw_bank_editor",
        )

    selected_count = int(edited["selecionado"].sum())
    st.caption(f"{selected_count} artigo(s) marcado(s).")

    if st.button("Confirmar seleção", disabled=selected_count == 0):
        st.session_state.selected_bank = edited[edited["selecionado"]].drop(columns="selecionado").reset_index(drop=True)
        st.session_state.final_portfolio = None
        st.rerun()


def render_step_filters():
    selected_bank = st.session_state.selected_bank
    if selected_bank is None:
        return

    st.divider()
    st.markdown('<div class="step-label">Passo 3</div>', unsafe_allow_html=True)
    st.markdown('<div class="step-title">Filtros automáticos do ProKnow-C</div>', unsafe_allow_html=True)
    st.caption(
        "Reconhece os artigos mais citados, resgata quem compartilha autor com eles e quem é recente "
        "demais para ter acumulado citações."
    )

    with st.container(border=True):
        col1, col2 = st.columns(2)
        with col1:
            citation_cutoff = st.slider("Representatividade de citações", 50, 100, 80, step=5, format="%d%%")
        with col2:
            recent_years = st.slider("Anos para considerar 'recente'", 0, 5, 2)

    if st.button("Aplicar filtros e montar portfólio", type="primary"):
        final_portfolio, discarded = build_final_portfolio(
            selected_bank, cutoff=citation_cutoff / 100, max_age_years=recent_years
        )
        final_portfolio = final_portfolio.copy()
        final_portfolio["link_doi"] = final_portfolio["doi"].apply(
            lambda doi: f"https://doi.org/{doi}" if pd.notna(doi) and str(doi).strip() else ""
        )
        st.session_state.final_portfolio = final_portfolio
        st.session_state.discarded = discarded
        st.rerun()


def build_download_file(final_portfolio, discarded):
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        final_portfolio.to_excel(writer, sheet_name="Portfolio Final", index=False)
        discarded.to_excel(writer, sheet_name="Descartados", index=False)
    return buffer.getvalue()


def render_step_results():
    final_portfolio = st.session_state.final_portfolio
    if final_portfolio is None:
        return

    discarded = st.session_state.discarded
    reason_counts = final_portfolio["motivo_inclusao"].value_counts()

    st.divider()
    st.markdown('<div class="step-label">Resultado</div>', unsafe_allow_html=True)
    st.markdown('<div class="step-title">Portfólio bibliográfico final</div>', unsafe_allow_html=True)

    cols = st.columns(4)
    cols[0].metric("Total final", len(final_portfolio))
    cols[1].metric("Por citação", int(reason_counts.get("Representatividade de citações", 0)))
    cols[2].metric("Por autor", int(reason_counts.get("Autor com reconhecimento científico", 0)))
    cols[3].metric("Descartados", len(discarded))

    with st.container(height=600):
        st.dataframe(
            final_portfolio,
            column_config={
                "title": st.column_config.TextColumn("Título", width="large"),
                "cited_by": st.column_config.NumberColumn("Citações"),
                "year": st.column_config.NumberColumn("Ano", format="%d"),
                "motivo_inclusao": st.column_config.TextColumn("Motivo"),
                "link_doi": st.column_config.LinkColumn("DOI", display_text="Abrir"),
            },
            hide_index=True,
            width="stretch",
            height="stretch",
        )

    st.download_button(
        "Baixar portfólio final (.xlsx)",
        data=build_download_file(final_portfolio, discarded),
        file_name="portfolio_final.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


def main():
    init_session_state()
    render_header()
    render_step_upload()
    render_step_selection()
    render_step_filters()
    render_step_results()

    if st.session_state.raw_bank is not None:
        st.divider()
        if st.button("Recomeçar"):
            reset_pipeline()
            st.rerun()


if __name__ == "__main__":
    main()
