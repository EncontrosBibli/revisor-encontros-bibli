import streamlit as st
from docx import Document
from PyPDF2 import PdfReader
import requests
import os

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Editoria Encontros Bibli", layout="wide", page_icon="🛡️")

# --- 1. GESTÃO DO TUTORIAL (ENDEREÇO FIXO) ---
URL_TUTORIAL = "https://periodicos.ufsc.br/index.php/eb/libraryFiles/downloadPublic/710"
CAMINHO_LOCAL_TUTORIAL = "tutorial_encontros_bibli.pdf"

@st.cache_data(show_spinner=False)
def baixar_e_ler_tutorial():
    """Baixa o tutorial do site da UFSC e extrai o texto."""
    try:
        response = requests.get(URL_TUTORIAL, timeout=10)
        with open(CAMINHO_LOCAL_TUTORIAL, "wb") as f:
            f.write(response.content)
        
        pdf = PdfReader(CAMINHO_LOCAL_TUTORIAL)
        texto = "\n".join([page.extract_text() for page in pdf.pages])
        return texto
    except Exception as e:
        return f"Erro ao acessar diretrizes online: {e}"

# --- 2. FUNÇÕES DE APOIO ---
def limpar_sessao():
    st.session_state.clear()
    st.rerun()

def descobrir_modelo(chave):
    url = f"https://generativelanguage.googleapis.com/v1/models?key={chave}"
    try:
        res = requests.get(url)
        if res.status_code == 200:
            modelos = res.json().get('models', [])
            for m in modelos:
                if "generateContent" in m.get("supportedGenerationMethods", []):
                    return m.get("name")
    except: return None
    return None

# --- INTERFACE ---
st.title("🛡️ Painel de Editoração - Revista Encontros Bibli")
st.caption("Sistema de Revisão Técnica, Normativa e Linguística (PT/EN/ES)")

# BARRA LATERAL
with st.sidebar:
    st.header("Configurações")
    api_key = st.text_input("🔑 API Key do Editor:", type="password")
    if "GEMINI_API_KEY" in st.secrets:
        api_key = st.secrets["GEMINI_API_KEY"]
        st.info("Utilizando chave mestra do sistema.")
    
    st.divider()
    if st.button("🧹 Limpar e Novo Artigo"):
        limpar_sessao()

if not api_key:
    st.warning("👈 Por favor, insira a API Key para ativar os módulos de IA.")
    st.stop()

nome_modelo = descobrir_modelo(api_key)

# --- FLUXO PRINCIPAL ---
artigo_file = st.file_uploader("📂 Subir Artigo para Revisão (Formato DOCX)", type="docx")

if artigo_file:
    with st.spinner("⏳ Lendo artigo e sincronizando normas da UFSC..."):
        doc = Document(artigo_file)
        texto_artigo = "\n".join([p.text.strip() for p in doc.paragraphs if p.text.strip()])
        texto_tutorial = baixar_e_ler_tutorial()

    st.success("✅ Documentos processados com sucesso!")
    
    # Módulos de Análise
    tab1, tab2, tab3 = st.tabs(["📐 Estrutura & Formatação", "✍️ Gramática & Citações", "📚 Referências (ABNT)"])

    def realizar_analise(prompt_texto):
        url = f"https://generativelanguage.googleapis.com/v1/{nome_modelo}:generateContent?key={api_key}"
        payload = {
            "contents": [{"parts": [{"text": prompt_texto}]}],
            "generationConfig": {"temperature": 0.1, "maxOutputTokens": 8192}
        }
        res = requests.post(url, json=payload)
        return res.json()['candidates'][0]['content']['parts'][0]['text'] if res.status_code == 200 else f"Erro: {res.text}"

    with tab1:
        if st.button("Executar Verificação de Estrutura"):
            with st.spinner("Analisando..."):
                prompt = f"REVISOR RIGOROSO: Compare o artigo com o tutorial da UFSC abaixo. Verifique rigorosamente a estrutura: títulos bilingues, resumo (100-250 palavras), palavras-chave separadas por ponto final. Identifique o idioma (PT, EN ou ES) e verifique a coerência estrutural.\nTUTORIAL: {texto_tutorial}\nTEXTO: {texto_artigo[:6000]}"
                st.markdown(realizar_analise(prompt))

    with tab2:
        if st.button("Executar Revisão Linguística"):
            with st.spinner("Analisando..."):
                prompt = f"Você é um revisor linguístico e de normas ABNT. Identifique ERROS de ortografia, gramática e concordância no idioma original do artigo (PT, EN ou ES). Paralelamente, verifique se citações curtas estão com aspas e citações longas (>3 linhas) têm recuo de 4cm e fonte menor. Aponte o erro e indique sugestão de mudança.\nTEXTO: {texto_artigo}"
                st.markdown(realizar_analise(prompt))

    with tab3:
        if st.button("Executar Validação de Referências"):
            with st.spinner("Analisando..."):
                referencias = texto_artigo[int(len(texto_artigo)*0.7):]
                prompt = f"Verifique se as referências seguem a ABNT NBR 6023:2018. Itens obrigatórios: Título da obra em NEGRITO, ordem alfabética, nomes de autores padronizados. Liste apenas as que precisam de correção com sugestões.\nREFERÊNCIAS:\n{referencias}"
                st.markdown(realizar_analise(prompt))