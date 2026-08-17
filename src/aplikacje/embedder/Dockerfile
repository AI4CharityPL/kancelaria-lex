# Embedder — multilingual-e5-base, 768 wymiarów (ADR-0004).
#
# ⚠️ OBRAZ JEST CELOWO ODCIĘTY OD SIECI W CZASIE PRACY.
#    `transformers` domyślnie dociąga model, gdy nie znajdzie go lokalnie.
#    W systemie, którego jedyną obietnicą jest „akta nie opuszczają
#    urządzenia", ciche pobranie z internetu jest niedopuszczalne.
#    Zmienne poniżej wyłączają tę ścieżkę na poziomie biblioteki, a
#    `serwer.py` sprawdza obecność wag jeszcze przed jej importem.
#    Segment `net_ai` (internal: true) jest trzecią, niezależną warstwą.

FROM python:3.12-slim

# Wersje przypięte — łańcuch dostaw ma być powtarzalny (art. 21 ust. 2
# lit. d KSC). Odświeżenie wyłącznie w oknie serwisowym, z przeglądem.
ARG TORCH=2.4.1
ARG TRANSFORMERS=4.44.2

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    HF_HUB_OFFLINE=1 \
    TRANSFORMERS_OFFLINE=1 \
    HF_HUB_DISABLE_TELEMETRY=1 \
    MODEL_PATH=/modele/e5-base \
    MODEL_NAME=intfloat/multilingual-e5-base \
    PORT=8000

# Wariant CPU: embedder nie konkuruje o VRAM z modelem językowym
# (8 GB to cały budżet karty — patrz docs/12-sprzet-i-koszty.md).
# Indeks CPU zamiast domyślnego oszczędza ~2 GB obrazu na bibliotekach CUDA.
RUN pip install --no-cache-dir \
        --index-url https://download.pytorch.org/whl/cpu \
        "torch==${TORCH}" \
 && pip install --no-cache-dir \
        "transformers==${TRANSFORMERS}"

WORKDIR /aplikacja
COPY serwer.py /aplikacja/serwer.py

# Bez uprawnień administratora wewnątrz kontenera.
RUN useradd --create-home --shell /usr/sbin/nologin embedder
USER embedder

EXPOSE 8000

# Sprawdzenie żywotności NIE pobiera modelu — pyta o stan gotowości.
HEALTHCHECK --interval=30s --timeout=5s --start-period=120s --retries=3 \
    CMD python -c "import urllib.request,sys; \
        sys.exit(0 if 'gotowy' in urllib.request.urlopen('http://127.0.0.1:8000/zdrowie', timeout=3).read().decode() else 1)"

CMD ["python", "/aplikacja/serwer.py"]
