# Visa Doctors

Backend service for Visa Doctors platform.

## Technology Stack

- Python 3.11
- Django 5.0.2
- Django REST Framework 3.14.0
- PostgreSQL 17.4
- Docker & Docker Compose

## Features

- REST API with Swagger documentation
- Admin panel with Jazzmin theme
- Multi-language support
- Error tracking with Sentry
- CORS support for frontend integration
- Debug toolbar for development
- Secure configuration for production

## Local Development

1. Clone the repository
2. Create `.env` file based on provided example
3. Run with Docker:
```bash
docker compose up --build
```

Or run locally:
```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

## API Documentation

- Swagger UI: `/api/schema/swagger-ui/`
- ReDoc: `/api/schema/redoc/`

## Environment Variables

See `.env.example` for all required environment variables.

## Security

- HTTPS enforced in production
- CORS configuration
- XSS protection
- HSTS enabled
- Content security headers

## Contributing

1. Create feature branch
2. Make changes
3. Run tests
4. Create pull request

## License

Private. All rights reserved.
