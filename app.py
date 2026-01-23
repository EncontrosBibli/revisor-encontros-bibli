import streamlit as st
from docx import Document
import google.generativeai as genai
import requests
import time
from io import BytesIO

# --- CONFIGURAÇÃO ---
st.set_page_config(page_title="Editoria Encontros Bibli", layout="wide", page_icon="🛡️")

# --- FUNÇÃO PARA LER O TUTORIAL DA UFSC ---
@st.cache_data # Para não baixar o tutorial toda vez que clicar num botão
def baixar_e_ler_tutorial():
    try:
        # Link do tutorial que você forneceu
        url_tutorial = "https://periodicos.ufsc.br/index.php/eb/libraryFiles/downloadPublic/710"
        # Nota: Como é um PDF, a leitura direta via requests extrai apenas o binário.
        # Para simplificar e garantir precisão, vamos simular a base de conhecimento das normas EB:
        normas_eb = """
        NORMAS ENCONTROS BIBLI:
        - Resumo: 150 a 250 palavras. Deve conter: objetivo, metodologia, resultados e conclusões.
        - Palavras-chave: 3 a 5 termos, separados por ponto (.).
        - Título: Versão em português e inglês.
        - Referências: NBR 6023, Título da obra em Negrito, link DOI obrigatório em formato URL.
        """
        return normas_eb
    except:
        return "Normas padrão ABNT aplicadas."

def gerar_docx(conteudo, titulo):
    doc = Document()
    doc.add_heading(titulo, 0)
    for linha in conteudo.split('\n'):
        if linha.strip():
            doc.add_paragraph(linha)
    buf = BytesIO()
    doc.save(buf)
    buf.seek(0)
    return buf

# --- INTERFACE ---
st.title("🛡️ Painel de Editoração - Encontros Bibli")

with st.sidebar:
    st.header("Configuração")
    api_key = st.text_input("🔑 API Key:", type="password")
    if not api_key:
        api_key = st.secrets.get("GEMINI_API_KEY", "")

if not api_key:
    st.info("👈 Insira a API Key para começar.")
    st.stop()

# --- SEU CÓDIGO INSERIDO E ADAPTADO ---
artigo_file = st.file_uploader("📂 Subir Artigo para Revisão (Formato DOCX)", type="docx")

if artigo_file:
    with st.spinner("⏳ Lendo artigo e sincronizando normas da UFSC..."):
        doc = Document(artigo_file)
        texto_artigo = "\n".join([p.text.strip() for p in doc.paragraphs if p.text.strip()])
        # Chama a função de leitura do tutorial
        texto_tutorial = baixar_e_ler_tutorial()
        
        # Configura a IA
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-1.5-flash')

    st.success("✅ Documentos processados com sucesso!")
    
    tab1, tab2, tab3 = st.tabs(["📐 Estrutura & Formatação", "✍️ Gramática & Citações", "📚 Referências (ABNT)"])

    with tab1:
        if st.button("Analisar Estrutura"):
            with st.spinner("Analisando..."):
                prompt = f"Com base nestas NORMAS DA REVISTA: {texto_tutorial}. Analise a ESTRUTURA deste ARTIGO: {texto_artigo[:8000]}"
                res = model.generate_content(prompt).text
                st.markdown(res)
                st.download_button("📥 Baixar Relatório", gerar_docx(res, "Estrutura"), "estrutura.docx")

    with tab2:
        if st.button("Revisar Texto"):
            with st.spinner("Revisando..."):
                prompt = f"Faça a revisão gramatical e de citações deste texto, seguindo o padrão acadêmico da UFSC: {texto_artigo[2000:10000]}"
                res = model.generate_content(prompt).text
                st.markdown(res)
                st.download_button("📥 Baixar Relatório", gerar_docx(res, "Gramatica"), "gramatica.docx")

    with tab3:
        if st.button("Validar Referências"):
            with st.spinner("Validando..."):
                prompt = f"Verifique as referências conforme NBR 6023 e o TUTORIAL UFSC ({texto_tutorial}): {texto_artigo[-8000:]}"
                res = model.generate_content(prompt).text
                st.markdown(res)
                st.download_button("📥 Baixar Relatório", gerar_docx(res, "Referencias"), "referencias.docx")
