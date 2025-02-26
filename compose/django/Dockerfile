FROM python:3.11-slim-buster
ENV PYTHONUNBUFFERED 1
ENV PYTHONDONTWRITEBYTECODE 1

# Install build tools and utilities
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        make \
        gettext \
    && rm -rf /var/lib/apt/lists/*

# Requirements are installed here to ensure they will be cached.
COPY ./requirements.txt /requirements.txt
RUN pip install -r /requirements.txt

COPY ./compose/django/entrypoint /entrypoint
RUN sed -i 's/\r$//g' /entrypoint
RUN chmod +x /entrypoint

COPY ./compose/django/start /start
RUN sed -i 's/\r$//g' /start
RUN chmod +x /start

WORKDIR /app
COPY . /app

# Create logs directory and set permissions
RUN mkdir -p /app/logs && \
    touch /app/logs/critical.log /app/logs/error.log /app/logs/info.log /app/logs/warning.log && \
    chmod -R 777 /app/logs

# Create media directories and set permissions
RUN mkdir -p /app/media/uploads/ckeditor /app/media/about && \
    chmod -R 777 /app/media

ENTRYPOINT ["/entrypoint"]
