"""Descarga las fuentes oficiales de Docker y FastAPI del corpus v2.

Uso:
    python -m src.download_docs

Requiere conexión a Internet. Descarga todas las fuentes en memoria y solo si
todas se obtienen correctamente reemplaza los Markdown de data/documentos y
su manifest.json. Así, un fallo de red no deja un corpus a medias.

La lista de fuentes y la pregunta que respalda cada una están documentadas en
evaluation/corpus_evaluacion_v2.md.
"""
import json
import re
from datetime import datetime, timezone
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup
from markdownify import markdownify as to_markdown

from .config import DOCS_DIR


# (archivo, título, URL, dominio)
SOURCES = [
    # FastAPI
    ("fastapi_path_params", "FastAPI Path Parameters", "https://fastapi.tiangolo.com/tutorial/path-params/", "fastapi"),
    ("fastapi_query_params", "FastAPI Query Parameters", "https://fastapi.tiangolo.com/tutorial/query-params/", "fastapi"),
    ("fastapi_query_validations", "FastAPI Query Parameters and String Validations", "https://fastapi.tiangolo.com/tutorial/query-params-str-validations/", "fastapi"),
    ("fastapi_request_body", "FastAPI Request Body", "https://fastapi.tiangolo.com/tutorial/body/", "fastapi"),
    ("fastapi_response_model", "FastAPI Response Model", "https://fastapi.tiangolo.com/tutorial/response-model/", "fastapi"),
    ("fastapi_handling_errors", "FastAPI Handling Errors", "https://fastapi.tiangolo.com/tutorial/handling-errors/", "fastapi"),
    ("fastapi_dependencies", "FastAPI Dependencies", "https://fastapi.tiangolo.com/tutorial/dependencies/", "fastapi"),
    ("fastapi_cli", "FastAPI CLI", "https://fastapi.tiangolo.com/fastapi-cli/", "fastapi"),
    ("fastapi_settings", "FastAPI Settings and Environment Variables", "https://fastapi.tiangolo.com/advanced/settings/", "fastapi"),
    ("fastapi_docker", "FastAPI in Containers - Docker", "https://fastapi.tiangolo.com/deployment/docker/", "fastapi"),
    # Docker
    ("docker_what_is_container", "What is a container?", "https://docs.docker.com/learn/content/what-is-a-container/", "docker"),
    ("docker_write_dockerfile", "Write your first Dockerfile", "https://docs.docker.com/learn/content/write-your-first-dockerfile/", "docker"),
    ("docker_build_cache", "Image layers and the build cache", "https://docs.docker.com/learn/content/how-image-layers-and-the-build-cache-work/", "docker"),
    ("docker_persisting_data", "Keep data with volumes and bind mounts", "https://docs.docker.com/learn/content/keep-data-with-volumes-and-bind-mounts/", "docker"),
    ("docker_storage", "Docker storage", "https://docs.docker.com/engine/storage/", "docker"),
    ("docker_networking", "Networking overview", "https://docs.docker.com/engine/network/", "docker"),
    ("docker_bridge", "Bridge network driver", "https://docs.docker.com/engine/network/drivers/bridge/", "docker"),
    ("docker_port_publishing", "Port publishing and mapping", "https://docs.docker.com/engine/network/port-publishing/", "docker"),
    ("compose_application_model", "How Compose works", "https://docs.docker.com/compose/intro/compose-application-model/", "docker"),
    ("compose_networking", "Networking in Compose", "https://docs.docker.com/compose/how-tos/networking/", "docker"),
    ("compose_startup_order", "Control startup and shutdown order in Compose", "https://docs.docker.com/compose/how-tos/startup-order/", "docker"),
    ("compose_env_vars", "Set environment variables in Compose", "https://docs.docker.com/compose/how-tos/environment-variables/set-environment-variables/", "docker"),
    ("compose_volumes", "Define and manage volumes in Docker Compose", "https://docs.docker.com/reference/compose-file/volumes/", "docker"),
]

ALLOWED_HOSTS = {"docs.docker.com", "fastapi.tiangolo.com"}

# Elementos que no forman parte del contenido técnico.
NOISE_SELECTORS = (
    "nav, aside:not(.callout), footer, button, script, style, form, svg, "
    "astro-island, figure.video-embed, div.interactive, div.inline-sim, "
    ".feedback, .pagination, a.headerlink"
)

# Secciones de navegación o cuestionarios de Docker Learn. El cuestionario
# "Check your understanding" incluye opciones de respuesta incorrectas que
# no deben llegar al corpus.
NOISE_SECTIONS = {
    "check your understanding",
    "next",
    "keep going on your route",
    "continue with reference material",
}


def select_content(soup: BeautifulSoup):
    """Devuelve el contenedor con el contenido principal de la página."""
    return (
        soup.select_one("div.page-columns__main div.prose")  # Docker Learn
        or soup.select_one("main article")                   # FastAPI
        or soup.select_one("article")                        # Docker docs
        or soup.select_one("main")
    )


def remove_section(heading) -> None:
    """Elimina un encabezado y todo lo que hay hasta el siguiente del mismo nivel o superior."""
    level = int(heading.name[1])
    node = heading.next_sibling
    while node is not None:
        following = node.next_sibling
        name = getattr(node, "name", None)
        if name and re.fullmatch(r"h[1-6]", name) and int(name[1]) <= level:
            break
        node.extract()
        node = following
    heading.decompose()


def clean_content(content) -> None:
    """Quita del HTML los elementos que no son documentación técnica."""
    for tag in content.select(NOISE_SELECTORS):
        tag.decompose()

    # FastAPI: aviso desplegable "AI coding agents" al inicio de cada página.
    for details in content.select("details"):
        summary = details.find("summary")
        if summary and "ai coding agents" in summary.get_text().casefold():
            details.decompose()

    # Docker: los títulos envuelven su texto en un enlace a su propia ancla.
    for heading in content.find_all(re.compile(r"^h[1-6]$")):
        for link in heading.find_all("a", href=re.compile(r"^#")):
            link.unwrap()

    for heading in content.find_all(re.compile(r"^h[2-3]$")):
        if heading.get_text(" ", strip=True).casefold() in NOISE_SECTIONS:
            remove_section(heading)


def fetch_one(filename: str, title: str, url: str, domain: str) -> tuple[str, dict]:
    response = requests.get(
        url,
        timeout=40,
        headers={"User-Agent": "DockerRAG-Academic-Project/0.4"},
    )
    response.raise_for_status()

    final_url = response.url
    if urlparse(final_url).hostname not in ALLOWED_HOSTS:
        raise ValueError(f"Redirección a dominio inesperado: {final_url}")
    redirected = final_url.rstrip("/") != url.rstrip("/")

    # Se pasan los bytes para que BeautifulSoup detecte la codificación
    # (<meta charset>). response.text asume ISO-8859-1 cuando el servidor no
    # declara charset, y estropea los caracteres UTF-8 (You've -> Youâve).
    soup = BeautifulSoup(response.content, "html.parser")
    content = select_content(soup)
    if content is None:
        raise ValueError(f"No se encontró contenido principal para {url}")

    clean_content(content)

    markdown = to_markdown(
        str(content),
        heading_style="ATX",
        strip=["img"],
    ).strip()
    markdown = markdown.replace("¶", "")
    markdown = re.sub(r"[ \t]+\n", "\n", markdown)
    markdown = re.sub(r"\n{3,}", "\n\n", markdown)

    if len(markdown) < 350:
        raise ValueError(f"Contenido insuficiente en {url}: {len(markdown)} caracteres")

    text = (
        f"# {title}\n\nDominio: {domain}\n\n"
        f"Fuente: {final_url}\n\n{markdown}\n"
    )

    entry = {
        "filename": f"{filename}.md",
        "title": title,
        "domain": domain,
        "source_url": final_url,
        "requested_url": url,
        "redirected": redirected,
        "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
        "characters": len(text),
        "status": "ok",
    }
    return text, entry


def main():
    downloaded = []
    errors = []

    for filename, title, url, domain in SOURCES:
        try:
            text, entry = fetch_one(filename, title, url, domain)
            downloaded.append((text, entry))
            note = f" (redirigida a {entry['source_url']})" if entry["redirected"] else ""
            print(f"OK [{domain}]: {entry['filename']} ({entry['characters']} caracteres){note}")
        except (requests.RequestException, ValueError) as exc:
            errors.append(f"{title}: {exc}")
            print(f"ERROR [{domain}] {title}: {exc}")

    if errors:
        raise SystemExit(
            f"Fallaron {len(errors)} de {len(SOURCES)} fuentes. "
            "No se modificó data/documentos."
        )

    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    for old_file in DOCS_DIR.glob("*.md"):
        old_file.unlink()

    manifest = []
    for text, entry in downloaded:
        (DOCS_DIR / entry["filename"]).write_text(text, encoding="utf-8")
        manifest.append(entry)

    manifest_path = DOCS_DIR / "manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    by_domain = {}
    for entry in manifest:
        by_domain[entry["domain"]] = by_domain.get(entry["domain"], 0) + 1
    print(
        f"\nDescargadas {len(manifest)}/{len(SOURCES)}: "
        + ", ".join(f"{name} {count}" for name, count in sorted(by_domain.items()))
    )
    print(f"Manifiesto: {manifest_path}")


if __name__ == "__main__":
    main()
