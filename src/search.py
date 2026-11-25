"""Prueba la recuperación semántica y la expansión bilingüe."""
import argparse
from collections import Counter

from .rag import retrieve, get_search_query_specs, resolve_domains


def main():
    parser = argparse.ArgumentParser(
        description="Busca fragmentos en el corpus Docker + FastAPI."
    )
    parser.add_argument(
        "--domain",
        choices=("docker", "fastapi"),
        default=None,
        help="Limita la búsqueda a una tecnología. Si se omite, consulta ambas.",
    )
    parser.add_argument(
        "--k",
        type=int,
        default=None,
        help="Cantidad final de fragmentos por dominio.",
    )
    parser.add_argument(
        "--full",
        action="store_true",
        help="Muestra el texto completo de cada fragmento.",
    )
    parser.add_argument(
        "--hide-expanded-query",
        action="store_true",
        help="No muestra las consultas utilizadas para la búsqueda.",
    )
    parser.add_argument(
        "question",
        nargs="*",
        help="Pregunta en lenguaje natural.",
    )
    args = parser.parse_args()

    question = " ".join(args.question).strip()
    if not question:
        question = "¿Cómo contenerizo una API FastAPI?"

    if args.k is not None and args.k < 1:
        parser.error("--k debe ser mayor que cero.")

    domains = resolve_domains(question, args.domain)
    queries_by_domain = {
        current_domain: get_search_query_specs(question, current_domain)
        for current_domain in domains
    }
    docs = retrieve(question, k=args.k, domain=args.domain)

    print(f"\nPregunta original: {question}")
    print("Dominios consultados: " + ", ".join(domains))
    if not args.hide_expanded_query:
        print("\nConsultas utilizadas por dominio:")
        labels = {
            "original": "Original",
            "expanded": "Expansión bilingüe",
            "specific": "Consulta específica",
        }
        for current_domain, queries in queries_by_domain.items():
            print(f"  [{current_domain}]")
            for index, (query, weight, query_type) in enumerate(queries, start=1):
                label = labels.get(query_type, f"Consulta {index}")
                print(f"    {label} (peso RRF {weight:.2f}): {query}")

    if not docs:
        print("\nNo se encontraron fragmentos para esta consulta.")
        return

    counts = Counter(
        (doc.metadata or {}).get("domain", "desconocido")
        for doc in docs
    )
    print(f"\nFragmentos recuperados: {len(docs)}")
    print("Distribución por dominio: " + ", ".join(
        f"{name}={count}" for name, count in sorted(counts.items())
    ))

    for index, doc in enumerate(docs, start=1):
        metadata = doc.metadata or {}
        print(
            f"\n[{index}] {metadata.get('domain', 'sin dominio')} | "
            f"{metadata.get('filename', 'archivo no identificado')} | "
            f"{metadata.get('chunk_id', 'chunk no identificado')}"
        )
        print(f"Título: {metadata.get('title', 'Sin título')}")
        print(f"Fuente: {metadata.get('source', 'URL no disponible')}")
        content = doc.page_content or ""
        if not args.full:
            content = content[:1000] + ("..." if len(content) > 1000 else "")
        print(content.replace("\n", " "))


if __name__ == "__main__":
    main()
