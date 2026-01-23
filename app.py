import streamlit as st
from docx import Document
from PyPDF2 import PdfReader
import requests
import os
import time
from io import BytesIO

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Editoria Encontros Bibli", layout="wide", page_icon="🛡️")

# --- 1. GESTÃO DO TUTORIAL ---
URL_TUTORIAL = "https://periodicos.ufsc.br/index.php/eb/libraryFiles/downloadPublic/710"
CAMINHO_LOCAL_TUTORIAL = "tutorial_encontros_bibli.pdf"

@st.cache_data(show_spinner=False)
def baixar_e_ler_tutorial():
    try:
        response = requests.get(URL_TUTORIAL, timeout=15)
        with open(CAMINHO_LOCAL_TUTORIAL, "wb") as f:
            f.write(response.content)
        pdf = PdfReader(CAMINHO_LOCAL_TUTORIAL)
        texto = "\n".join([page.extract_text() for page in pdf.pages])
        return texto
    except Exception as e:
        return f"Erro ao acessar diretrizes: {e}"

# --- 2. FUNÇÕES DE APOIO ---
def gerar_docx_download(conteudo, titulo_relatorio):
    doc_out = Document()
    doc_out.add_heading(titulo_relatorio, 0)
    for linha in conteudo.split('\n'):
        if linha.startswith('###'):
            doc_out.add_heading(linha.replace('###', '').strip(), level=1)
        elif linha.strip():
            doc_out.add_paragraph(linha)
    buffer = BytesIO()
    doc_out.save(buffer)
    buffer.seek(0)
    return buffer

def descobrir_melhor_modelo(chave):
    """Pergunta ao Google qual modelo está disponível para evitar erro 404."""
    for versao in ["v1beta", "v1"]:
        url = f"https://generativelanguage.googleapis.com/{versao}/models?key={chave}"
        try:
            res = requests.get(url, timeout=10)
            if res.status_code == 200:
                modelos = res.json().get('models', [])
                # Priorizamos o 1.5-flash por causa da cota alta
                for m in modelos:
                    if "gemini-1.5-flash" in m['name'] and "generateContent" in m['supportedGenerationMethods']:
                        return f"{versao}/{m['name']}"
                # Se não achar o 1.5-flash, pega o primeiro que suporte gerar conteúdo
                for m in modelos:
                    if "generateContent" in m['supportedGenerationMethods']:
                        return f"{versao}/{m['name']}"
        except: continue
    return None

# --- 3. FUNÇÃO DE ANÁLISE ---
def realizar_analise(prompt_texto, api_key, caminho_modelo):
    url = f"https://generativelanguage.googleapis.com/{caminho_modelo}:generateContent?key={api_key}"
    payload = {
        "contents": [{"parts": [{"text": prompt_texto}]}],
        "generationConfig": {"temperature": 0.1, "maxOutputTokens": 8192}
    }
    try:
        res = requests.post(url, json=payload, timeout=60)
        if res.status_code == 200:
            return res.json()['candidates'][0]['content']['parts'][0]['text']
        elif res.status_code == 429:
            return "ERRO_COTA"
        else:
            return f"Erro {res.status_code}: {res.text}"
    except Exception as e:
        return f"Erro de conexão: {e}"

# --- INTERFACE ---
st.title("🛡️ Painel de Editoração - Revista Encontros Bibli")

with st.sidebar:
    st.header("Configurações")
    api_key_input = st.text_input("🔑 API Key do Editor:", type="password")
    api_key = api_key_input if api_key_input else st.secrets.get("GEMINI_API_KEY", "")
    
    if st.secrets.get("GEMINI_API_KEY") and not api_key_input:
        st.info("Utilizando chave mestra do sistema.")
    
    if st.button("🧹 Novo Artigo"):
        st.session_state.clear()
        st.rerun()

if not api_key:
    st.warning("👈 Insira a API Key para começar.")
    st.stop()

# Descobre o modelo ideal para a chave atual
with st.spinner("Conectando com Google AI..."):
    caminho_modelo = descobrir_melhor_modelo(api_key)

if not caminho_modelo:
    st.error("Não foi possível encontrar um modelo válido para esta API Key.")
    st.stop()

artigo_file = st.file_uploader("📂 Subir Artigo (DOCX)", type="docx")

if artigo_file:
    with st.spinner("⏳ Lendo documentos..."):
        doc = Document(artigo_file)
        texto_artigo = "\n".join([p.text.strip() for p in doc.paragraphs if p.text.strip()])
        texto_tutorial = baixar_e_ler_tutorial()

    tab1, tab2, tab3 = st.tabs(["📐 Estrutura", "✍️ Gramática", "📚 Referências"])

    # --- TAB 1 ---
    with tab1:
        if st.button("Analisar Estrutura", key="b1"):
            res = realizar_analise(f"Verifique títulos e resumos: {texto_artigo[:8000]}\nNormas: {texto_tutorial}", api_key, caminho_modelo)
            st.markdown(res)
            if "Erro" not in res:
                st.download_button("📥 Salvar Relatório (.docx)", gerar_docx_download(res, "Estrutura"), f"Estrutura_{artigo_file.name}", key="d1")

    # --- TAB 2 ---
    with tab2:
        if st.button("Analisar Gramática", key="b2"):
            tamanho = 12000
            blocos = [texto_artigo[i:i+tamanho] for i in range(0, len(texto_artigo), tamanho)]
            relatorio = ""
            prog = st.progress(0)
            status = st.empty()
            for idx, b in enumerate(blocos):
                status.text(f"Analisando parte {idx+1} de {len(blocos)}...")
                r = realizar_analise(f"Revisão ortográfica e citações ABNT: {b}", api_key, caminho_modelo)
                if r == "ERRO_COTA":
                    time.sleep(15)
                    r = realizar_analise(f"Revisão ortográfica e citações ABNT: {b}", api_key, caminho_modelo)
                relatorio += f"\n### Parte {idx+1}\n{r}"
                time.sleep(5)
                prog.progress((idx+1)/len(blocos))
            status.empty()
            st.markdown(relatorio)
            if relatorio:
                st.download_button("📥 Salvar Relatório (.docx)", gerar_docx_download(relatorio, "Gramática"), f"Gramatica_{artigo_file.name}", key="d2")

    # --- TAB 3 ---
    with tab3:
        if st.button("Analisar Referências", key="b3"):
            res = realizar_analise(f"Verifique ABNT 6023: {texto_artigo[int(len(texto_artigo)*0.7):]}", api_key, caminho_modelo)
            st.markdown(res)
            if "Erro" not in res:
                st.download_button("📥 Salvar Relatório (.docx)", gerar_docx_download(res, "Referências"), f"Ref_{artigo_file.name}", key="d3")
