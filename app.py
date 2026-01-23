import streamlit as st
from docx import Document
from PyPDF2 import PdfReader
import requests
import time
from io import BytesIO

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Editoria Encontros Bibli", layout="wide", page_icon="🛡️")

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

# --- A FUNÇÃO DE SUCESSO REVISADA ---
def realizar_analise(prompt, api_key):
    # Lista de todas as variações de URL que o Google aceita
    urls_tentativas = [
        f"https://generativelanguage.googleapis.com/v1/models/gemini-1.5-flash:generateContent?key={api_key}",
        f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}",
        f"https://generativelanguage.googleapis.com/v1beta/gemini-1.5-flash:generateContent?key={api_key}"
    ]
    
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.1, "maxOutputTokens": 8192}
    }
    
    headers = {'Content-Type': 'application/json'}
    
    for url in urls_tentativas:
        try:
            res = requests.post(url, json=payload, headers=headers, timeout=60)
            if res.status_code == 200:
                return res.json()['candidates'][0]['content']['parts'][0]['text']
            if res.status_code == 429:
                return "ERRO_COTA"
            # Se for 404, continua para a próxima URL da lista
            continue
        except:
            continue
            
    return "ERRO_404_TOTAL"

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
    st.warning("Insira a API Key para começar.")
    st.stop()

arquivo = st.file_uploader("📂 Subir Artigo (DOCX)", type="docx")

if arquivo:
    doc = Document(arquivo)
    texto_completo = "\n".join([p.text for p in doc.paragraphs if p.text.strip()])
    
    tab1, tab2, tab3 = st.tabs(["📐 Estrutura", "✍️ Gramática", "📚 Referências"])

    with tab1:
        if st.button("Analisar Estrutura"):
            with st.spinner("Analisando..."):
                res = realizar_analise(f"Verifique a estrutura do artigo: {texto_completo[:10000]}", api_key)
                if res == "ERRO_404_TOTAL":
                    st.error("Erro Crítico: O Google não reconheceu o modelo em nenhuma URL. Verifique se a chave é do tipo 'Gemini API' no AI Studio.")
                else:
                    st.markdown(res)
                    if "Erro" not in res:
                        st.download_button("📥 Salvar Relatório", gerar_docx_download(res, "Estrutura"), f"Estrutura_{arquivo.name}")

    with tab2:
        if st.button("Analisar Gramática"):
            tamanho = 18000
            blocos = [texto_completo[i:i+tamanho] for i in range(0, len(texto_completo), tamanho)]
            relatorio_final = ""
            progresso = st.progress(0)
            
            for idx, bloco in enumerate(blocos):
                st.write(f"Analisando parte {idx+1}...")
                r = realizar_analise(f"Revise gramática e citações ABNT: {bloco}", api_key)
                
                if r == "ERRO_COTA":
                    st.warning("Cota atingida. Aguardando 60s...")
                    time.sleep(60)
                    r = realizar_analise(f"Revise gramática e citações ABNT: {bloco}", api_key)
                
                relatorio_final += f"\n### Parte {idx+1}\n{r}"
                time.sleep(5)
                progresso.progress((idx+1)/len(blocos))
                
            st.markdown(relatorio_final)
            if relatorio_final and "ERRO" not in relatorio_final:
                st.download_button("📥 Salvar Relatório", gerar_docx_download(relatorio_final, "Gramática"), f"Gramatica_{arquivo.name}")

    with tab3:
        if st.button("Analisar Referências"):
            with st.spinner("Analisando..."):
                res = realizar_analise(f"Verifique as referências NBR 6023: {texto_completo[-8000:]}", api_key)
                st.markdown(res)
                if "ERRO" not in res:
                    st.download_button("📥 Salvar Relatório", gerar_docx_download(res, "Referências"), f"Ref_{arquivo.name}")
