import streamlit as st
from docx import Document
import google.generativeai as genai
import time
from io import BytesIO

# --- 1. CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Editoria Encontros Bibli", layout="wide", page_icon="🛡️")

# --- 2. FUNÇÕES DE APOIO ---
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
        
        # Descoberta automática do modelo para evitar Erro 404
        modelos = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        nome_modelo = next((m for m in modelos if 'gemini-1.5-flash' in m), None)
        
        if not nome_modelo:
            if modelos:
                nome_modelo = modelos[0]
            else:
                return "Erro: Nenhum modelo disponível nesta chave API."

        model = genai.GenerativeModel(nome_modelo)
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        if "429" in str(e): return "ERRO_COTA"
        return f"Erro na API: {str(e)}"

# --- 3. INTERFACE ---
st.title("🛡️ Painel de Editoração - Encontros Bibli")

with st.sidebar:
    st.header("Configuração")
    api_key_input = st.text_input("🔑 API Key:", type="password")
    # Tenta pegar dos Secrets se o campo estiver vazio
    api_key = api_key_input if api_key_input else st.secrets.get("GEMINI_API_KEY", "")
    
    st.divider()
    if st.button("🧹 Limpar Sessão"):
        st.session_state.clear()
        st.rerun()

if not api_key:
    st.info("👈 Por favor, insira a API Key na barra lateral.")
    st.stop()

arquivo = st.file_uploader("📂 Suba o artigo em DOCX", type="docx")

if arquivo:
    doc_file = Document(arquivo)
    texto_completo = "\n".join([p.text for p in doc_file.paragraphs if p.text.strip()])
    
    st.success(f"Artigo '{arquivo.name}' pronto para análise!")

    # --- 4. ABAS E BOTÕES ---
    tab1, tab2, tab3 = st.tabs(["📐 Estrutura", "✍️ Gramática", "📚 Referências"])

    with tab1:
        st.subheader("Análise de Elementos Pré-textuais")
        if st.button("Executar Análise de Estrutura"):
            with st.spinner("Analisando..."):
                res = realizar_analise(f"Analise a estrutura deste artigo: {texto_completo[:8000]}", api_key)
                st.markdown(res)
                if "Erro" not in res:
                    st.download_button("📥 Baixar Relatório", gerar_docx(res, "Estrutura"), f"Estrutura_{arquivo.name}")

    with tab2:
        st.subheader("Revisão Gramatical e Ortográfica")
        if st.button("Executar Revisão de Texto"):
            # Processamento em blocos para evitar erros de limite
            blocos = [texto_completo[i:i+15000] for i in range(0, len(texto_completo), 15000)]
            relatorio_final = ""
            progresso = st.progress(0)
            
            for idx, bloco in enumerate(blocos):
                st.write(f"Processando parte {idx+1}...")
                r = realizar_analise(f"Corrija erros gramaticais: {bloco}", api_key)
                if r == "ERRO_COTA":
                    st.warning("Cota excedida. Aguardando 60s...")
                    time.sleep(60)
                    r = realizar_analise(f"Corrija erros gramaticais: {bloco}", api_key)
                relatorio_final += f"\n### Parte {idx+1}\n{r}"
                time.sleep(5)
                progresso.progress((idx+1)/len(blocos))
            
            st.markdown(relatorio_final)
            if relatorio_final and "Erro" not in relatorio_final:
                st.download_button("📥 Baixar Relatório", gerar_docx(relatorio_final, "Gramatica"), f"Gramatica_{arquivo.name}")

    with tab3:
        st.subheader("Verificação de Referências (NBR 6023)")
        if st.button("Validar Referências"):
            with st.spinner("Verificando referências..."):
                res = realizar_analise(f"Verifique as referências bibliográficas: {texto_completo[-8000:]}", api_key)
                st.markdown(res)
                if "Erro" not in res:
                    st.download_button("📥 Baixar Relatório", gerar_docx(res, "Referencias"), f"Ref_{arquivo.name}")
