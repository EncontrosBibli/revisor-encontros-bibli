import streamlit as st
from docx import Document
from PyPDF2 import PdfReader
import requests
import os
import time # incluindo um mecanismo de pausa (time.sleep) para não sobrecarregar a API

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Editoria Encontros Bibli", layout="wide", page_icon="🛡️")

# --- 1. GESTÃO DO TUTORIAL (ENDEREÇO FIXO) ---
URL_TUTORIAL = "https://periodicos.ufsc.br/index.php/eb/libraryFiles/downloadPublic/710"
CAMINHO_LOCAL_TUTORIAL = "tutorial_encontros_bibli.pdf"

@st.cache_data(show_spinner=False)
def baixar_e_ler_tutorial():
    """Baixa o tutorial do site da UFSC e extrai o texto."""
    try:
        response = requests.get(URL_TUTORIAL, timeout=10)
        with open(CAMINHO_LOCAL_TUTORIAL, "wb") as f:
            f.write(response.content)
        
        pdf = PdfReader(CAMINHO_LOCAL_TUTORIAL)
        texto = "\n".join([page.extract_text() for page in pdf.pages])
        return texto
    except Exception as e:
        return f"Erro ao acessar diretrizes online: {e}"

# --- 2. FUNÇÕES DE APOIO ---
def limpar_sessao():
    st.session_state.clear()
    st.rerun()

def descobrir_modelo(chave):
    url = f"https://generativelanguage.googleapis.com/v1/models?key={chave}"
    try:
        res = requests.get(url)
        if res.status_code == 200:
            modelos = res.json().get('models', [])
            for m in modelos:
                if "generateContent" in m.get("supportedGenerationMethods", []):
                    return m.get("name")
    except: return None
    return None

# --- INTERFACE ---
st.title("🛡️ Painel de Editoração - Revista Encontros Bibli")
st.caption("Sistema de Revisão Técnica, Normativa e Linguística (PT/EN/ES)")

# BARRA LATERAL
with st.sidebar:
    st.header("Configurações")
    api_key = st.text_input("🔑 API Key do Editor:", type="password")
    if "GEMINI_API_KEY" in st.secrets:
        api_key = st.secrets["GEMINI_API_KEY"]
        st.info("Utilizando chave mestra do sistema.")
    
    st.divider()
    if st.button("🧹 Limpar e Novo Artigo"):
        limpar_sessao()

if not api_key:
    st.warning("👈 Por favor, insira a API Key para ativar os módulos de IA.")
    st.stop()

nome_modelo = descobrir_modelo(api_key)

# --- FLUXO PRINCIPAL ---
artigo_file = st.file_uploader("📂 Subir Artigo para Revisão (Formato DOCX)", type="docx")

if artigo_file:
    with st.spinner("⏳ Lendo artigo e sincronizando normas da UFSC..."):
        doc = Document(artigo_file)
        texto_artigo = "\n".join([p.text.strip() for p in doc.paragraphs if p.text.strip()])
        texto_tutorial = baixar_e_ler_tutorial()

    st.success("✅ Documentos processados com sucesso!")
    
    # Módulos de Análise
    tab1, tab2, tab3 = st.tabs(["📐 Estrutura & Formatação", "✍️ Gramática & Citações", "📚 Referências (ABNT)"])

    def realizar_analise(prompt_texto):
        url = f"https://generativelanguage.googleapis.com/v1/{nome_modelo}:generateContent?key={api_key}"
        payload = {
            "contents": [{"parts": [{"text": prompt_texto}]}],
            "generationConfig": {"temperature": 0.1, "maxOutputTokens": 8192}
        }
        res = requests.post(url, json=payload)
        return res.json()['candidates'][0]['content']['parts'][0]['text'] if res.status_code == 200 else f"Erro: {res.text}"

    with tab1:
        if st.button("Executar Verificação de Estrutura"):
            with st.spinner("Analisando..."):
                prompt = f"REVISOR RIGOROSO: Compare o artigo com o tutorial da UFSC abaixo. Verifique rigorosamente a estrutura: títulos bilingues, resumo (100-250 palavras), palavras-chave separadas por ponto final. Identifique o idioma (PT, EN ou ES) e verifique a coerência estrutural.\nTUTORIAL: {texto_tutorial}\nTEXTO: {texto_artigo[:6000]}"
                st.markdown(realizar_analise(prompt))

    with tab2:
        if st.button("Executar Revisão Linguística"):
            with st.spinner("Analisando gramática e citações de forma robusta..."):
                # Aumentamos o bloco para 8000 caracteres para reduzir o número de partes
                tamanho_bloco = 8000 
                blocos = [texto_artigo[i:i + tamanho_bloco] for i in range(0, len(texto_artigo), tamanho_bloco)]
                
                relatorio_final = ""
                progresso = st.progress(0)
                placeholder_status = st.empty() # Para mostrar em qual parte está
                
                for idx, bloco in enumerate(blocos):
                    placeholder_status.text(f"Analisando bloco {idx+1} de {len(blocos)}...")
                    
                    prompt = f"""
                    Atue como Revisor Linguístico Sênior. Analise o TRECHO abaixo:
                    1. Ortografia/Gramática (PT, EN ou ES).
                    2. Citações ABNT (recuo 4cm p/ >3 linhas).
                    
                    Formato de resposta:
                    ❌ ERRO: [Original]
                    ✔️ SUGESTÃO: [Correção]
                    (Se não houver erros, diga: "OK")
                    
                    TRECHO:
                    {bloco}
                    """
                    
                    try:
                        resultado_parcial = realizar_analise(prompt)
                        if "OK" not in resultado_parcial.upper():
                            relatorio_final += f"\n### Seção {idx+1}\n" + resultado_parcial
                        
                        # Pequena pausa para não dar erro de limite (Rate Limit)
                        time.sleep(2) 
                        
                    except Exception as e:
                        relatorio_final += f"\n⚠️ Erro na Seção {idx+1}: O sistema não conseguiu processar esta parte."
                    
                    progresso.progress((idx + 1) / len(blocos))
                
                placeholder_status.empty() # Limpa o status ao terminar
                
                if relatorio_final == "":
                    st.success("Nenhum erro encontrado nos blocos analisados.")
                else:
                    st.markdown(relatorio_final)

    with tab3:
        if st.button("Executar Validação de Referências"):
            with st.spinner("Analisando..."):
                referencias = texto_artigo[int(len(texto_artigo)*0.7):]
                prompt = f"Verifique se as referências seguem a ABNT NBR 6023:2018. Itens obrigatórios: Título da obra em NEGRITO, ordem alfabética, nomes de autores padronizados. Liste apenas as que precisam de correção com sugestões.\nREFERÊNCIAS:\n{referencias}"
                st.markdown(realizar_analise(prompt))
