import streamlit as st
from docx import Document
import google.generativeai as genai
import time
from io import BytesIO

# --- 1. CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Editoria Encontros Bibli", layout="wide", page_icon="🛡️")

# --- 2. FUNÇÕES DE APOIO (Word e API) ---
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

def realizar_analise(prompt, api_key):
    try:
        genai.configure(api_key=api_key)
        # O modelo 'gemini-1.5-flash' é o padrão para evitar o erro 404
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        if "429" in str(e): return "ERRO_COTA"
        return f"Erro na API: {str(e)}"

# --- 3. INTERFACE DO USUÁRIO ---
st.title("🛡️ Painel de Editoração - Encontros Bibli")

with st.sidebar:
    st.header("Configuração")
    api_key = st.text_input("🔑 API Key:", type="password")
    if not api_key:
        api_key = st.secrets.get("GEMINI_API_KEY", "")
    
    st.divider()
    if st.button("🧹 Limpar Sessão"):
        st.session_state.clear()
        st.rerun()

if not api_key:
    st.warning("⚠️ Insira a API Key na lateral para ativar as funções.")
    st.stop()

# --- 4. CARREGAMENTO DO ARQUIVO ---
arquivo = st.file_uploader("📂 Escolha o artigo em DOCX", type="docx")

if arquivo:
    # Processamento do texto
    doc_file = Document(arquivo)
    texto_completo = "\n".join([p.text for p in doc_file.paragraphs if p.text.strip()])
    
    st.success(f"Artigo '{arquivo.name}' carregado!")

    # --- 5. ABAS DE TRABALHO (AQUI ESTÃO AS OPÇÕES) ---
    tab1, tab2, tab3 = st.tabs(["📐 Estrutura", "✍️ Gramática", "📚 Referências"])

    with tab1:
        st.subheader("Análise Pré-textual")
        if st.button("Analisar Estrutura"):
            with st.spinner("Processando..."):
                prompt = f"Avalie a clareza do título, resumo e palavras-chave deste texto: {texto_completo[:8000]}"
                res = realizar_analise(prompt, api_key)
                st.markdown(res)
                if "Erro" not in res:
                    st.download_button("📥 Baixar Relatório", gerar_docx(res, "Estrutura"), "estrutura.docx")

    with tab2:
        st.subheader("Revisão Gramatical")
        if st.button("Executar Revisão"):
            # Divisão em blocos para textos longos
            blocos = [texto_completo[i:i+15000] for i in range(0, len(texto_completo), 15000)]
            relatorio = ""
            progresso = st.progress(0)
            for idx, b in enumerate(blocos):
                r = realizar_analise(f"Corrija gramática e ortografia: {b}", api_key)
                if r == "ERRO_COTA":
                    st.warning("Aguardando 60s por limite de cota...")
                    time.sleep(60)
                    r = realizar_analise(f"Corrija gramática e ortografia: {b}", api_key)
                relatorio += f"\n### Parte {idx+1}\n{r}"
                time.sleep(4)
                progresso.progress((idx+1)/len(blocos))
            st.markdown(relatorio)
            if relatorio:
                st.download_button("📥 Baixar Relatório", gerar_docx(relatorio, "Gramatica"), "gramatica.docx")

    with tab3:
        st.subheader("Normatização ABNT (NBR 6023)")
        if st.button("Validar Referências"):
            with st.spinner("Analisando..."):
                # Foca no final do documento (referências)
                res = realizar_analise(f"Verifique as referências bibliográficas (ABNT): {texto_completo[-8000:]}", api_key)
                st.markdown(res)
                if "Erro" not in res:
                    st.download_button("📥 Baixar Relatório", gerar_docx(res, "Referencias"), "referencias.docx")
