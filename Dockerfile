# Optional. Only used if you pick the Docker route on Render, where the
# platform builds everything itself and you never run npm locally.
#
# The application does not need Docker to run — the spec ruled it out of the
# stack, and nothing in backend/ or frontend/ knows this file exists. Delete
# it if you build the frontend yourself.
#
#   docker build -t nav . && docker run -p 8000:8000 nav

# --- stage 1: build the static frontend ------------------------------------
FROM node:20-slim AS web

WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# --- stage 2: the Python service, serving the API and that build -----------
FROM python:3.12-slim

WORKDIR /app/backend
COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/ ./

# app/main.py mounts this automatically when index.html is present.
COPY --from=web /app/frontend/out /app/frontend/out

ENV PYTHONUNBUFFERED=1 \
    DATABASE_URL=sqlite:////tmp/nav.db \
    WEATHER_PROVIDER=mock \
    PORT=8000

EXPOSE 8000

# Seeding is a no-op once the database holds a fleet.
CMD python seed.py --if-empty && uvicorn app.main:app --host 0.0.0.0 --port ${PORT}
