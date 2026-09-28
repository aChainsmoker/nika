FROM python:3.11-slim

WORKDIR /app
COPY app.py .

ENV WIT_TOKEN=""
ENV WIT_URL="https://api.wit.ai/message"
ENV FORCED_INTENT="about_entity"
ENV LISTEN_PORT="8091"

EXPOSE 8091

ENTRYPOINT ["python3", "app.py"]
