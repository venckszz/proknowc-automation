# ProKnow-C Automation

Automação do processo **ProKnow-C** (*Knowledge Development Process – Constructivist*), metodologia usada em revisões bibliométricas para construir um portfólio de artigos relevantes a partir de exports do **Web of Science** e/ou **Scopus**.

Duas formas de usar: uma interface web (Streamlit) e uma CLI. Os dois usam a mesma lógica de filtragem, em `normalize.py` e `filters.py`.

## A ideia, passo a passo

O ProKnow-C parte de uma busca bruta (muitos artigos, pouco filtrados) e vai reduzindo até um portfólio final relevante e citável. Este projeto automatiza as etapas que dá pra automatizar e deixa manual só a etapa que exige julgamento humano (ler o título e decidir se é do tema).

1. **Banco bruto.** Você exporta os resultados de uma busca no WoS e/ou Scopus (`.xlsx`/`.csv`) e o programa junta tudo em uma base só, removendo duplicatas (mesmo artigo indexado nas duas bases) por DOI ou, na ausência dele, por título.
2. **Alinhamento ao tema (manual).** Você olha os títulos e marca quais fazem sentido para a sua pesquisa. Essa etapa não dá pra automatizar — é julgamento humano.
3. **Representatividade de citações.** Dos artigos selecionados, ordena por número de citações e separa os que, somados, representam um percentual do total de citações do conjunto (padrão: 80%, ajustável). Esses viram o núcleo "reconhecido cientificamente" do portfólio.
4. **Resgate por autor.** Um artigo que ficou de fora do corte de citações volta ao portfólio se algum dos seus autores já aparece em um artigo reconhecido no passo 3 — a lógica é que um autor de peso no tema carrega relevância mesmo em um artigo ainda pouco citado.
5. **Resgate por recência.** Um artigo publicado nos últimos N anos (padrão: 2) também é aceito mesmo sem citações representativas, porque é recente demais para ter tido tempo de acumular citações.
6. **Portfólio final.** O resultado (passos 3+4+5, sem repetição) sai em um `.xlsx` com o motivo de inclusão de cada artigo e um link clicável para o DOI.

## Estrutura do projeto

```
proknowc-automation/
├── app.py            # interface web (Streamlit)
├── proknowc.py        # interface de linha de comando (CLI)
├── normalize.py        # leitura e padronização dos exports do WoS/Scopus
├── filters.py          # lógica dos filtros de citação, autor e recência
├── requirements.txt
└── .streamlit/
    └── config.toml      # tema visual do app
```

`normalize.py` e `filters.py` não sabem nada sobre interface — tanto `app.py` quanto `proknowc.py` os usam. Se precisar mudar a regra de negócio (ex.: outro critério de corte), é só mexer ali; a interface não muda.

## Como rodar

### Pré-requisitos

- Python 3.10+

### Instalação

```bash
git clone <url-do-repositorio>
cd proknowc-automation
python3 -m venv .venv
source .venv/bin/activate        # no Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### Interface web (recomendado)

```bash
streamlit run app.py
```

Abre em `http://localhost:8501`. Fluxo dentro do app:

1. **Envie os exports** do WoS e/ou Scopus (um ou mais arquivos `.xlsx`/`.csv`) e clique em "Gerar banco bruto".
2. **Marque os artigos** alinhados ao tema na coluna "Incluir?" e clique em "Confirmar seleção".
3. **Ajuste os sliders** de representatividade de citações e de "quantos anos conta como recente", e clique em "Aplicar filtros e montar portfólio".
4. **Baixe o resultado** em "Baixar portfólio final (.xlsx)" — vem com a aba do portfólio e uma aba "Descartados" para auditoria.

### Linha de comando (alternativa)

```bash
# 1. Combina WoS + Scopus num banco bruto para seleção manual de títulos
python proknowc.py bank wos_export.xlsx scopus_export.xlsx -o banco_bruto_selecao.xlsx

# 2. Abra o .xlsx, marque "sim" na coluna "selecionado" nos títulos alinhados ao tema,
#    salve, e rode:
python proknowc.py select banco_bruto_selecao.xlsx -o banco_selecionado.xlsx

# 3. Aplica citação -> autor -> recência e gera o portfólio final
python proknowc.py filter banco_selecionado.xlsx -o portfolio_final.xlsx \
    --citation-cutoff 0.8 --recent-years 2
```

## Formato de entrada esperado

Qualquer export padrão do WoS ou Scopus em `.xlsx`/`.csv`, com pelo menos: título, autores, ano de publicação e número de citações. DOI é opcional, mas necessário para os links de download no resultado final. `normalize.py` reconhece os nomes de coluna usados por ambas as bases automaticamente.

## Fonte da metodologia

Ensslin, L. et al. *ProKnow-C, knowledge development process-constructivist.* Processo técnico com patente de registro pertencente aos autores, 2010.
