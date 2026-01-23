import streamlit as st
from docx import Document
from PyPDF2 import PdfReader
import requests
import time
from io import BytesIO

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Editoria Encontros Bibli", layout="wide", page_icon="🛡️")

# --- FUNÇÕES DE APOIO ---
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

@st.cache_data(show_spinner=False)
def descobrir_modelo_viva(api_key):
    """Esta foi a função que resolveu o 404: ela pergunta ao Google o nome exato do modelo."""
    for versao in ["v1beta", "v1"]:
        url = f"https://generativelanguage.googleapis.com/{versao}/models?key={api_key}"
        try:
            res = requests.get(url, timeout=10)
            if res.status_code == 200:
                modelos = res.json().get('models', [])
                for m in modelos:
                    # Buscamos o flash 1.5 que é o que tem a melhor cota
                    if "gemini-1.5-flash" in m['name'].lower():
                        return f"{versao}/{m['name']}" # Retorna v1beta/models/gemini-1.5-flash
        except:
            continue
    return None

def realizar_analise(prompt, api_key, modelo_path):
    url = f"https://generativelanguage.googleapis.com/{modelo_path}:generateContent?key={api_key}"
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.2, "maxOutputTokens": 8192}
    }
    try:
        res = requests.post(url, json=payload, timeout=90)
        if res.status_code == 200:
            return res.json()['candidates'][0]['content']['parts'][0]['text']
        elif res.status_code == 429:
            return "ERRO_COTA"
        else:
            return f"Erro {res.status_code}: {res.text}"
    except Exception as e:
        return f"Erro de conexão: {e}"

# --- INTERFACE ---
st.title("🛡️ Painel de Editoração - Encontros Bibli")

with st.sidebar:
    api_key_input = st.text_input("🔑 API Key:", type="password")
    api_key = api_key_input if api_key_input else st.secrets.get("GEMINI_API_KEY", "")
    
    if st.button("🧹 Novo Artigo"):
        st.session_state.clear()
        st.rerun()

if not api_key:
    st.warning("Insira a chave para começar.")
    st.stop()

# Tenta descobrir o modelo (A solução do 404)
modelo_escolhido = descobrir_modelo_viva(api_key)

if not modelo_escolhido:
    st.error("Erro 404: O Google não autorizou o modelo para esta chave. Verifique se a chave é nova.")
    st.stop()

arquivo = st.file_uploader("📂 Subir Artigo (DOCX)", type="docx")

if arquivo:
    doc = Document(arquivo)
    texto_completo = "\n".join([p.text for p in doc.paragraphs])
    
    t1, t2, t3 = st.tabs(["📐 Estrutura", "✍️ Gramática", "📚 Referências"])

    with t1:
        if st.button("Analisar Estrutura"):
            with st.spinner("Analisando..."):
                res = realizar_analise(f"Verifique título, resumo e palavras-chave: {texto_completo[:10000]}", api_key, modelo_escolhido)
                st.markdown(res)
                if "Erro" not in res:
                    st.download_button("📥 Salvar Relatório", gerar_docx_download(res, "Estrutura"), f"Estrutura_{arquivo.name}", key="d1")

    with t2:
        if st.button("Analisar Gramática"):
            tamanho = 20000
            blocos = [texto_completo[i:i+tamanho] for i in range(0, len(texto_completo), tamanho)]
            relatorio_final = ""
            progresso = st.progress(0)
            
            for idx, bloco in enumerate(blocos):
                st.write(f"Analisando parte {idx+1}...")
                r = realizar_analise(f"Revise gramática e citações: {bloco}", api_key, modelo_escolhido)
                if r == "ERRO_COTA":
                    st.warning("Cota atingida. Aguardando 60s...")
                    time.sleep(60)
                    r = realizar_analise(f"Revise gramática e citações: {bloco}", api_key, modelo_escolhido)
                relatorio_final += f"\n### Parte {idx+1}\n{r}"
                time.sleep(5)
                progresso.progress((idx+1)/len(blocos))
                
            st.markdown(relatorio_final)
            if relatorio_final:
                st.download_button("📥 Salvar Relatório", gerar_docx_download(relatorio_final, "Gramática"), f"Gramatica_{arquivo.name}", key="d2")

    with t3:
        if st.button("Analisar Referências"):
            with st.spinner("Analisando..."):
                res = realizar_analise(f"Verifique referências ABNT: {texto_completo[-8000:]}", api_key, modelo_escolhido)
                st.markdown(res)
                if "Erro" not in res:
                    st.download_button("📥 Salvar Relatório", gerar_docx_download(res, "Referências"), f"Ref_{arquivo.name}", key="d3")
