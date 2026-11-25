FROM python:3.12-slim
WORKDIR /srv
COPY servicio.py .
RUN useradd --create-home --uid 10001 app
USER app
EXPOSE 8000
HEALTHCHECK --interval=5s --timeout=3s --retries=10 CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://localhost:8000/health', timeout=2).status == 200 else 1)"
CMD ["python", "servicio.py"]
