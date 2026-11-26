"""Este repo es publico: no puede llevar direcciones de red ni correos.

La comprobacion completa (nombres de repos privados, clientes e IPs del manifiesto real) la hace
la revision nocturna desde el repo de datos, porque esa lista no puede vivir aqui.
"""
import re
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
IGNORAR = {".git", "node_modules", "dist", ".venv", "__pycache__", ".pytest_cache"}
TEXTO = {".md", ".py", ".ts", ".tsx", ".json", ".yml", ".yaml", ".toml", ".txt", ".html", ".css", ".sh", ".ejemplo"}
IPV4 = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")
CORREO = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
PERMITIDAS = {"127.0.0.1", "0.0.0.0"}
CORREOS_PERMITIDOS = {"noreply@anthropic.com"}


def _archivos():
    for ruta in RAIZ.rglob("*"):
        if ruta.is_file() and not IGNORAR & set(ruta.relative_to(RAIZ).parts) and (ruta.suffix in TEXTO or ruta.name == "Dockerfile"):
            if ruta.name == "package-lock.json":
                continue
            yield ruta


def test_sin_ips_ni_correos():
    hallazgos = []
    for ruta in _archivos():
        texto = ruta.read_text(encoding="utf-8")
        for ip in set(IPV4.findall(texto)) - PERMITIDAS:
            # Versiones como 1.2.3.4 en dependencias tambien casan; aqui no hay ninguna legitima.
            hallazgos.append(f"{ruta.relative_to(RAIZ)}: {ip}")
        for correo in set(CORREO.findall(texto)) - CORREOS_PERMITIDOS:
            hallazgos.append(f"{ruta.relative_to(RAIZ)}: {correo}")
    assert hallazgos == []
