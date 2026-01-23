import streamlit as st
from docx import Document
import google.generativeai as genai
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

def realizar_analise_oficial(prompt, api_key):
    try:
        genai.configure(api_key=api_key)
        
        # Tenta listar os modelos para garantir que a chave tem acesso
        modelos = list(genai.list_models())
        if not modelos:
            return "Erro: Sua chave não tem acesso a nenhum modelo de IA. Crie uma chave em 'NEW PROJECT' no AI Studio."

        # Seleciona o Gemini 1.5 Flash (mais rápido e gratuito)
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        if "429" in str(e): return "ERRO_COTA"
        return f"Erro na API: {str(e)}"

# --- INTERFACE ---
st.title("🛡️ Painel de Editoração - Revista Encontros Bibli")

with st.sidebar:
    st.header("Configuração de Segurança")
    # A chave é inserida aqui pelo usuário, de forma segura no app rodando
    api_key_input = st.text_input("🔑 Nova API Key (AIza...):", type="password")
    
    st.divider()
    if st.button("🧹 Limpar tudo"):
        st.session_state.clear()
        st.rerun()

# Se não houver chave, o app para aqui com um aviso amigável
if not api_key_input:
    st.info("👈 Gere uma chave nova no AI Studio e insira ao lado para começar.")
    st.stop()

arquivo = st.file_uploader("📂 Subir Artigo (DOCX)", type="docx")

if arquivo:
    doc = Document(arquivo)
    texto_artigo = "\n".join([p.text for p in doc.paragraphs if p.text.strip()])
    
    tab1, tab2, tab3 = st.tabs(["📐 Estrutura", "✍️ Gramática", "📚 Referências"])

    with tab1:
        if st.button("Analisar Estrutura"):
            with st.spinner("Analisando..."):
                res = realizar_analise_oficial(f"Verifique títulos e resumo deste artigo: {texto_artigo[:10000]}", api_key_input)
                st.markdown(res)
                if "Erro" not in res:
                    st.download_button("📥 Baixar DOCX", gerar_docx_download(res, "Estrutura"), f"Estrutura_{arquivo.name}")

    with tab2:
        if st.button("Analisar Gramática"):
            # Divisão em blocos para evitar limites
            blocos = [texto_artigo[i:i+15000] for i in range(0, len(texto_artigo), 15000)]
            relatorio = ""
            progresso = st.progress(0)
            for idx, b in enumerate(blocos):
                r = realizar_analise_oficial(f"Revise gramática e normas ABNT: {b}", api_key_input)
                if r == "ERRO_COTA":
                    st.warning("Aguardando 60s por limite de cota...")
                    time.sleep(60)
                    r = realizar_analise_oficial(f"Revise gramática e normas ABNT: {b}", api_key_input)
                relatorio += f"\n### Parte {idx+1}\n{r}"
                time.sleep(5)
                progresso.progress((idx+1)/len(blocos))
            st.markdown(relatorio)
            if relatorio:
                st.download_button("📥 Baixar DOCX", gerar_docx_download(relatorio, "Gramática"), f"Gramatica_{arquivo.name}")

    with tab3:
        if st.button("Analisar Referências"):
            with st.spinner("Analisando..."):
                res = realizar_analise_oficial(f"Verifique as referências conforme NBR 6023: {texto_artigo[-8000:]}", api_key_input)
                st.markdown(res)
                if "Erro" not in res:
                    st.download_button("📥 Baixar DOCX", gerar_docx_download(res, "Referências"), f"Ref_{arquivo.name}")
