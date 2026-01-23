import streamlit as st
from docx import Document
from PyPDF2 import PdfReader
import requests
import time
from io import BytesIO

# --- CONFIGURAÇÃO ---
st.set_page_config(page_title="Editoria Encontros Bibli", layout="wide", page_icon="🛡️")

def gerar_docx(conteudo, titulo):
    doc = Document()
    doc.add_heading(titulo, 0)
    for linha in conteudo.split('\n'):
        if linha.startswith('###'):
            doc.add_heading(linha.replace('###', '').strip(), level=1)
        elif linha.strip():
            doc.add_paragraph(linha)
    buf = BytesIO()
    doc.save(buf)
    buf.seek(0)
    return buf

# --- FUNÇÃO DE ANÁLISE (URL CORRIGIDA) ---
def analisar(prompt, api_key):
    # Esta é a URL exata que o Google espera para o Gemini 1.5 Flash
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
    
    headers = {'Content-Type': 'application/json'}
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.2, "maxOutputTokens": 8192}
    }
    
    try:
        res = requests.post(url, json=payload, headers=headers, timeout=60)
        if res.status_code == 200:
            return res.json()['candidates'][0]['content']['parts'][0]['text']
        elif res.status_code == 429:
            return "ERRO_COTA"
        else:
            return f"Erro {res.status_code}: {res.text}"
    except Exception as e:
        return f"Falha de conexão: {e}"

# --- INTERFACE ---
st.title("🛡️ Painel de Editoração - Encontros Bibli")

with st.sidebar:
    api_key = st.text_input("🔑 API Key do Editor:", type="password")
    if not api_key:
        api_key = st.secrets.get("GEMINI_API_KEY", "")
    if st.button("🧹 Novo Artigo"):
        st.session_state.clear()
        st.rerun()

if not api_key:
    st.warning("Insira a API Key para começar.")
    st.stop()

arquivo = st.file_uploader("📂 Subir Artigo (DOCX)", type="docx")

if arquivo:
    doc = Document(arquivo)
    texto_artigo = "\n".join([p.text for p in doc.paragraphs])
    
    t1, t2, t3 = st.tabs(["📐 Estrutura", "✍️ Gramática", "📚 Referências"])

    with t1:
        if st.button("Analisar Estrutura"):
            with st.spinner("Analisando..."):
                res = analisar(f"Analise a estrutura (título, resumo, palavras-chave) deste texto: {texto_artigo[:10000]}", api_key)
                st.markdown(res)
                if "Erro" not in res:
                    st.download_button("📥 Salvar Relatório", gerar_docx(res, "Estrutura"), f"Estrutura_{arquivo.name}")

    with t2:
        if st.button("Analisar Gramática"):
            # Dividindo em blocos para evitar erro de cota
            blocos = [texto_artigo[i:i+15000] for i in range(0, len(texto_artigo), 15000)]
            relatorio = ""
            for idx, b in enumerate(blocos):
                st.write(f"Processando parte {idx+1}...")
                r = analisar(f"Revise a gramática e citações ABNT: {b}", api_key)
                if r == "ERRO_COTA":
                    st.warning("Cota atingida. Aguardando 60s...")
                    time.sleep(60)
                    r = analisar(f"Revise a gramática e citações ABNT: {b}", api_key)
                relatorio += f"\n### Parte {idx+1}\n{r}"
                time.sleep(5)
            st.markdown(relatorio)
            st.download_button("📥 Salvar Relatório", gerar_docx(relatorio, "Gramática"), f"Gramatica_{arquivo.name}")

    with t3:
        if st.button("Analisar Referências"):
            with st.spinner("Analisando..."):
                res = analisar(f"Verifique as referências ABNT NBR 6023: {texto_artigo[-8000:]}", api_key)
                st.markdown(res)
                if "Erro" not in res:
                    st.download_button("📥 Salvar Relatório", gerar_docx(res, "Referências"), f"Ref_{arquivo.name}")
