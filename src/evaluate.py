"""Ejecuta el banco de preguntas con el LLM base y con RAG.

Uso:
    python -m src.evaluate --limit 2
    python -m src.evaluate
    python -m src.evaluate --output results/piloto.csv

El script NO asigna calificaciones automáticas. Guarda ambas respuestas y
las fuentes recuperadas para que el equipo complete la rúbrica manualmente.
"""
from __future__ import annotations

import argparse
import csv
from pathlib import Path

from .config import ROOT
from .rag import answer

INPUT_DEFAULT = ROOT / "results" / "preguntas_evaluacion.csv"
OUTPUT_DEFAULT = ROOT / "results" / "evaluacion_resultados.csv"

OUTPUT_FIELDS = [
    "id", "domain", "category", "question", "expected_answer",
    "expected_sources", "answer_base", "answer_rag",
    "retrieved_sources", "retrieved_domains",
    "retrieval_relevant", "accuracy_base", "accuracy_rag",
    "grounded_base", "grounded_rag",
    "hallucination_base", "hallucination_rag", "notes",
    "execution_error",
]


def format_sources(sources: list[dict]) -> str:
    """Serializa las fuentes recuperadas en una sola celda CSV."""
    parts = []
    for source in sources:
        parts.append(
            f"[{source.get('id')}] {source.get('domain')} | "
            f"{source.get('title')} | {source.get('filename', 'sin_filename')} | "
            f"{source.get('chunk_id')} | {source.get('url')}"
        )
    return " || ".join(parts)


def run():
    parser = argparse.ArgumentParser(description="Evaluación experimental de DockerRAG")
    parser.add_argument("--input", default=str(INPUT_DEFAULT), help="CSV con las preguntas")
    parser.add_argument("--output", default=str(OUTPUT_DEFAULT), help="CSV donde guardar resultados")
    parser.add_argument("--limit", type=int, default=0, help="Ejecuta solo las primeras N preguntas (0 = todas)")
    args = parser.parse_args()

    input_path = Path(args.input)
    output_path = Path(args.output)

    if not input_path.exists():
        raise SystemExit(f"No se encontró el banco de preguntas: {input_path}")

    with input_path.open("r", encoding="utf-8-sig", newline="") as file:
        questions = list(csv.DictReader(file))

    if args.limit > 0:
        questions = questions[:args.limit]

    if not questions:
        raise SystemExit("El banco de preguntas está vacío.")

    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=OUTPUT_FIELDS)
        writer.writeheader()
        file.flush()

        for index, question_row in enumerate(questions, start=1):
            qid = question_row["id"]
            domain_value = (question_row.get("domain") or "").strip().lower()
            # Para preguntas integradas se consulta en ambos dominios.
            domain_filter = domain_value if domain_value in {"docker", "fastapi"} else None

            print(f"\n[{index}/{len(questions)}] {qid} — {question_row['question']}")
            result_row = {
                field: question_row.get(field, "")
                for field in [
                    "id", "domain", "category", "question",
                    "expected_answer", "expected_sources"
                ]
            }
            result_row.update({
                "answer_base": "",
                "answer_rag": "",
                "retrieved_sources": "",
                "retrieved_domains": "",
                "retrieval_relevant": "",
                "accuracy_base": "",
                "accuracy_rag": "",
                "grounded_base": "",
                "grounded_rag": "",
                "hallucination_base": "",
                "hallucination_rag": "",
                "notes": "",
                "execution_error": "",
            })

            try:
                base_result = answer(
                    question_row["question"],
                    use_rag=False,
                    domain=domain_filter,
                )
                rag_result = answer(
                    question_row["question"],
                    use_rag=True,
                    domain=domain_filter,
                )

                result_row["answer_base"] = str(base_result["answer"])
                result_row["answer_rag"] = str(rag_result["answer"])
                result_row["retrieved_sources"] = format_sources(rag_result["sources"])
                result_row["retrieved_domains"] = ";".join(
                    sorted({source["domain"] for source in rag_result["sources"]})
                )
                print("  OK: respuestas base y RAG guardadas.")
                print(f"  Fuentes recuperadas: {result_row['retrieved_domains'] or 'ninguna'}")
            except Exception as exc:
                result_row["execution_error"] = f"{type(exc).__name__}: {exc}"
                print(f"  ERROR: {result_row['execution_error']}")

            writer.writerow(result_row)
            file.flush()

    print(f"\nEvaluación terminada. Resultados guardados en: {output_path}")
    print("Completa manualmente las columnas de relevancia, exactitud, fundamentación y alucinación.")


if __name__ == "__main__":
    run()
