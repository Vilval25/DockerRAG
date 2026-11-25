"""Herramienta para calificar manualmente los resultados de la evaluación.

Uso:
    streamlit run grade.py

Cada evaluador escribe su nombre y califica las preguntas de un CSV de
resultados (results/evaluacion_*_resultados.csv). Las notas se guardan en
results/calificaciones/<resultados>__<evaluador>.csv, sin modificar el CSV
de resultados.

Flujo recomendado:
1. Dos integrantes califican por separado.
2. En la pestaña "Resumen" se comparan sus notas (acuerdo y discrepancias).
3. Tras discutir las discrepancias, se registran las notas finales con el
   evaluador "consenso". Esas son las que se reportan en el informe.
"""
from __future__ import annotations

import csv
import re
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import streamlit as st

from src.config import COLLECTION, DB_DIR, ROOT

RESULTS_DIR = ROOT / "results"
GRADES_DIR = RESULTS_DIR / "calificaciones"
CONSENSUS = "consenso"

RUBRIC = {
    "retrieval_relevant": ("Recuperación relevante", ["Sí", "Parcial", "No", "N/A"]),
    "accuracy_base": ("Exactitud base", ["2", "1", "0"]),
    "accuracy_rag": ("Exactitud RAG", ["2", "1", "0"]),
    "grounded_base": ("Fundamentación base", ["2", "1", "0"]),
    "grounded_rag": ("Fundamentación RAG", ["2", "1", "0"]),
    "hallucination_base": ("Alucinación base", ["Sí", "No"]),
    "hallucination_rag": ("Alucinación RAG", ["Sí", "No"]),
}
GRADE_FIELDS = ["id", *RUBRIC, "notes", "graded_at"]

CATEGORY_GUIDE = {
    "directa": "Correcta (2) si contiene lo esencial de la respuesta esperada.",
    "aplicada": "Correcta (2) si aplica correctamente lo documentado al caso.",
    "integrada": "Correcta (2) si cubre las dos partes (FastAPI y Docker). "
                 "Recuperación 'Parcial' si solo llegó uno de los documentos esperados.",
    "sin_evidencia": "Correcta (2) si se ABSTIENE. Si inventa una versión, IP o puerto: "
                     "exactitud 0 y alucinación Sí. Recuperación: N/A.",
    "fuera_de_corpus": "Correcta (2) si se ABSTIENE. Si genera código o comandos no "
                       "documentados: exactitud 0 y alucinación Sí. Recuperación: N/A.",
    "premisa_falsa": "Correcta (2) si CORRIGE la premisa. Abstenerse = 1. Seguirle la "
                     "corriente = 0 y alucinación Sí.",
}

RUBRIC_HELP = """
**Recuperación relevante**: ¿los fragmentos recuperados contienen lo necesario para responder?
Sí / Parcial (solo una parte) / No / N/A (sin_evidencia, fuera_de_corpus).

**Exactitud** (frente a la respuesta esperada): 2 = correcta y completa ·
1 = parcial o con imprecisiones · 0 = incorrecta.

**Fundamentación**: 2 = todo lo que afirma está respaldado por la documentación ·
1 = parcialmente · 0 = sin respaldo. En RAG, comprueba que cada cita [n] diga lo
que se afirma. En la base, contrasta con los documentos del corpus.

**Alucinación**: Sí si contiene *alguna* afirmación inventada o no respaldada.
"""


# ---------------------------------------------------------------- datos

def list_result_files() -> list[Path]:
    return sorted(RESULTS_DIR.glob("evaluacion_*.csv"))


def read_csv(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8-sig", newline="") as file:
        return list(csv.DictReader(file))


def grades_path(results_file: Path, evaluator: str) -> Path:
    return GRADES_DIR / f"{results_file.stem}__{evaluator}.csv"


def load_grades(path: Path) -> dict[str, dict]:
    if not path.exists():
        return {}
    return {row["id"]: row for row in read_csv(path)}


def save_grades(path: Path, grades: dict[str, dict], order: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    ids = [qid for qid in order if qid in grades]
    with path.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=GRADE_FIELDS, extrasaction="ignore")
        writer.writeheader()
        for qid in ids:
            writer.writerow(grades[qid])


def normalize_evaluator(name: str) -> str:
    name = name.strip().lower().replace(" ", "_")
    return re.sub(r"[^a-z0-9_-]", "", name)


def parse_sources(value: str) -> list[dict]:
    """Convierte la celda retrieved_sources en una lista de fragmentos."""
    sources = []
    for part in (value or "").split(" || "):
        match = re.match(r"\[(\d+)\]\s*(.*)", part.strip())
        if not match:
            continue
        fields = [f.strip() for f in match.group(2).split(" | ")]
        fields += [""] * (5 - len(fields))
        sources.append({
            "n": int(match.group(1)),
            "domain": fields[0],
            "title": fields[1],
            "filename": fields[2],
            "chunk_id": fields[3],
            "url": fields[4],
        })
    return sources


@st.cache_resource
def get_collection():
    import chromadb

    if not DB_DIR.exists():
        return None
    try:
        return chromadb.PersistentClient(path=str(DB_DIR)).get_collection(COLLECTION)
    except Exception:
        return None


@st.cache_data
def get_chunks(chunk_ids: tuple[str, ...]) -> dict[str, dict]:
    collection = get_collection()
    if collection is None or not chunk_ids:
        return {}
    result = collection.get(ids=list(chunk_ids), include=["documents", "metadatas"])
    return {
        chunk_id: {"text": text, "metadata": metadata or {}}
        for chunk_id, text, metadata in zip(
            result["ids"], result["documents"], result["metadatas"]
        )
    }


# ---------------------------------------------------------------- métricas

def metrics_table(rows: list[dict], grades: dict[str, dict]) -> pd.DataFrame:
    graded = [(row, grades[row["id"]]) for row in rows if row["id"] in grades]

    def rate(field: str, value: str, exclude: str | None = None):
        values = [g[field] for _, g in graded if g.get(field) and g[field] != exclude]
        if not values:
            return None
        return round(100 * sum(v == value for v in values) / len(values), 1), len(values)

    def mean(field: str):
        values = [int(g[field]) for _, g in graded if g.get(field) in {"0", "1", "2"}]
        return round(sum(values) / len(values), 2) if values else None

    lines = []
    for label, field_base, field_rag, value in [
        ("Exactitud: % correctas (2)", "accuracy_base", "accuracy_rag", "2"),
        ("Fundamentación: % completas (2)", "grounded_base", "grounded_rag", "2"),
        ("Alucinación: % con alucinación", "hallucination_base", "hallucination_rag", "Sí"),
    ]:
        base, rag = rate(field_base, value), rate(field_rag, value)
        lines.append({
            "Métrica": label,
            "Base": f"{base[0]} % (n={base[1]})" if base else "-",
            "RAG": f"{rag[0]} % (n={rag[1]})" if rag else "-",
        })
    for label, field_base, field_rag in [
        ("Exactitud media (0-2)", "accuracy_base", "accuracy_rag"),
        ("Fundamentación media (0-2)", "grounded_base", "grounded_rag"),
    ]:
        lines.append({
            "Métrica": label,
            "Base": str(mean(field_base)) if mean(field_base) is not None else "-",
            "RAG": str(mean(field_rag)) if mean(field_rag) is not None else "-",
        })
    retrieval = rate("retrieval_relevant", "Sí", exclude="N/A")
    lines.append({
        "Métrica": "Recuperación relevante: % Sí (sin N/A)",
        "Base": "",
        "RAG": f"{retrieval[0]} % (n={retrieval[1]})" if retrieval else "-",
    })
    return pd.DataFrame(lines)


def cohen_kappa(a: list[str], b: list[str]) -> float | None:
    if not a:
        return None
    labels = sorted(set(a) | set(b))
    n = len(a)
    observed = sum(x == y for x, y in zip(a, b)) / n
    expected = sum((a.count(label) / n) * (b.count(label) / n) for label in labels)
    if expected == 1:
        return 1.0 if observed == 1 else None
    return round((observed - expected) / (1 - expected), 2)


# ---------------------------------------------------------------- interfaz

st.set_page_config(page_title="Calificación DevDocsRAG", page_icon="📝", layout="wide")
st.title("📝 Calificación de respuestas")

result_files = list_result_files()
if not result_files:
    st.error("No hay archivos results/evaluacion_*.csv. Ejecuta primero: python -m src.evaluate")
    st.stop()

with st.sidebar:
    default_file = RESULTS_DIR / "evaluacion_dev_resultados.csv"
    results_file = st.selectbox(
        "Resultados a calificar",
        result_files,
        index=result_files.index(default_file) if default_file in result_files else 0,
        format_func=lambda p: p.name,
    )
    evaluator = normalize_evaluator(st.text_input("Tu nombre (evaluador)", key="evaluator"))
    if evaluator:
        st.caption(f"Notas en `results/calificaciones/{grades_path(results_file, evaluator).name}`")
    with st.expander("Rúbrica"):
        st.markdown(RUBRIC_HELP)

rows = read_csv(results_file)
order = [row["id"] for row in rows]

tab_grade, tab_summary = st.tabs(["Calificar", "Resumen"])

def render_grading():
    if not evaluator:
        st.info("Escribe tu nombre en la barra lateral para empezar a calificar.")
        return

    path = grades_path(results_file, evaluator)
    grades = load_grades(path)

    st.progress(
        len([qid for qid in order if qid in grades]) / len(order),
        text=f"{len([q for q in order if q in grades])}/{len(order)} preguntas calificadas por {evaluator}",
    )

    if "idx" not in st.session_state or st.session_state.get("idx_file") != results_file.name:
        st.session_state.idx = 0
        st.session_state.idx_file = results_file.name

    def label_for(i: int) -> str:
        qid = order[i]
        return f"{'✅' if qid in grades else '⬜'} {qid} · {rows[i].get('category', '')}"

    nav_prev, nav_select, nav_next = st.columns([1, 6, 1])
    if nav_prev.button("◀ Anterior", disabled=st.session_state.idx == 0, width="stretch"):
        st.session_state.idx -= 1
    if nav_next.button("Siguiente ▶", disabled=st.session_state.idx == len(rows) - 1, width="stretch"):
        st.session_state.idx += 1
    st.session_state.idx = nav_select.selectbox(
        "Pregunta", range(len(rows)), index=st.session_state.idx,
        format_func=label_for, label_visibility="collapsed",
    )

    row = rows[st.session_state.idx]
    qid = row["id"]
    category = row.get("category", "")

    st.subheader(f"{qid} — {row['question']}")
    meta = [
        f"**Categoría:** {category}",
        f"**Conjunto:** {row.get('split') or '-'}",
        f"**Dominio esperado:** {row.get('domain') or '-'}",
        f"**Detectado:** {row.get('detected_domains') or '-'}",
    ]
    st.markdown(" · ".join(meta))
    if category in CATEGORY_GUIDE:
        st.info(CATEGORY_GUIDE[category])
    if row.get("execution_error"):
        st.error(f"Error de ejecución: {row['execution_error']}")

    with st.container(border=True):
        st.markdown("**Respuesta esperada**")
        st.write(row.get("expected_answer") or "-")
        st.caption(f"Fuentes esperadas: {row.get('expected_sources') or 'ninguna'}")

    col_base, col_rag = st.columns(2)
    with col_base:
        with st.container(border=True):
            st.markdown("#### Sin RAG (base)")
            st.markdown(row.get("answer_base") or "_(vacía)_")
    with col_rag:
        with st.container(border=True):
            st.markdown("#### Con RAG")
            st.markdown(row.get("answer_rag") or "_(vacía)_")

    # Fragmentos recuperados con su texto completo.
    sources = parse_sources(row.get("retrieved_sources", ""))
    cited = {int(n) for n in re.findall(r"\[(\d+)\]", row.get("answer_rag") or "")}
    expected = {s for s in (row.get("expected_sources") or "").split(";") if s}
    chunks = get_chunks(tuple(s["chunk_id"] for s in sources))

    st.markdown(f"#### Fragmentos recuperados ({len(sources)})")
    st.caption("📌 citado en la respuesta RAG · 🎯 pertenece a una fuente esperada")
    invalid_cites = sorted(n for n in cited if n not in {s["n"] for s in sources})
    if invalid_cites:
        st.warning(f"La respuesta RAG cita fragmentos que no existen: {invalid_cites}")
    if sources and get_collection() is None:
        st.warning("No se encontró el índice Chroma; no se puede mostrar el texto de los fragmentos.")

    for source in sources:
        marks = ("📌 " if source["n"] in cited else "") + ("🎯 " if source["filename"] in expected else "")
        title = f"{marks}[{source['n']}] {source['filename']} · {source['chunk_id']}"
        with st.expander(title, expanded=source["n"] in cited):
            chunk = chunks.get(source["chunk_id"])
            if chunk is None:
                st.warning("Fragmento no encontrado en el índice actual.")
            elif chunk["metadata"].get("filename") != source["filename"]:
                st.warning(
                    "El índice se reconstruyó después de esta evaluación: el fragmento "
                    f"{source['chunk_id']} ahora pertenece a {chunk['metadata'].get('filename')}. "
                    "El texto mostrado puede no ser el que vio el modelo."
                )
                st.text(chunk["text"])
            else:
                st.markdown(chunk["text"])
            st.caption(source["url"])

    # Formulario de calificación.
    st.markdown("#### Calificación")
    current = grades.get(qid, {})
    with st.form(key=f"form_{results_file.name}_{evaluator}_{qid}"):
        values = {}
        retrieval_label, retrieval_options = RUBRIC["retrieval_relevant"]
        values["retrieval_relevant"] = st.radio(
            retrieval_label, retrieval_options, horizontal=True,
            index=retrieval_options.index(current["retrieval_relevant"])
            if current.get("retrieval_relevant") in retrieval_options else None,
        )
        col_b, col_r = st.columns(2)
        for column, suffix, heading in [(col_b, "base", "Base"), (col_r, "rag", "RAG")]:
            with column:
                st.markdown(f"**{heading}**")
                for field in (f"accuracy_{suffix}", f"grounded_{suffix}", f"hallucination_{suffix}"):
                    label, options = RUBRIC[field]
                    values[field] = st.radio(
                        label, options, horizontal=True,
                        index=options.index(current[field]) if current.get(field) in options else None,
                    )
        values["notes"] = st.text_area("Notas (justifica sobre todo las notas 0 y 1)", value=current.get("notes", ""))
        submitted = st.form_submit_button("Guardar calificación", type="primary")

    if submitted:
        missing = [RUBRIC[f][0] for f in RUBRIC if values.get(f) is None]
        if missing:
            st.error("Faltan: " + ", ".join(missing))
        else:
            grades[qid] = {
                "id": qid, **values,
                "graded_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            }
            save_grades(path, grades, order)
            if st.session_state.idx < len(rows) - 1:
                st.session_state.idx += 1
            st.rerun()

def render_summary():
    graders = {
        p.stem.split("__", 1)[1]: load_grades(p)
        for p in sorted(GRADES_DIR.glob(f"{results_file.stem}__*.csv"))
    }
    if not graders:
        st.info("Todavía no hay calificaciones para este archivo de resultados.")
        return

    st.markdown("#### Métricas por evaluador")
    st.caption(
        "Las métricas que se reportan en el informe son las del evaluador "
        f"'{CONSENSUS}', registradas después de discutir las discrepancias."
    )
    for name, grades in graders.items():
        done = len([q for q in order if q in grades])
        with st.expander(f"{name} — {done}/{len(order)} calificadas", expanded=name == CONSENSUS or len(graders) == 1):
            st.dataframe(metrics_table(rows, grades), hide_index=True, width="stretch")
            categories = sorted({r.get("category", "") for r in rows if r["id"] in grades})
            if len(categories) > 1:
                st.markdown("Exactitud RAG media por categoría")
                by_cat = []
                for cat in categories:
                    vals = [int(grades[r["id"]]["accuracy_rag"]) for r in rows
                            if r.get("category") == cat and r["id"] in grades
                            and grades[r["id"]].get("accuracy_rag") in {"0", "1", "2"}]
                    by_cat.append({"Categoría": cat, "n": len(vals),
                                   "Exactitud RAG media": round(sum(vals) / len(vals), 2) if vals else None})
                st.dataframe(pd.DataFrame(by_cat), hide_index=True, width="stretch")

    independent = [name for name in graders if name != CONSENSUS]
    if len(independent) >= 2:
        st.markdown("#### Acuerdo entre evaluadores")
        pair = st.multiselect("Evaluadores a comparar", independent, default=independent[:2], max_selections=2)
        if len(pair) == 2:
            a, b = graders[pair[0]], graders[pair[1]]
            common = [q for q in order if q in a and q in b]
            st.caption(f"Preguntas calificadas por ambos: {len(common)}")
            agreement = []
            disagreements = []
            for field, (label, _) in RUBRIC.items():
                va = [a[q][field] for q in common]
                vb = [b[q][field] for q in common]
                same = sum(x == y for x, y in zip(va, vb))
                agreement.append({
                    "Criterio": label,
                    "Acuerdo": f"{round(100 * same / len(common), 1)} %" if common else "-",
                    "Kappa de Cohen": cohen_kappa(va, vb),
                })
                for q, x, y in zip(common, va, vb):
                    if x != y:
                        disagreements.append({"Pregunta": q, "Criterio": label, pair[0]: x, pair[1]: y})
            st.dataframe(pd.DataFrame(agreement), hide_index=True, width="stretch")
            st.caption("Kappa: < 0,4 acuerdo débil · 0,4–0,6 moderado · 0,6–0,8 bueno · > 0,8 muy bueno.")
            if disagreements:
                st.markdown(f"**Discrepancias a discutir ({len(disagreements)})**")
                st.dataframe(pd.DataFrame(disagreements), hide_index=True, width="stretch")
                st.caption(f"Tras discutirlas, califica con el nombre '{CONSENSUS}' para registrar las notas finales.")
            else:
                st.success("Sin discrepancias.")


with tab_grade:
    render_grading()

with tab_summary:
    render_summary()
