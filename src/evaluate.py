"""Ejecuta el banco de preguntas con el LLM base y con RAG.

Uso:
    python -m src.evaluate                      # preguntas dev (por defecto)
    python -m src.evaluate --split test         # preguntas de prueba, solo al final
    python -m src.evaluate --split dev --limit 3 --output results/piloto.csv
    python -m src.evaluate --input results/preguntas_evaluacion.csv --split all

Las mejoras del sistema se ajustan solo con el conjunto dev. El conjunto test
se ejecuta al final para comprobar si la mejora se mantiene con preguntas
que no se usaron para ajustar el sistema.

El dominio NO se toma del CSV: el sistema lo detecta a partir de la
pregunta, como haría con un usuario real. La columna domain del banco se
conserva como referencia para comparar con detected_domains.

El script NO asigna calificaciones automáticas. Guarda ambas respuestas y
las fuentes recuperadas para que el equipo complete la rúbrica manualmente.
"""
from __future__ import annotations

import argparse
import csv
from pathlib import Path

from .config import ROOT
from .rag import answer, resolve_domains

INPUT_DEFAULT = ROOT / "results" / "preguntas_evaluacion_v2.csv"
SPLITS = ("dev", "test", "all")

QUESTION_FIELDS = [
    "id", "split", "domain", "category", "question",
    "expected_answer", "expected_sources",
]

OUTPUT_FIELDS = QUESTION_FIELDS + [
    "detected_domains", "answer_base", "answer_rag",
    "retrieved_sources", "retrieved_domains",
    "retrieval_relevant", "accuracy_base", "accuracy_rag",
    "grounded_base", "grounded_rag",
    "hallucination_base", "hallucination_rag", "notes",
    "execution_error",
]

RUBRIC_FIELDS = [
    "retrieval_relevant", "accuracy_base", "accuracy_rag",
    "grounded_base", "grounded_rag",
    "hallucination_base", "hallucination_rag", "notes",
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


def load_questions(input_path: Path, split: str) -> list[dict]:
    """Lee el banco de preguntas y filtra por conjunto."""
    if not input_path.exists():
        raise SystemExit(f"No se encontró el banco de preguntas: {input_path}")

    with input_path.open("r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)
        questions = list(reader)
        has_split = "split" in (reader.fieldnames or [])

    if split == "all":
        return questions

    if not has_split:
        raise SystemExit(
            f"{input_path.name} no tiene columna 'split'. "
            "Usa --split all para ejecutar todas sus preguntas."
        )

    return [
        row for row in questions
        if (row.get("split") or "").strip().lower() == split
    ]


def run():
    parser = argparse.ArgumentParser(description="Evaluación experimental de DockerRAG")
    parser.add_argument("--input", default=str(INPUT_DEFAULT), help="CSV con las preguntas")
    parser.add_argument(
        "--split",
        choices=SPLITS,
        default="dev",
        help="Conjunto a ejecutar: dev (por defecto), test o all.",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="CSV de resultados (por defecto results/evaluacion_<split>_resultados.csv)",
    )
    parser.add_argument("--limit", type=int, default=0, help="Ejecuta solo las primeras N preguntas (0 = todas)")
    args = parser.parse_args()

    input_path = Path(args.input)
    output_path = Path(
        args.output
        or ROOT / "results" / f"evaluacion_{args.split}_resultados.csv"
    )

    questions = load_questions(input_path, args.split)

    if args.limit > 0:
        questions = questions[:args.limit]

    if not questions:
        raise SystemExit(f"No hay preguntas para el conjunto '{args.split}'.")

    print(f"Banco: {input_path.name} | conjunto: {args.split} | preguntas: {len(questions)}")

    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=OUTPUT_FIELDS)
        writer.writeheader()
        file.flush()

        for index, question_row in enumerate(questions, start=1):
            qid = question_row["id"]
            question = question_row["question"]

            print(f"\n[{index}/{len(questions)}] {qid} — {question}")
            result_row = {field: question_row.get(field, "") for field in QUESTION_FIELDS}
            result_row.update({
                field: ""
                for field in OUTPUT_FIELDS
                if field not in QUESTION_FIELDS
            })

            try:
                # Mismo dominio que usará la recuperación: detección automática.
                result_row["detected_domains"] = ";".join(resolve_domains(question))

                base_result = answer(question, use_rag=False)
                rag_result = answer(question, use_rag=True)

                result_row["answer_base"] = str(base_result["answer"])
                result_row["answer_rag"] = str(rag_result["answer"])
                result_row["retrieved_sources"] = format_sources(rag_result["sources"])
                result_row["retrieved_domains"] = ";".join(
                    sorted({source["domain"] for source in rag_result["sources"]})
                )
                print(
                    f"  OK. Dominio esperado: {result_row['domain'] or '-'} | "
                    f"detectado: {result_row['detected_domains']} | "
                    f"fuentes: {result_row['retrieved_domains'] or 'ninguna'}"
                )
            except Exception as exc:
                result_row["execution_error"] = f"{type(exc).__name__}: {exc}"
                print(f"  ERROR: {result_row['execution_error']}")

            writer.writerow(result_row)
            file.flush()

    print(f"\nEvaluación terminada. Resultados guardados en: {output_path}")
    print("Completa manualmente: " + ", ".join(RUBRIC_FIELDS) + ".")


if __name__ == "__main__":
    run()
