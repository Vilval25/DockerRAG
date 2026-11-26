"""Herramienta para calificar manualmente los resultados de la evaluación.

Uso:
    streamlit run grade.py

La rúbrica está definida en docs/rubrica_evaluacion.md. Cada evaluador escribe
su nombre y califica las preguntas de un CSV de resultados
(results/evaluacion_*_resultados.csv). Las notas se guardan en
results/calificaciones/<resultados>__<evaluador>.csv, sin modificar el CSV de
resultados.

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
QUESTION_BANK = RESULTS_DIR / "preguntas_evaluacion_v2.csv"
RUBRIC_DOC = ROOT / "docs" / "rubrica_evaluacion.md"
CONSENSUS = "consenso"

GROUNDING_HELP = (
    "Clasifica cada afirmación técnica: R = respaldada por el corpus; "
    "F = falsa o inventada (contradice el corpus o menciona algo inexistente); "
    "N = no está en el corpus pero es cierta.\n\n"
    "**Fundamentada**: todo lo central es R y no hay ninguna F (una abstención "
    "también es Fundamentada).\n\n"
    "**Parcial**: nada central es F, pero hay alguna F secundaria o algo central es N.\n\n"
    "**Alucinada**: alguna afirmación central es F (incluye inventar un dato, "
    "aceptar una premisa falsa o dar una implementación inventada)."
)
ACCURACY_HELP = (
    "**2**: contiene todos los elementos esenciales y ninguno es erróneo.\n\n"
    "**1**: contiene al menos uno, pero omite otro o tiene un error en alguno.\n\n"
    "**0**: ningún elemento esencial correcto (responde otra cosa, repite la "
    "pregunta, se abstiene teniendo respuesta en el corpus o lo central es erróneo).\n\n"
    "Las categorías sin_evidencia, fuera_de_corpus y premisa_falsa tienen reglas propias "
    "(ver el recuadro de la categoría)."
)
RETRIEVAL_HELP = (
    "Se juzga por el contenido de los fragmentos, no por el nombre del archivo.\n\n"
    "**Sí**: entre los fragmentos están todos los elementos esenciales.\n\n"
    "**Parcial**: están algunos, falta al menos uno.\n\n"
    "**No**: ningún fragmento contiene elementos esenciales.\n\n"
    "**N/A**: preguntas sin_evidencia y fuera_de_corpus."
)
CITATIONS_HELP = (
    "**Sí**: hay citas y cada [n] apunta a un fragmento que contiene lo afirmado.\n\n"
    "**Parcial**: al menos una cita correcta, pero otra no respalda lo afirmado o una "
    "afirmación central queda sin cita.\n\n"
    "**No**: respuesta con contenido sin citas, o ninguna cita respalda lo afirmado.\n\n"
    "**N/A**: la respuesta es una abstención (anota en notas si lleva una cita sobrante)."
)

# campo: (etiqueta, opciones, ayuda)
RUBRIC = {
    "grounding_base": ("Fundamentación base", ["Fundamentada", "Parcial", "Alucinada"], GROUNDING_HELP),
    "accuracy_base": ("Exactitud base", ["2", "1", "0"], ACCURACY_HELP),
    "grounding_rag": ("Fundamentación RAG", ["Fundamentada", "Parcial", "Alucinada"], GROUNDING_HELP),
    "accuracy_rag": ("Exactitud RAG", ["2", "1", "0"], ACCURACY_HELP),
    "retrieval_relevant": ("Recuperación relevante", ["Sí", "Parcial", "No", "N/A"], RETRIEVAL_HELP),
    "citations_rag": ("Citas correctas", ["Sí", "Parcial", "No", "N/A"], CITATIONS_HELP),
}
GRADE_FIELDS = ["id", *RUBRIC, "notes", "graded_at"]

CATEGORY_GUIDE = {
    "directa": "Exactitud según los elementos esenciales (2 = todos sin errores).",
    "aplicada": "Exactitud según los elementos esenciales (2 = todos sin errores).",
    "integrada": "Exactitud según los elementos esenciales de ambas partes. "
                 "Recuperación 'Parcial' si falta la información de una de las dos tecnologías.",
    "sin_evidencia": "Exactitud: 2 = indica que no puede saberse sin inventarlo (puede sugerir cómo "
                     "averiguarlo) · 1 = se abstiene pero añade un dato concreto como posible · "
                     "0 = da el dato como si lo supiera. Recuperación y citas: N/A.",
    "fuera_de_corpus": "Exactitud: 2 = indica que la documentación no cubre el tema y no genera contenido "
                       "técnico · 1 = lo indica pero además da pasos o código · 0 = responde sin advertirlo. "
                       "Recuperación y citas: N/A.",
    "premisa_falsa": "Exactitud: 2 = dice explícitamente que la premisa es falsa y explica lo correcto · "
                     "1 = no la acepta ni la corrige, o da lo correcto sin señalar que es falsa · "
                     "0 = acepta la premisa. Aceptar la premisa también implica fundamentación 'Alucinada'.",
}


# ---------------------------------------------------------------- datos

def list_result_files() -> list[Path]:
    return sorted(RESULTS_DIR.glob("evaluacion_*_resultados.csv"))


def read_csv(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8-sig", newline="") as file:
        return list(csv.DictReader(file))


@st.cache_data
def load_essentials() -> dict[str, list[str]]:
    if not QUESTION_BANK.exists():
        return {}
    return {
        row["id"]: [e.strip() for e in (row.get("essential_elements") or "").split(" | ") if e.strip()]
        for row in read_csv(QUESTION_BANK)
    }


def grades_path(results_file: Path, evaluator: str) -> Path:
    return GRADES_DIR / f"{results_file.stem}__{evaluator}.csv"


def load_grades(path: Path) -> dict[str, dict]:
    if not path.exists():
        return {}
    return {row["id"]: row for row in read_csv(path)}


def save_grades(path: Path, grades: dict[str, dict], order: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=GRADE_FIELDS, extrasaction="ignore")
        writer.writeheader()
        for qid in order:
            if qid in grades:
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
            "n": int(match.group(1)), "domain": fields[0], "title": fields[1],
            "filename": fields[2], "chunk_id": fields[3], "url": fields[4],
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
        for chunk_id, text, metadata in zip(result["ids"], result["documents"], result["metadatas"])
    }


# ---------------------------------------------------------------- métricas

def pct(values: list[str], targets: set[str]) -> str:
    if not values:
        return "-"
    return f"{round(100 * sum(v in targets for v in values) / len(values), 1)} % (n={len(values)})"


def mean_score(values: list[str]) -> str:
    nums = [int(v) for v in values if v in {"0", "1", "2"}]
    return str(round(sum(nums) / len(nums), 2)) if nums else "-"


def metrics_table(rows: list[dict], grades: dict[str, dict]) -> pd.DataFrame:
    graded = [grades[r["id"]] for r in rows if r["id"] in grades]

    def col(field, exclude_na=False):
        return [g.get(field, "") for g in graded if g.get(field) and not (exclude_na and g[field] == "N/A")]

    lines = [
        {"Métrica": "Fundamentada (%)", "Base": pct(col("grounding_base"), {"Fundamentada"}),
         "RAG": pct(col("grounding_rag"), {"Fundamentada"})},
        {"Métrica": "Alucinación estricta: Alucinada (%)", "Base": pct(col("grounding_base"), {"Alucinada"}),
         "RAG": pct(col("grounding_rag"), {"Alucinada"})},
        {"Métrica": "Alucinación amplia: Alucinada + Parcial (%)",
         "Base": pct(col("grounding_base"), {"Alucinada", "Parcial"}),
         "RAG": pct(col("grounding_rag"), {"Alucinada", "Parcial"})},
        {"Métrica": "Exactitud: correctas (2) (%)", "Base": pct(col("accuracy_base"), {"2"}),
         "RAG": pct(col("accuracy_rag"), {"2"})},
        {"Métrica": "Exactitud media (0-2)", "Base": mean_score(col("accuracy_base")),
         "RAG": mean_score(col("accuracy_rag"))},
        {"Métrica": "Recuperación relevante: Sí (%, sin N/A)", "Base": "",
         "RAG": pct(col("retrieval_relevant", exclude_na=True), {"Sí"})},
        {"Métrica": "Citas correctas: Sí (%, sin N/A)", "Base": "",
         "RAG": pct(col("citations_rag", exclude_na=True), {"Sí"})},
    ]
    return pd.DataFrame(lines)


def failure_table(rows: list[dict], grades: dict[str, dict]) -> pd.DataFrame:
    """Clasifica las respuestas RAG con exactitud 0-1 según la recuperación."""
    counts = {"Fallo del modelo (recuperación Sí)": [], "Fallo de búsqueda (recuperación Parcial/No)": []}
    for row in rows:
        grade = grades.get(row["id"])
        if not grade or grade.get("accuracy_rag") not in {"0", "1"}:
            continue
        if grade.get("retrieval_relevant") == "Sí":
            counts["Fallo del modelo (recuperación Sí)"].append(row["id"])
        elif grade.get("retrieval_relevant") in {"Parcial", "No"}:
            counts["Fallo de búsqueda (recuperación Parcial/No)"].append(row["id"])
    return pd.DataFrame([
        {"Tipo de fallo (exactitud RAG 0-1)": k, "n": len(v), "Preguntas": ", ".join(v)}
        for k, v in counts.items()
    ])


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
    st.error("No hay archivos results/evaluacion_*_resultados.csv. Ejecuta primero: python -m src.evaluate")
    st.stop()

with st.sidebar:
    default_file = RESULTS_DIR / "evaluacion_dev_resultados.csv"
    results_file = st.selectbox(
        "Resultados a calificar", result_files,
        index=result_files.index(default_file) if default_file in result_files else 0,
        format_func=lambda p: p.name,
    )
    evaluator = normalize_evaluator(st.text_input("Tu nombre (evaluador)", key="evaluator"))
    if evaluator:
        st.caption(f"Notas en `results/calificaciones/{grades_path(results_file, evaluator).name}`")
    with st.expander("Rúbrica completa"):
        if RUBRIC_DOC.exists():
            st.markdown(RUBRIC_DOC.read_text(encoding="utf-8"))
        else:
            st.warning("No se encontró docs/rubrica_evaluacion.md")

rows = read_csv(results_file)
order = [row["id"] for row in rows]
essentials = load_essentials()

tab_grade, tab_summary = st.tabs(["Calificar", "Resumen"])


def render_grading():
    if not evaluator:
        st.info("Escribe tu nombre en la barra lateral para empezar a calificar.")
        return

    path = grades_path(results_file, evaluator)
    grades = load_grades(path)
    done = len([q for q in order if q in grades])
    st.progress(done / len(order), text=f"{done}/{len(order)} preguntas calificadas por {evaluator}")

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
    st.markdown(" · ".join([
        f"**Categoría:** {category}",
        f"**Conjunto:** {row.get('split') or '-'}",
        f"**Dominio esperado:** {row.get('domain') or '-'}",
        f"**Detectado:** {row.get('detected_domains') or '-'}",
    ]))
    if category in CATEGORY_GUIDE:
        st.info(CATEGORY_GUIDE[category])
    if row.get("execution_error"):
        st.error(f"Error de ejecución: {row['execution_error']}")

    with st.container(border=True):
        st.markdown("**Respuesta esperada**")
        st.write(row.get("expected_answer") or "-")
        items = essentials.get(qid, [])
        if items:
            st.markdown("**Elementos esenciales** (márcalos mientras lees; no se guardan)")
            check_base, check_rag = st.columns(2)
            check_base.caption("Presentes en la respuesta base")
            check_rag.caption("Presentes en la respuesta RAG")
            for i, item in enumerate(items, start=1):
                check_base.checkbox(f"{i}. {item}", key=f"eb_{results_file.name}_{qid}_{i}")
                check_rag.checkbox(f"{i}. {item}", key=f"er_{results_file.name}_{qid}_{i}")
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
        with st.expander(f"{marks}[{source['n']}] {source['filename']} · {source['chunk_id']}",
                         expanded=source["n"] in cited):
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

    st.markdown("#### Calificación")
    st.caption("Pasa el cursor sobre el ❔ de cada criterio para ver la definición de cada valor.")
    current = grades.get(qid, {})

    def radio(field):
        label, options, help_text = RUBRIC[field]
        return st.radio(
            label, options, horizontal=True, help=help_text,
            index=options.index(current[field]) if current.get(field) in options else None,
        )

    with st.form(key=f"form_{results_file.name}_{evaluator}_{qid}"):
        values = {}
        col_b, col_r = st.columns(2)
        with col_b:
            st.markdown("**Base** (comparación)")
            values["grounding_base"] = radio("grounding_base")
            values["accuracy_base"] = radio("accuracy_base")
        with col_r:
            st.markdown("**RAG** (comparación)")
            values["grounding_rag"] = radio("grounding_rag")
            values["accuracy_rag"] = radio("accuracy_rag")
        st.markdown("**RAG** (diagnóstico)")
        col_d1, col_d2 = st.columns(2)
        with col_d1:
            values["retrieval_relevant"] = radio("retrieval_relevant")
        with col_d2:
            values["citations_rag"] = radio("citations_rag")
        values["notes"] = st.text_area(
            "Notas (justifica todo valor distinto de Fundamentada / 2 / Sí)",
            value=current.get("notes", ""),
        )
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
    graders = {name: g for name, g in graders.items() if any("grounding_rag" in r for r in g.values())}
    if not graders:
        st.info("Todavía no hay calificaciones (con la rúbrica actual) para este archivo de resultados.")
        return

    st.markdown("#### Métricas por evaluador")
    st.caption(
        "Las métricas que se reportan en el informe son las del evaluador "
        f"'{CONSENSUS}', registradas después de discutir las discrepancias."
    )
    for name, grades in graders.items():
        done = len([q for q in order if q in grades])
        with st.expander(f"{name} — {done}/{len(order)} calificadas",
                         expanded=name == CONSENSUS or len(graders) == 1):
            st.dataframe(metrics_table(rows, grades), hide_index=True, width="stretch")
            st.dataframe(failure_table(rows, grades), hide_index=True, width="stretch")
            categories = sorted({r.get("category", "") for r in rows if r["id"] in grades})
            if len(categories) > 1:
                by_cat = []
                for cat in categories:
                    subset = [r for r in rows if r.get("category") == cat]
                    sub = {r["id"]: grades[r["id"]] for r in subset if r["id"] in grades}
                    by_cat.append({
                        "Categoría": cat, "n": len(sub),
                        "Exactitud media base": mean_score([g["accuracy_base"] for g in sub.values()]),
                        "Exactitud media RAG": mean_score([g["accuracy_rag"] for g in sub.values()]),
                        "Alucinada base": pct([g["grounding_base"] for g in sub.values()], {"Alucinada"}),
                        "Alucinada RAG": pct([g["grounding_rag"] for g in sub.values()], {"Alucinada"}),
                    })
                st.dataframe(pd.DataFrame(by_cat), hide_index=True, width="stretch")

    independent = [name for name in graders if name != CONSENSUS]
    if len(independent) >= 2:
        st.markdown("#### Acuerdo entre evaluadores")
        pair = st.multiselect("Evaluadores a comparar", independent, default=independent[:2], max_selections=2)
        if len(pair) == 2:
            a, b = graders[pair[0]], graders[pair[1]]
            common = [q for q in order if q in a and q in b]
            st.caption(f"Preguntas calificadas por ambos: {len(common)}")
            agreement, disagreements = [], []
            for field, (label, _, _) in RUBRIC.items():
                va = [a[q].get(field, "") for q in common]
                vb = [b[q].get(field, "") for q in common]
                same = sum(x == y for x, y in zip(va, vb))
                agreement.append({
                    "Criterio": label,
                    "Acuerdo": f"{round(100 * same / len(common), 1)} %" if common else "-",
                    "Kappa de Cohen": cohen_kappa(va, vb),
                })
                disagreements += [
                    {"Pregunta": q, "Criterio": label, pair[0]: x, pair[1]: y}
                    for q, x, y in zip(common, va, vb) if x != y
                ]
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
