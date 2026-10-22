FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
RUN python -m archi_agent index
EXPOSE 8000
CMD ["python", "-m", "uvicorn", "archi_agent.api:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]
