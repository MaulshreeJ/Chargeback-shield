# Chargeback Shield — Razorpay AI Buildathon 2026, Track 02
#
# The model and reports are trained/generated at BUILD time (not on first
# request), so the container starts up instantly and deterministically.
# RiskModel.__init__ has its own in-memory self-healing retrain fallback
# (src/model.py) if the baked artifact is ever missing or incompatible,
# but baking it here is what makes startup fast and build-time-verifiable:
# if synthetic data generation or training ever breaks, `docker build`
# fails loudly instead of the API failing silently on first score.

FROM python:3.10-slim

WORKDIR /app

# Install dependencies first so this layer is cached across code-only changes.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Now the application code.
COPY src ./src
COPY scripts ./scripts
COPY tests ./tests
COPY conftest.py pytest.ini ./

# Train the model and evaluate the evidence-packet engine at build time.
# All data is synthetic (src/data_gen.py) -- nothing external or secret is
# needed for this step. Writes reports/model.joblib, metrics.json,
# model_card.md, feature_baselines.json, thresholds.json,
# merchant_rollup.json, and packet_metrics.json into the image.
# Set LOKY_MAX_CPU_COUNT=1 to prevent joblib/loky CPU core auto-detection
# failures in sandboxed container build environments (e.g. Render).
ENV LOKY_MAX_CPU_COUNT=1
RUN python -m scripts.train && python -m scripts.evaluate_packets && python -m scripts.merchant_rollup

# Never bake secrets into the image -- the optional Gemini narrative layer
# reads GEMINI_API_KEY from the environment at runtime (see .env.example),
# not from anything copied in here. .dockerignore also excludes .env.
ENV PYTHONUNBUFFERED=1
# Most hosting platforms (Render, Railway, Fly, etc.) assign a random port
# at runtime via $PORT and route traffic to it -- 8000 is only the local
# default (docker run -p 8000:8000 ... still works, since uvicorn falls
# back to 8000 when $PORT is unset).
ENV PORT=8000
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import os, urllib.request; port = os.environ.get('PORT', '8000'); urllib.request.urlopen('http://127.0.0.1:' + port + '/health', timeout=3)" || exit 1

CMD uvicorn src.api:app --host 0.0.0.0 --port ${PORT:-8000}
