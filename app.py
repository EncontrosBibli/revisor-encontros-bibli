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

# --- FUNÇÃO DE ANÁLISE (A QUE FUNCIONA PARA O 404) ---
def realizar_analise(prompt, api_key):
    # Endpoint v1beta é o mais estável para chaves novas e o modelo Flash
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
    
    headers = {'Content-Type': 'application/json'}
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.1, "maxOutputTokens": 8192}
    }
    
    try:
        # Forçamos o POST com headers explícitos
        res = requests.post(url, json=payload, headers=headers, timeout=90)
        
        if res.status_code == 200:
            return res.json()['candidates'][0]['content']['parts'][0]['text']
        elif res.status_code == 404:
            return "ERRO_404"
        elif res.status_code == 429:
            return "ERRO_COTA"
        else:
            return f"Erro {res.status_code}: {res.text}"
    except Exception as e:
        return f"Erro de conexão: {e}"

# --- INTERFACE ---
st.title("🛡️ Painel de Editoração - Encontros Bibli")

with st.sidebar:
    st.header("Configuração")
    api_key_input = st.text_input("🔑 API Key:", type="password")
    api_key = api_key_input if api_key_input else st.secrets.get("GEMINI_API_KEY", "")
    
    if st.button("🧹 Novo Artigo"):
        st.session_state.clear()
        st.rerun()

if not api_key:
    st.warning("Insira a chave para começar.")
    st.stop()

arquivo = st.file_uploader("📂 Subir Artigo (DOCX)", type="docx")

if arquivo:
    doc = Document(arquivo)
    texto_completo = "\n".join([p.text for p in doc.paragraphs if p.text.strip()])
    
    tab1, tab2, tab3 = st.tabs(["📐 Estrutura", "✍️ Gramática", "📚 Referências"])

    # --- TAB 1: ESTRUTURA ---
    with tab1:
        if st.button("Analisar Estrutura"):
            with st.spinner("Analisando..."):
                res = realizar_analise(f"Verifique título, resumo e palavras-chave: {texto_completo[:10000]}", api_key)
                if res == "ERRO_404":
                    st.error("Erro 404: O modelo não foi encontrado. Tente gerar uma chave em 'New Project' no AI Studio.")
                else:
                    st.markdown(res)
                    if "Erro" not in res:
                        st.download_button("📥 Salvar Relatório", gerar_docx_download(res, "Estrutura"), f"Estrutura_{arquivo.name}")

    # --- TAB 2: GRAMÁTICA ---
    with tab2:
        if st.button("Analisar Gramática"):
            tamanho = 20000
            blocos = [texto_completo[i:i+tamanho] for i in range(0, len(texto_completo), tamanho)]
            relatorio_final = ""
            progresso = st.progress(0)
            
            for idx, bloco in enumerate(blocos):
                st.write(f"Analisando parte {idx+1}...")
                r = realizar_analise(f"Revise gramática e citações: {bloco}", api_key)
                
                if r == "ERRO_COTA":
                    st.warning("Cota atingida. Aguardando 60s...")
                    time.sleep(60)
                    r = realizar_analise(f"Revise gramática e citações: {bloco}", api_key)
                
                relatorio_final += f"\n### Parte {idx+1}\n{r}"
                time.sleep(5)
                progresso.progress((idx+1)/len(blocos))
                
            st.markdown(relatorio_final)
            if relatorio_final and "Erro" not in relatorio_final:
                st.download_button("📥 Salvar Relatório", gerar_docx_download(relatorio_final, "Gramática"), f"Gramatica_{arquivo.name}")

    # --- TAB 3: REFERÊNCIAS ---
    with tab3:
        if st.button("Analisar Referências"):
            with st.spinner("Analisando..."):
                res = realizar_analise(f"Verifique ABNT NBR 6023: {texto_completo[-8000:]}", api_key)
                st.markdown(res)
                if "Erro" not in res and res != "ERRO_404":
                    st.download_button("📥 Salvar Relatório", gerar_docx_download(res, "Referências"), f"Ref_{arquivo.name}")
