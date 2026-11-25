"""Descarga las 13 fuentes oficiales de Docker y FastAPI.

Uso:
    python -m src.download_docs

Requiere conexión a Internet. La ejecución actualiza data/documentos/manifest.json.
"""
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup
from markdownify import markdownify as to_markdown

from .config import DOCS_DIR


SOURCES = [
    # Docker
    ("01_docker_overview", "Docker overview", "https://docs.docker.com/get-started/docker-overview/", "docker"),
    ("02_dockerfile", "Writing a Dockerfile", "https://docs.docker.com/get-started/docker-concepts/building-images/writing-a-dockerfile/", "docker"),
    ("03_networking", "Networking overview", "https://docs.docker.com/engine/network/", "docker"),
    ("04_volumes", "Volumes", "https://docs.docker.com/engine/storage/volumes/", "docker"),
    ("05_compose_concepts", "Compose application model", "https://docs.docker.com/compose/intro/compose-application-model/", "docker"),
    ("06_compose_quickstart", "Compose Quickstart", "https://docs.docker.com/compose/gettingstarted/", "docker"),
    ("13_docker_port_publishing", "Port publishing and mapping", "https://docs.docker.com/engine/network/port-publishing/", "docker"),
    # FastAPI
    ("07_fastapi_first_steps", "FastAPI First Steps", "https://fastapi.tiangolo.com/tutorial/first-steps/", "fastapi"),
    ("08_fastapi_path_params", "FastAPI Path Parameters", "https://fastapi.tiangolo.com/tutorial/path-params/", "fastapi"),
    ("09_fastapi_query_params", "FastAPI Query Parameters", "https://fastapi.tiangolo.com/tutorial/query-params/", "fastapi"),
    ("10_fastapi_request_body", "FastAPI Request Body", "https://fastapi.tiangolo.com/tutorial/body/", "fastapi"),
    ("11_fastapi_dependencies", "FastAPI Dependencies", "https://fastapi.tiangolo.com/tutorial/dependencies/", "fastapi"),
    ("12_fastapi_docker", "FastAPI in Containers - Docker", "https://fastapi.tiangolo.com/deployment/docker/", "fastapi"),
]

ALLOWED_HOSTS = {"docs.docker.com", "fastapi.tiangolo.com"}


def fetch_one(filename: str, title: str, url: str, domain: str) -> dict:
    response = requests.get(
        url,
        timeout=40,
        headers={"User-Agent": "DockerRAG-Academic-Project/0.3"},
    )
    response.raise_for_status()

    hostname = urlparse(response.url).hostname
    if hostname not in ALLOWED_HOSTS:
        raise ValueError(f"Redirección a dominio inesperado: {response.url}")

    soup = BeautifulSoup(response.text, "html.parser")
    main = (
        soup.select_one("main article")
        or soup.select_one("article")
        or soup.select_one("main")
    )
    if main is None:
        raise ValueError(f"No se encontró contenido principal para {url}")

    for tag in main.select(
        "nav, aside, footer, button, script, style, form, "
        ".feedback, .pagination"
    ):
        tag.decompose()

    content = to_markdown(
        str(main),
        heading_style="ATX",
        strip=["img", "svg"],
    ).strip()
    content = re.sub(r"\n{3,}", "\n\n", content)

    if len(content) < 350:
        raise ValueError(
            f"Contenido insuficiente en {url}: {len(content)} caracteres"
        )

    content = (
        f"# {title}\n\nDominio: {domain}\n\n"
        f"Fuente: {response.url}\n\n{content}\n"
    )

    output = DOCS_DIR / f"{filename}.md"
    output.write_text(content, encoding="utf-8")

    return {
        "filename": output.name,
        "title": title,
        "domain": domain,
        "source_url": response.url,
        "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
        "characters": len(content),
        "status": "ok",
    }


def main():
    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    manifest = []

    for filename, title, url, domain in SOURCES:
        try:
            item = fetch_one(filename, title, url, domain)
            manifest.append(item)
            print(
                f"OK [{domain}]: {item['filename']} "
                f"({item['characters']} caracteres)"
            )
        except (requests.RequestException, ValueError) as exc:
            manifest.append(
                {
                    "filename": f"{filename}.md",
                    "title": title,
                    "domain": domain,
                    "source_url": url,
                    "status": "error",
                    "error": str(exc),
                }
            )
            print(f"ERROR [{domain}] {title}: {exc}")

    manifest_path = DOCS_DIR / "manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    ok = sum(item["status"] == "ok" for item in manifest)
    docker_ok = sum(
        item["status"] == "ok" and item.get("domain") == "docker"
        for item in manifest
    )
    fastapi_ok = sum(
        item["status"] == "ok" and item.get("domain") == "fastapi"
        for item in manifest
    )

    print(
        f"Descargados {ok}/{len(SOURCES)}: "
        f"Docker {docker_ok}/7; FastAPI {fastapi_ok}/6"
    )
    print(f"Manifiesto: {manifest_path}")

    if ok != len(SOURCES):
        raise SystemExit(
            "Corpus incompleto. Revisa manifest.json y vuelve a ejecutar "
            "la descarga."
        )


if __name__ == "__main__":
    main()
