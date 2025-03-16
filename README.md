# JWT Authentication System

A Django REST Framework + Vue.js application featuring JWT authentication using HTTP-only cookies.

## Features

- JWT authentication with refresh tokens via HTTP-only cookies
- No access tokens, just refresh tokens for enhanced security
- Custom DRF authentication class and middleware
- Standard API response format with status, success, detail, and result fields
- Swagger API documentation
- Custom error message handling
- Vue.js frontend with authentication flow
- Docker and Docker Compose setup for both development and production
- PostgreSQL database

## Project Structure

```
.
├── backend             # Django backend
│   ├── config/         # Django project settings
│   ├── web/            # Django app
│   ├── manage.py
│   └── ...
├── frontend            # Vue.js frontend
│   ├── src/
│   ├── public/
│   └── ...
├── nginx               # Nginx configuration
│   ├── conf.d/         # Server configurations
│   └── ssl/            # SSL certificates
├── docker-compose.yml          # Development docker-compose
├── docker-compose.prod.yml     # Production docker-compose
├── .env.dev                    # Development environment variables
├── .env.prod                   # Production environment variables
├── .env.test                   # Testing environment variables
└── .env.example                # Example environment variables
```

## Development Setup

### Prerequisites

- Docker and Docker Compose
- Git

### Setup Steps

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/jwt-auth-system.git
   cd jwt-auth-system
   ```

2. Create environment files:
   ```bash
   cp .env.example .env.dev
   ```

3. Start the development environment:
   ```bash
   docker-compose up -d
   ```

4. Access the services:
   - Backend: http://localhost:8000
   - Frontend: http://localhost:5173
   - API docs: http://localhost:8000/swagger/
   - Admin: http://localhost:8000/admin/ (admin/admin)

## Testing Setup

For testing with built frontend and a more production-like environment:

1. Create the test environment:
   ```bash
   cp .env.test .env
   ```

2. Start the test environment:
   ```bash
   docker-compose -f docker-compose.prod.yml up -d
   ```

3. Use the app.dev.conf in the nginx configuration to run without SSL:
   ```bash
   cp nginx/conf.d/app.dev.conf nginx/conf.d/default.conf
   ```

4. Access the test instance:
   - Application: http://localhost
   - API: http://localhost/api/
   - Admin: http://localhost/admin/

## Production Deployment

### Prerequisites

- Docker and Docker Compose
- Domain name
- SSL certificates

### Deployment Steps

1. Clone the repository on your server:
   ```bash
   git clone https://github.com/yourusername/jwt-auth-system.git
   cd jwt-auth-system
   ```

2. Create and configure the production environment file:
   ```bash
   cp .env.example .env.prod
   ```
   
   Edit `.env.prod` with your production settings:
   - Update `SECRET_KEY` with a secure random string
   - Set `DJANGO_ALLOWED_HOSTS` to your domain names
   - Update database credentials
   - Set `CORS_ALLOWED_ORIGINS` to your domain names

3. SSL setup:
   Place your SSL certificates in the `nginx/ssl/` directory:
   - `fullchain.pem`: Your SSL certificate chain
   - `privkey.pem`: Your private key
   
   Update the domain names in `nginx/conf.d/app.conf` to match your domain.

4. Start the production environment:
   ```bash
   docker-compose -f docker-compose.prod.yml up -d
   ```

5. Access your application:
   - Frontend: https://your-domain.com
   - Admin: https://your-domain.com/admin/

## Environment Variables

### Backend Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DEBUG` | Django debug mode | `True` in dev, `False` in prod |
| `SECRET_KEY` | Django secret key | Placeholder in dev |
| `DJANGO_ALLOWED_HOSTS` | Allowed hosts | `localhost 127.0.0.1 [::1]` in dev |
| `DB_ENGINE` | Database engine | `django.db.backends.postgresql` |
| `DB_NAME` | Database name | `panel_back_dev` in dev |
| `DB_USER` | Database user | `postgres` in dev |
| `DB_PASSWORD` | Database password | `postgres` in dev |
| `DB_HOST` | Database host | `db` |
| `DB_PORT` | Database port | `5432` |
| `CORS_ALLOWED_ORIGINS` | Allowed CORS origins | Development URLs in dev |
| `JWT_SIGNING_KEY` | JWT signing key | Same as `SECRET_KEY` by default |
| `JWT_REFRESH_TOKEN_LIFETIME_DAYS` | Refresh token lifetime | `30` days |

### Frontend Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `VITE_API_URL` | Backend API URL | `http://localhost:8000/api/auth/` in dev |

## API Endpoints

| Endpoint | Method | Description | Authentication |
|----------|--------|-------------|----------------|
| `/api/auth/login/` | POST | Login and get refresh token | No |
| `/api/auth/logout/` | POST | Logout and clear token | Yes |
| `/api/auth/test/` | GET | Test authentication | Yes |

## Adding SSL Certificates

For production deployment, you'll need SSL certificates. You can get them from Let's Encrypt:

```bash
certbot certonly --standalone -d your-domain.com -d www.your-domain.com
```

Then copy the certificates to the nginx/ssl directory:

```bash
cp /etc/letsencrypt/live/your-domain.com/fullchain.pem nginx/ssl/
cp /etc/letsencrypt/live/your-domain.com/privkey.pem nginx/ssl/
```

## Security Considerations

- JWT tokens are stored in HTTP-only cookies, not in localStorage
- CSRF protection is enabled
- SSL is enforced in production
- Access tokens removed for enhanced security
- Refresh tokens are used exclusively

## Custom Response Format

All API responses follow this format:

```json
{
  "status": 200,
  "success": true,
  "result": {
    // Data payload
  },
  "detail": null
}
```

Error responses:

```json
{
  "status": 400,
  "success": false,
  "result": null,
  "detail": "Error message"
}
```

## Maintenance

### Database Backups

To backup the PostgreSQL database:

```bash
docker-compose exec db pg_dump -U postgres panel_back_prod > backup.sql
```

To restore from a backup:

```bash
cat backup.sql | docker-compose exec -T db psql -U postgres panel_back_prod
```

### Updating the Application

To update the application:

1. Pull the latest changes:
   ```bash
   git pull
   ```

2. Rebuild and restart the containers:
   ```bash
   docker-compose -f docker-compose.prod.yml up -d --build
   ```

## License

This project is licensed under the MIT License - see the LICENSE file for details. 