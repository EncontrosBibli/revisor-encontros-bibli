import streamlit as st
from docx import Document
from PyPDF2 import PdfReader
import requests
import time
from io import BytesIO

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Editoria Encontros Bibli", layout="wide", page_icon="🛡️")

# --- 1. GESTÃO DO TUTORIAL ---
URL_TUTORIAL = "https://periodicos.ufsc.br/index.php/eb/libraryFiles/downloadPublic/710"
CAMINHO_LOCAL_TUTORIAL = "tutorial_encontros_bibli.pdf"

@st.cache_data(show_spinner=False)
def baixar_e_ler_tutorial():
    try:
        response = requests.get(URL_TUTORIAL, timeout=15)
        with open(CAMINHO_LOCAL_TUTORIAL, "wb") as f:
            f.write(response.content)
        pdf = PdfReader(CAMINHO_LOCAL_TUTORIAL)
        texto = "\n".join([page.extract_text() for page in pdf.pages])
        return texto
    except Exception as e:
        return f"Erro ao acessar diretrizes: {e}"

# --- 2. FUNÇÕES DE APOIO ---
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

# --- 3. FUNÇÃO DE ANÁLISE ROBUSTA (SEM ERRO 404) ---
def realizar_analise_robusta(prompt_texto, api_key, max_tentativas=3):
    # Tentamos os dois endpoints mais comuns do Google
    urls_para_tentar = [
        f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}",
        f"https://generativelanguage.googleapis.com/v1/models/gemini-1.5-flash:generateContent?key={api_key}"
    ]
    
    payload = {
        "contents": [{"parts": [{"text": prompt_texto}]}],
        "generationConfig": {"temperature": 0.1, "maxOutputTokens": 8192}
    }
    
    for tentativa in range(max_tentativas):
        for url in urls_para_tentar:
            try:
                res = requests.post(url, json=payload, timeout=90)
                
                if res.status_code == 200:
                    return res.json()['candidates'][0]['content']['parts'][0]['text']
                
                if res.status_code == 429:
                    st.warning(f"⚠️ Cota atingida. Aguardando 60s (Tentativa {tentativa+1})...")
                    time.sleep(60)
                    break # Sai do loop de URLs para tentar novamente após a pausa
                
                # Se for 404, o loop continua para a próxima URL da lista
                if res.status_code == 404:
                    continue
                    
            except Exception as e:
                continue
    
    return "Erro: Não foi possível conectar ao modelo. Verifique se sua API Key está correta e sem espaços."

# --- INTERFACE ---
st.title("🛡️ Painel de Editoração - Revista Encontros Bibli")

with st.sidebar:
    st.header("Configurações")
    api_key_input = st.text_input("🔑 API Key do Editor:", type="password")
    api_key = api_key_input if api_key_input else st.secrets.get("GEMINI_API_KEY", "")
    
    if st.secrets.get("GEMINI_API_KEY") and not api_key_input:
        st.info("Utilizando chave mestra do sistema.")
    
    st.divider()
    if st.button("🧹 Novo Artigo"):
        st.session_state.clear()
        st.rerun()

if not api_key:
    st.warning("👈 Por favor, insira a API Key para começar.")
    st.stop()

# --- FLUXO PRINCIPAL ---
artigo_file = st.file_uploader("📂 Subir Artigo (DOCX)", type="docx")

if artigo_file:
    with st.spinner("⏳ Processando documentos..."):
        doc = Document(artigo_file)
        texto_artigo = "\n".join([p.text.strip() for p in doc.paragraphs if p.text.strip()])
        texto_tutorial = baixar_e_ler_tutorial()

    st.success("✅ Pronto para análise!")
    tab1, tab2, tab3 = st.tabs(["📐 Estrutura", "✍️ Gramática", "📚 Referências"])

    with tab1:
        if st.button("Analisar Estrutura", key="b1"):
            with st.spinner("Analisando..."):
                res = realizar_analise_robusta(f"Verifique títulos bilingues e resumo (100-250 palavras) conforme: {texto_tutorial}\nTexto: {texto_artigo[:8000]}", api_key)
                st.markdown(res)
                st.download_button("📥 Salvar Relatório (.docx)", gerar_docx_download(res, "Estrutura"), f"Estrutura_{artigo_file.name}")

    with tab2:
        if st.button("Analisar Gramática", key="b2"):
            tamanho = 20000 
            blocos = [texto_artigo[i:i+tamanho] for i in range(0, len(texto_artigo), tamanho)]
            relatorio = ""
            prog = st.progress(0)
            status = st.empty()
            
            for idx, b in enumerate(blocos):
                status.text(f"Analisando parte {idx+1} de {len(blocos)}...")
                r = realizar_analise_robusta(f"Revisão ortográfica e citações ABNT: {b}", api_key)
                relatorio += f"\n### Parte {idx+1}\n{r}"
                time.sleep(10) 
                prog.progress((idx+1)/len(blocos))
                
            status.empty()
            st.markdown(relatorio)
            if relatorio:
                st.download_button("📥 Salvar Relatório (.docx)", gerar_docx_download(relatorio, "Gramática"), f"Gramatica_{artigo_file.name}")

    with tab3:
        if st.button("Analisar Referências", key="b3"):
            with st.spinner("Analisando..."):
                res = realizar_analise_robusta(f"Verifique ABNT 6023 (Negrito no título): {texto_artigo[int(len(texto_artigo)*0.7):]}", api_key)
                st.markdown(res)
                st.download_button("📥 Salvar Relatório (.docx)", gerar_docx_download(res, "Referências"), f"Ref_{artigo_file.name}")
