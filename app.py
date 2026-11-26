"""Interfaz Streamlit para consultas sobre FastAPI y Docker."""
import streamlit as st
from src.rag import answer

st.set_page_config(page_title="DevDocsRAG", page_icon="📚")
st.title("📚 DevDocsRAG")
st.caption("Asistente de documentación técnica: FastAPI + Docker")
question = st.text_input(
    "Pregunta",
    placeholder="¿Cómo puedo contenerizar una API desarrollada con FastAPI?",
)
domain_label = st.selectbox(
    "Documentación que se consultará",
    ["Automático (según la pregunta)", "Solo FastAPI", "Solo Docker"],
    help="En modo automático el sistema detecta si la pregunta es de FastAPI, "
         "de Docker o de ambas, y busca en la documentación correspondiente.",
)
domain = {
    "Automático (según la pregunta)": None,
    "Solo FastAPI": "fastapi",
    "Solo Docker": "docker",
}[domain_label]
use_rag = st.toggle("Utilizar recuperación RAG", value=True)
if st.button("Consultar") and question.strip():
    try:
        with st.spinner("Consultando documentación y modelo local..."):
            result = answer(question, use_rag=use_rag, domain=domain)
        st.markdown(result["answer"])
        if result["sources"]:
            st.subheader("Fragmentos recuperados")
            for src in result["sources"]:
                with st.expander(f"[{src['id']}] {src['domain'].upper()} · {src['title']} · {src['chunk_id']}"):
                    st.write(src["url"])
                    st.code(src["excerpt"], language="text")
    except Exception as exc:
        st.error(f"No se pudo completar la consulta: {exc}")
