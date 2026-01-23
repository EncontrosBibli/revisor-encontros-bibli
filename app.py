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
    for versao in ["v1beta", "v1"]:
        url = f"https://generativelanguage.googleapis.com/{versao}/models?key={chave}"
        try:
            res = requests.get(url, timeout=10)
            if res.status_code == 200:
                modelos = res.json().get('models', [])
                for m in modelos:
                    if "gemini-1.5-flash" in m['name'] and "generateContent" in m['supportedGenerationMethods']:
                        return f"{versao}/{m['name']}"
        except: continue
    return None

# --- 3. FUNÇÃO DE ANÁLISE COM REPETIÇÃO (ANTI-COTA) ---
def realizar_analise_robusta(prompt_texto, api_key, caminho_modelo, max_tentativas=3):
    url = f"https://generativelanguage.googleapis.com/{caminho_modelo}:generateContent?key={api_key}"
    payload = {
        "contents": [{"parts": [{"text": prompt_texto}]}],
        "generationConfig": {"temperature": 0.1, "maxOutputTokens": 8192}
    }
    
    for tentativa in range(max_tentativas):
        try:
            res = requests.post(url, json=payload, timeout=90)
            if res.status_code == 200:
                return res.json()['candidates'][0]['content']['parts'][0]['text']
            elif res.status_code == 429:
                if tentativa < max_tentativas - 1:
                    tempo_espera = 60  # Espera 1 minuto se estourar a cota
                    st.warning(f"⚠️ Cota atingida. Pausando por {tempo_espera}s para retomar...")
                    time.sleep(tempo_espera)
                    continue
                else:
                    return "ERRO_LIMITE_DIARIO: A cota diária ou de velocidade foi excedida permanentemente."
            else:
                return f"Erro {res.status_code}: {res.text}"
        except Exception as e:
            time.sleep(5)
            continue
    return "Erro persistente após várias tentativas."

# --- INTERFACE ---
st.title("🛡️ Painel de Editoração - Revista Encontros Bibli")

with st.sidebar:
    st.header("Configurações")
    api_key_input = st.text_input("🔑 API Key do Editor:", type="password")
    api_key = api_key_input if api_key_input else st.secrets.get("GEMINI_API_KEY", "")
    
    if st.button("🧹 Novo Artigo"):
        st.session_state.clear()
        st.rerun()

if not api_key:
    st.warning("👈 Insira a API Key para começar.")
    st.stop()

with st.spinner("Conectando com Google AI..."):
    caminho_modelo = descobrir_melhor_modelo(api_key)

if not caminho_modelo:
    st.error("Modelo não encontrado. Verifique sua chave.")
    st.stop()

artigo_file = st.file_uploader("📂 Subir Artigo (DOCX)", type="docx")

if artigo_file:
    with st.spinner("⏳ Lendo documentos..."):
        doc = Document(artigo_file)
        texto_artigo = "\n".join([p.text.strip() for p in doc.paragraphs if p.text.strip()])
        texto_tutorial = baixar_e_ler_tutorial()

    tab1, tab2, tab3 = st.tabs(["📐 Estrutura", "✍️ Gramática", "📚 Referências"])

    with tab1:
        if st.button("Analisar Estrutura", key="b1"):
            res = realizar_analise_robusta(f"Verifique títulos e resumos: {texto_artigo[:8000]}\nNormas: {texto_tutorial}", api_key, caminho_modelo)
            st.markdown(res)
            st.download_button("📥 Baixar DOCX", gerar_docx_download(res, "Estrutura"), f"Estrutura_{artigo_file.name}", key="d1")

    with tab2:
        if st.button("Analisar Gramática", key="b2"):
            # Aumentado para 25k para reduzir o número de requisições
            tamanho = 25000 
            blocos = [texto_artigo[i:i+tamanho] for i in range(0, len(texto_artigo), tamanho)]
            relatorio = ""
            prog = st.progress(0)
            status = st.empty()
            
            for idx, b in enumerate(blocos):
                status.text(f"Analisando parte {idx+1} de {len(blocos)}...")
                r = realizar_analise_robusta(f"Revisão ortográfica e citações ABNT: {b}", api_key, caminho_modelo)
                
                relatorio += f"\n### Parte {idx+1}\n{r}"
                time.sleep(10) # Pausa obrigatória de 10s entre blocos
                prog.progress((idx+1)/len(blocos))
                
            status.empty()
            st.markdown(relatorio)
            st.download_button("📥 Baixar DOCX", gerar_docx_download(relatorio, "Gramática"), f"Gramatica_{artigo_file.name}", key="d2")

    with tab3:
        if st.button("Analisar Referências", key="b3"):
            res = realizar_analise_robusta(f"Verifique ABNT 6023: {texto_artigo[int(len(texto_artigo)*0.7):]}", api_key, caminho_modelo)
            st.markdown(res)
            st.download_button("📥 Baixar DOCX", gerar_docx_download(res, "Referências"), f"Ref_{artigo_file.name}", key="d3")
