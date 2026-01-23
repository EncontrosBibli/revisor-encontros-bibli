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
st.caption("Versão atualizada com as normas do Tutorial de Normalização da UFSC/EB.")

with st.sidebar:
    st.header("Configuração")
    api_key_input = st.text_input("🔑 API Key:", type="password")
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
    
    st.success(f"Artigo '{arquivo.name}' carregado!")

    tab1, tab2, tab3 = st.tabs(["📐 Estrutura EB", "✍️ Revisão Textual", "📚 Normas ABNT/EB"])

    with tab1:
        st.subheader("Análise conforme Tutorial Encontros Bibli")
        if st.button("Analisar Estrutura"):
            with st.spinner("Conferindo normas da revista..."):
                prompt_eb = (
                    "Aja como editor da Revista Encontros Bibli (UFSC). Analise o artigo com base no tutorial de normalização da revista: "
                    "1. TÍTULO: Deve ser claro e conciso. Verifique se há versão em inglês. "
                    "2. RESUMO: Deve ser informativo, conter objetivo, metodologia, resultados e conclusões (mín. 150, máx. 250 palavras). "
                    "3. PALAVRAS-CHAVE: Devem ser de 3 a 5, separadas por ponto (.) conforme norma da revista. "
                    "4. SEÇÕES: Verifique se a estrutura segue a lógica: Introdução, Revisão, Metodologia, Resultados/Discussão e Conclusão. "
                    "Apresente as inadequações encontradas. NÃO RESUMA O ARTIGO. "
                    f"\n\nTexto:\n{texto_completo[:10000]}"
                )
                res = realizar_analise(prompt_eb, api_key)
                st.markdown(res)
                if "Erro" not in res:
                    st.download_button("📥 Baixar Relatório", gerar_docx(res, "Estrutura_EB"), f"Estrutura_EB_{arquivo.name}")

    with tab2:
        st.subheader("Revisão de Escrita Científica")
        if st.button("Executar Revisão"):
            blocos = [texto_completo[i:i+15000] for i in range(0, len(texto_completo), 15000)]
            relatorio_final = ""
            progresso = st.progress(0)
            
            for idx, bloco in enumerate(blocos):
                prompt_gram = (
                    "Realize revisão gramatical e de estilo científico. Use o tom formal exigido pela Encontros Bibli. "
                    "Verifique clareza, coesão e objetividade. Identifique erros de ortografia e pontuação. "
                    f"\n\nBloco:\n{bloco}"
                )
                r = realizar_analise(prompt_gram, api_key)
                if r == "ERRO_COTA":
                    time.sleep(60)
                    r = realizar_analise(prompt_gram, api_key)
                relatorio_final += f"\n### Parte {idx+1}\n{r}\n"
                time.sleep(4)
                progresso.progress((idx+1)/len(blocos))
            st.markdown(relatorio_final)
            if relatorio_final:
                st.download_button("📥 Baixar Relatório", gerar_docx(relatorio_final, "Revisao_Gramatical"), f"Revisao_{arquivo.name}")

    with tab3:
        st.subheader("Referências NBR 6023 (Tutorial UFSC)")
        if st.button("Validar Referências"):
            with st.spinner("Analisando ABNT..."):
                prompt_ref = (
                    "Aja como bibliotecário da UFSC. Valide as referências conforme o tutorial da revista Encontros Bibli: "
                    "1. O título da obra deve estar em NEGRITO. "
                    "2. Nomes de autores devem seguir o padrão: SOBRENOME, Nome. "
                    "3. Verifique se o link DOI foi incluído e se está no formato correto (https://doi.org/...). "
                    "4. Verifique a pontuação entre cidade, editora e ano. "
                    "Indique as correções necessárias. "
                    f"\n\nReferências:\n{texto_completo[-8000:]}"
                )
                res = realizar_analise(prompt_ref, api_key)
                st.markdown(res)
                if "Erro" not in res:
                    st.download_button("📥 Baixar Relatório", gerar_docx(res, "Referencias_EB"), f"Ref_EB_{arquivo.name}")
