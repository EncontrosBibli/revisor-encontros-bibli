import streamlit as st
import google.generativeai as genai
from docx import Document
from io import BytesIO

st.set_page_config(page_title="Editoria Encontros Bibli")

def realizar_analise(prompt, api_key):
    try:
        genai.configure(api_key=api_key)
        # Forçamos o modelo estável mais recente
        model = genai.GenerativeModel('gemini-1.5-flash-latest')
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"Erro Direto: {str(e)}"

st.title("🛡️ Editoria Encontros Bibli")

api_key = st.sidebar.text_input("Chave API:", type="password")
arquivo = st.file_uploader("Subir DOCX", type="docx")

if arquivo and api_key:
    doc = Document(arquivo)
    texto = "\n".join([p.text for p in doc.paragraphs])
    
    if st.button("Iniciar Análise de Teste"):
        with st.spinner("Conectando..."):
            res = realizar_analise("Faça um resumo de 2 frases deste texto: " + texto[:2000], api_key)
            st.markdown(res)
