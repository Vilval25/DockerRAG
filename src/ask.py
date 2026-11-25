"""Consulta DockerRAG desde terminal.

Ejemplos:
  python -m src.ask "¿Qué es un volumen Docker?"
  python -m src.ask --base "¿Qué es FastAPI?"
  python -m src.ask --domain fastapi "¿Cómo funcionan las dependencias?"
  python -m src.ask --domain docker "¿Cómo se publican puertos?"
  python -m src.ask "¿Cómo desplegar una API FastAPI con Docker Compose?"

Si no se especifica --domain, rag.py intenta detectar la tecnología a partir
de la pregunta. Si la pregunta es integrada o ambigua, consulta ambos dominios.
"""
import sys
from .rag import answer


def main():
    args = sys.argv[1:]

    base = "--base" in args
    args = [arg for arg in args if arg != "--base"]

    domain = None
    if "--domain" in args:
        index = args.index("--domain")
        if index + 1 >= len(args):
            raise SystemExit(
                "Uso: --domain docker o --domain fastapi"
            )

        domain = args[index + 1].lower()
        if domain not in {"docker", "fastapi"}:
            raise SystemExit(
                "Dominio inválido. Usa docker o fastapi."
            )
        del args[index:index + 2]

    question = " ".join(args).strip()
    if not question:
        question = "¿Cómo desplegar una API FastAPI con Docker?"

    result = answer(question, use_rag=not base, domain=domain)

    print("\nRESPUESTA:\n" + str(result["answer"]))

    sources = result.get("sources", [])
    if sources:
        print("\nFUENTES RECUPERADAS:")
        for source in sources:
            print(
                f"[{source['id']}] [{source['domain']}] "
                f"{source['title']} | "
                f"{source.get('filename', 'archivo no identificado')} | "
                f"{source.get('chunk_id', 'chunk no identificado')} | "
                f"{source['url']}"
            )
    elif not base:
        print("\nNo se recuperaron fuentes documentales.")


if __name__ == "__main__":
    main()
