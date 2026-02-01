# syntax=docker/dockerfile:1

FROM dailyco/pipecat-base:latest

RUN apt-get update -qq \
  && apt-get install --no-install-recommends -y ffmpeg \
  && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY pipecat_cloud/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY ai_health_board ./ai_health_board
COPY pipecat_cloud/app.py ./app.py

CMD ["python", "app.py"]
