ARG PYTHON_IMAGE=python:3.12-slim
FROM ${PYTHON_IMAGE}
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 LISTEN_HOST=0.0.0.0
WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY cloud.py host_service.py relay.py pcm.py transport.py session_policy.py screen_text.py healthcheck.py ./
COPY LICENSE THIRD_PARTY_NOTICES.md ./
COPY licenses/ ./licenses/
USER 10001:10001
EXPOSE 18878
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 CMD ["python", "healthcheck.py"]
CMD ["python", "host_service.py"]
