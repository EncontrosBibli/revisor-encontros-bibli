import streamlit as st
from docx import Document
from PyPDF2 import PdfReader
import google.generativeai as genai
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

def realizar_analise_oficial(prompt, api_key):
    try:
        genai.configure(api_key=api_key)
        
        # --- AJUSTE ANTI-404: DESCOBERTA AUTOMÁTICA ---
        modelos = genai.list_models()
        nome_modelo = None
        
        # Busca o primeiro modelo Flash disponível para a sua chave
        for m in modelos:
            if 'gemini-1.5-flash' in m.name and 'generateContent' in m.supported_generation_methods:
                nome_modelo = m.name
                break
        
        # Se não achar o flash específico, pega qualquer um que gere conteúdo
        if not nome_modelo:
            for m in modelos:
                if 'generateContent' in m.supported_generation_methods:
                    nome_modelo = m.name
                    break
        
        if not nome_modelo:
            return "Erro: Nenhum modelo disponível para esta API Key."

        # Usa o nome exato retornado pelo Google
        model = genai.GenerativeModel(nome_modelo)
        response = model.generate_content(prompt)
        return response.text

    except Exception as e:
        erro_msg = str(e)
        if "429" in erro_msg:
            return "ERRO_COTA"
        return f"Erro na API: {erro_msg}"

# --- INTERFACE ---
st.title("🛡️ Painel de Editoração - Revista Encontros Bibli")

with st.sidebar:
    st.header("Configuração")
    api_key_input = st.text_input("🔑 API Key:", type="password")
    api_key = api_key_input if api_key_input else st.secrets.get("GEMINI_API_KEY", "")
    
    st.divider()
    if st.button("🧹 Novo Artigo"):
        st.session_state.clear()
        st.rerun()

if not api_key:
    st.warning("Insira a API Key para começar.")
    st.stop()

arquivo = st.file_uploader("📂 Subir Artigo (DOCX)", type="docx")

if arquivo:
    with st.spinner("Lendo documento..."):
        doc = Document(arquivo)
        texto_completo = "\n".join([p.text for p in doc.paragraphs if p.text.strip()])
    
    st.success("Documento carregado!")
    tab1, tab2, tab3 = st.tabs(["📐 Estrutura", "✍️ Gramática", "📚 Referências"])

    # --- TAB 1: ESTRUTURA ---
    with tab1:
        if st.button("Analisar Estrutura", key="btn_est"):
            with st.spinner("Analisando estrutura..."):
                res = realizar_analise_oficial(f"Analise a estrutura (título, resumo, palavras-chave) deste artigo: {texto_completo[:10000]}", api_key)
                st.markdown(res)
                if "Erro" not in res:
                    st.download_button("📥 Salvar Relatório", gerar_docx_download(res, "Estrutura"), f"Estrutura_{arquivo.name}", key="dl_est")

    # --- TAB 2: GRAMÁTICA ---
    with tab2:
        if st.button("Analisar Gramática", key="btn_gram"):
            tamanho = 15000
            blocos = [texto_completo[i:i+tamanho] for i in range(0, len(texto_completo), tamanho)]
            relatorio_final = ""
            progresso = st.progress(0)
            status_txt = st.empty()
            
            for idx, bloco in enumerate(blocos):
                status_txt.text(f"Analisando parte {idx+1} de {len(blocos)}...")
                r = realizar_analise_oficial(f"Revise gramática e citações ABNT: {bloco}", api_key)
                
                if r == "ERRO_COTA":
                    st.warning("Cota atingida. Aguardando 60s para retomar...")
                    time.sleep(60)
                    r = realizar_analise_oficial(f"Revise gramática e citações ABNT: {bloco}", api_key)
                
                relatorio_final += f"\n### Parte {idx+1}\n{r}"
                time.sleep(5) 
                progresso.progress((idx+1)/len(blocos))
            
            status_txt.empty()
            st.markdown(relatorio_final)
            if relatorio_final and "Erro" not in relatorio_final:
                st.download_button("📥 Salvar Relatório", gerar_docx_download(relatorio_final, "Gramática"), f"Gramatica_{arquivo.name}", key="dl_gram")

    # --- TAB 3: REFERÊNCIAS ---
    with tab3:
        if st.button("Analisar Referências", key="btn_ref"):
            with st.spinner("Analisando referências..."):
                res = realizar_analise_oficial(f"Verifique as referências NBR 6023 (títulos em negrito): {texto_completo[-8000:]}", api_key)
                st.markdown(res)
                if "Erro" not in res:
                    st.download_button("📥 Salvar Relatório", gerar_docx_download(res, "Referências"), f"Ref_{arquivo.name}", key="dl_ref")
