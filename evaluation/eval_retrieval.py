"""Evalúa solo la recuperación: ¿aparecen los documentos esperados?

Uso:
    python -m evaluation.eval_retrieval                  # conjunto dev
    python -m evaluation.eval_retrieval --split test
    python -m evaluation.eval_retrieval --details        # muestra el ranking de cada pregunta

No llama al LLM para responder (solo para la expansión bilingüe de la
consulta), así que es rápido y sirve para comparar variantes de la
recuperación. Las métricas se calculan sobre las preguntas que tienen
fuentes esperadas:

- Recall: documentos esperados recuperados / documentos esperados.
- Completas: preguntas en las que se recuperaron TODOS los documentos esperados.
- MRR: media de 1/posición del primer fragmento de un documento esperado
  (0 si no aparece ninguno).
"""
from __future__ import annotations

import argparse
import csv
from pathlib import Path

from src.config import ROOT
from src.rag import resolve_domains, retrieve

INPUT_DEFAULT = ROOT / "evaluation" / "preguntas_evaluacion_v2.csv"


def evaluate(questions: list[dict], details: bool = False) -> dict:
    total_expected = 0
    total_found = 0
    complete = 0
    reciprocal_ranks = []
    evaluated = 0

    for row in questions:
        expected = [s for s in (row.get("expected_sources") or "").split(";") if s]
        if not expected:
            continue
        evaluated += 1

        docs = retrieve(row["question"])
        filenames = [(doc.metadata or {}).get("filename", "") for doc in docs]

        found = [name for name in expected if name in filenames]
        first_hit = next(
            (pos for pos, name in enumerate(filenames, start=1) if name in expected),
            None,
        )

        total_expected += len(expected)
        total_found += len(found)
        complete += len(found) == len(expected)
        reciprocal_ranks.append(1 / first_hit if first_hit else 0.0)

        status = "OK " if len(found) == len(expected) else ("PAR" if found else "NO ")
        print(
            f"{status} {row['id']:4} esperados {len(found)}/{len(expected)} "
            f"| primera posición: {first_hit or '-'} "
            f"| dominios: {';'.join(resolve_domains(row['question']))}"
        )
        if details:
            for pos, name in enumerate(filenames, start=1):
                mark = "*" if name in expected else " "
                print(f"      {mark} {pos:2}. {name}")
            missing = [name for name in expected if name not in filenames]
            if missing:
                print(f"      faltan: {', '.join(missing)}")

    return {
        "preguntas": evaluated,
        "recall": round(total_found / total_expected, 3) if total_expected else 0.0,
        "completas": complete,
        "mrr": round(sum(reciprocal_ranks) / len(reciprocal_ranks), 3) if reciprocal_ranks else 0.0,
        "encontrados": total_found,
        "esperados": total_expected,
    }


def main():
    parser = argparse.ArgumentParser(description="Evaluación de la recuperación")
    parser.add_argument("--input", default=str(INPUT_DEFAULT))
    parser.add_argument("--split", choices=("dev", "test", "all"), default="dev")
    parser.add_argument("--details", action="store_true")
    args = parser.parse_args()

    with Path(args.input).open("r", encoding="utf-8-sig", newline="") as file:
        questions = list(csv.DictReader(file))
    if args.split != "all":
        questions = [q for q in questions if q.get("split") == args.split]

    summary = evaluate(questions, details=args.details)
    print(
        f"\n[{args.split}] preguntas con fuentes: {summary['preguntas']} | "
        f"recall: {summary['recall']} ({summary['encontrados']}/{summary['esperados']}) | "
        f"completas: {summary['completas']}/{summary['preguntas']} | "
        f"MRR: {summary['mrr']}"
    )


if __name__ == "__main__":
    main()
