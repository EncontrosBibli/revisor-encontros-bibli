import streamlit as st
from docx import Document
from PyPDF2 import PdfReader
import requests
import os
import time
from io import BytesIO

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Editoria Encontros Bibli", layout="wide", page_icon="🛡️")

# --- 1. GESTÃO DO TUTORIAL (ENDEREÇO FIXO) ---
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
        return f"Erro ao acessar diretrizes online: {e}"

# --- 2. FUNÇÕES DE APOIO ---
def limpar_sessao():
    st.session_state.clear()
    st.rerun()

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

# --- 3. FUNÇÃO DE ANÁLISE CORRIGIDA (ERRO 404 RESOLVIDO) ---
def realizar_analise(prompt_texto, api_key):
    # Testamos a URL v1beta que é a mais compatível com o modelo flash atual
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
    
    payload = {
        "contents": [{"parts": [{"text": prompt_texto}]}],
        "generationConfig": {"temperature": 0.1, "maxOutputTokens": 8192}
    }
    
    try:
        res = requests.post(url, json=payload, timeout=60)
        
        # Se der erro 404 na v1beta, tentamos a v1 padrão
        if res.status_code == 404:
            url_alt = f"https://generativelanguage.googleapis.com/v1/models/gemini-1.5-flash:generateContent?key={api_key}"
            res = requests.post(url_alt, json=payload, timeout=60)

        if res.status_code == 200:
            return res.json()['candidates'][0]['content']['parts'][0]['text']
        elif res.status_code == 429:
            return "ERRO_COTA"
        else:
            return f"Erro na API ({res.status_code}): {res.text}"
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
    
    st.divider()
    if st.button("🧹 Limpar e Novo Artigo"):
        limpar_sessao()

if not api_key:
    st.warning("👈 Por favor, insira a API Key para ativar.")
    st.stop()

artigo_file = st.file_uploader("📂 Subir Artigo (DOCX)", type="docx")

if artigo_file:
    with st.spinner("⏳ Processando..."):
        doc = Document(artigo_file)
        texto_artigo = "\n".join([p.text.strip() for p in doc.paragraphs if p.text.strip()])
        texto_tutorial = baixar_e_ler_tutorial()

    tab1, tab2, tab3 = st.tabs(["📐 Estrutura", "✍️ Gramática", "📚 Referências"])

    # --- TAB 1 ---
    with tab1:
        if st.button("Analisar Estrutura", key="b1"):
            res = realizar_analise(f"Verifique títulos bilingues e resumo (100-250 palavras) conforme: {texto_tutorial}\nTexto: {texto_artigo[:8000]}", api_key)
            st.markdown(res)
            st.download_button("📥 Baixar DOCX", gerar_docx_download(res, "Estrutura"), f"Estrutura_{artigo_file.name}")

    # --- TAB 2 ---
    with tab2:
        if st.button("Analisar Gramática", key="b2"):
            tamanho = 12000
            blocos = [texto_artigo[i:i+tamanho] for i in range(0, len(texto_artigo), tamanho)]
            relatorio = ""
            prog = st.progress(0)
            for idx, b in enumerate(blocos):
                r = realizar_analise(f"Revisão ortográfica e citações ABNT: {b}", api_key)
                if r == "ERRO_COTA":
                    time.sleep(10)
                    r = realizar_analise(f"Revisão ortográfica e citações ABNT: {b}", api_key)
                relatorio += f"\n### Parte {idx+1}\n{r}"
                time.sleep(4)
                prog.progress((idx+1)/len(blocos))
            st.markdown(relatorio)
            st.download_button("📥 Baixar DOCX", gerar_docx_download(relatorio, "Gramática"), f"Gramatica_{artigo_file.name}")

    # --- TAB 3 ---
    with tab3:
        if st.button("Analisar Referências", key="b3"):
            res = realizar_analise(f"Verifique ABNT 6023 (Negrito no título): {texto_artigo[int(len(texto_artigo)*0.7):]}", api_key)
            st.markdown(res)
            st.download_button("📥 Baixar DOCX", gerar_docx_download(res, "Referências"), f"Ref_{artigo_file.name}")
