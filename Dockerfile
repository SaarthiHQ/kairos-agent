FROM python:3.12-slim

WORKDIR /app

COPY pyproject.toml .
COPY kairos_agent/ kairos_agent/

RUN pip install --no-cache-dir .

COPY kairos.yaml.example kairos.yaml.example

EXPOSE 8000

CMD ["kairos-agent", "--host", "0.0.0.0", "--port", "8000"]
