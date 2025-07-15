# 🚀 IGS Site Log Manager (SLM) - Docker Deployment

This setup provides a **production-ready Docker Compose deployment** for the IGS Site Log Manager with:

- ✅ SLM Django Application + Gunicorn
- ✅ PostgreSQL with PostGIS for spatial data
- ✅ Nginx reverse proxy with security headers
- ✅ SSL/TLS support (BYO certificates)
- ✅ Rate limiting and performance optimization
- ✅ Development environment support

---

## 🚀 Quick Start - Production

1. **Clone the repository and navigate to deploy folder**

```bash
git clone https://github.com/International-GNSS-Service/SLM.git
cd SLM/deploy
```

2. **Create your environment configuration**

```bash
cp .env.example .env
```

**Important:** Edit `.env` and update these critical settings:
- `SECRET_KEY` - Generate a secure secret key
- `SLM_DATABASE` - Set your PostGIS database URL with secure password
- `ADMINS` - Your admin email address(es)
- `SLM_SITE_NAME` - Your site's domain name
- `EMAIL_HOST*` - Configure email settings for notifications

3. **Start the services**

```bash
docker compose up --build -d
```

4. **Run initial deployment**

```bash
docker compose exec web uv run slm routine deploy
```

5. **Access your SLM instance**

- **HTTP**: [http://localhost](http://localhost)
- **Admin**: [http://localhost/admin](http://localhost/admin)
- **API**: [http://localhost/api](http://localhost/api)

---

## 🔧 Development Setup

For development with live code reloading:

```bash
# Create development .env
cp .env.example .env.dev
# Edit .env.dev with DEBUG=true

# Start development stack
docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build

# Run deployment in development
docker compose exec web uv run slm routine deploy

# Access services:
# - SLM App: http://localhost:8000
# - Database Admin: http://localhost:8080 (Adminer)
# - Redis: localhost:6379
# - PostgreSQL: localhost:5432
```

The development setup includes:
- Django development server with auto-reload
- Direct database access for debugging
- Redis for caching
- Adminer for database administration
- Optional esbuild asset watching for frontend development
- Automatic service dependency management with health checks

---

## 🔐 SSL/TLS Configuration

### Option 1: Bring Your Own Certificates

Place your certificate files in `deploy/certs/`:
- `fullchain.pem` – Your certificate chain
- `privkey.pem` – Your private key

```bash
mkdir -p certs/
# Copy your certificates
docker compose restart nginx
```

### Option 2: Let's Encrypt with Certbot

```bash
# Install certbot
sudo apt-get install certbot

# Generate certificates
sudo certbot certonly --standalone -d yourdomain.com

# Copy to deploy directory
sudo cp /etc/letsencrypt/live/yourdomain.com/fullchain.pem ./certs/
sudo cp /etc/letsencrypt/live/yourdomain.com/privkey.pem ./certs/
sudo chown $USER:$USER ./certs/*

# Restart nginx
docker compose restart nginx
```

**Without certificates:**
- Nginx serves HTTP only
- No automatic HTTPS redirect

---

## 🗄️ Database Management

### Database Configuration

SLM uses a database URL format via the `SLM_DATABASE` environment variable:

```bash
# Format: postgis://username:password@host:port/database
SLM_DATABASE=postgis://slm_user:secure_password@db:5432/slm
```

### Backup Database

```bash
# Create backup (adjust user/db names based on your SLM_DATABASE)
docker compose exec db pg_dump -U slm_user slm > slm_backup_$(date +%Y%m%d).sql

# Or full backup including users
docker compose exec db pg_dumpall -U slm_user > slm_full_backup_$(date +%Y%m%d).sql
```

### Restore Database

```bash
# Restore from backup
cat slm_backup_20241215.sql | docker compose exec -T db psql -U slm_user slm
```

### Upgrade PostGIS

1. Backup your data (see above)
2. Update PostGIS version in `docker-compose.yml`
3. Restart services:

```bash
docker compose down
docker compose up -d
```

---

## 🔧 SLM-Specific Operations

### SLM Management Commands

All SLM operations use the `slm` command entry point:

```bash
# Import legacy site logs
docker compose exec web uv run slm import_archive /path/to/archive.tar.gz

# Import equipment data
docker compose exec web uv run slm import_equipment /path/to/equipment.csv

# Build site index
docker compose exec web uv run slm build_index

# Generate SINEX files
docker compose exec web uv run slm generate_sinex

# Validate database integrity
docker compose exec web uv run slm validate_db

# Validate GeodesyML files
docker compose exec web uv run slm validate_gml
```

### Deployment Operations

SLM provides a comprehensive deployment routine that must be run manually after starting containers:

```bash
# Start containers first
docker compose up -d

# Then run deployment
docker compose exec web uv run slm routine deploy

# The deployment routine handles:
# - Database migrations
# - Static file collection  
# - Frontend asset building with esbuild
# - Cache warming
# - Other deployment tasks
```

**Note:** Deployment is separated from container startup to allow for interactive prompts and better control over the deployment process.

### Development with Asset Watching

For frontend development with automatic asset rebuilding:

```bash
# Start development with asset watching
docker compose --profile watch -f docker-compose.yml -f docker-compose.dev.yml up

# Or manually watch assets in separate terminal
docker compose -f docker-compose.dev.yml run --rm esbuild-watch
```


---

## 📊 Monitoring and Logs

### View logs

```bash
# All services
docker compose logs -f

# Specific service
docker compose logs -f web
docker compose logs -f db
docker compose logs -f nginx
```

### Monitor resources

```bash
# Container stats
docker stats

# Service health
docker compose ps
```

---

## 🔒 Security Considerations

### Production Checklist

- [ ] Change default database password in `SLM_DATABASE` URL
- [ ] Set strong `SECRET_KEY`
- [ ] Configure `ALLOWED_HOSTS` properly
- [ ] Set up SSL certificates
- [ ] Enable security headers (included in nginx config)
- [ ] Configure email for admin notifications
- [ ] Set up regular database backups
- [ ] Consider using Docker secrets for enhanced security
- [ ] Monitor logs for suspicious activity

### Security Features Included

- **Rate limiting**: API (10 req/s) and login (1 req/s) endpoints
- **Security headers**: HSTS, XSS protection, content type sniffing prevention
- **SSL/TLS**: Modern cipher suites and protocols
- **Non-root container**: Application runs as `slm` user
- **Network isolation**: Services communicate via dedicated network

---

## 🚀 Production Deployment

### Using Pre-built Images

Replace the `build` directive in `docker-compose.yml`:

```yaml
web:
  image: ghcr.io/international-gnss-service/slm:latest
  # Remove build section
```

### Environment Variables for Production

Key production settings in `.env`:

```bash
DEBUG=false
SECURE_SSL_REDIRECT=true
SESSION_COOKIE_SECURE=true
CSRF_COOKIE_SECURE=true
SECURE_HSTS_SECONDS=31536000
```

### Scaling

To run multiple web workers:

```bash
docker compose up --scale web=3 -d
```

Nginx is configured with upstream load balancing to handle multiple workers.

### Using Docker Secrets (Enhanced Security)

For production environments, use Docker secrets instead of environment variables:

```bash
# Create secrets directory and files
mkdir -p secrets/
echo "your_secure_database_password" > secrets/db_password.txt
echo "postgis://slm_user:your_secure_database_password@db:5432/slm" > secrets/slm_database_url.txt
chmod 600 secrets/*.txt

# Deploy with secrets
docker compose -f docker-compose.yml -f docker-compose.secrets.yml up -d
```

**Benefits of Docker secrets:**
- Encrypted storage and transmission
- Not visible in container inspection
- Never logged or exposed in process lists
- Fine-grained access control

---

## 🆘 Troubleshooting

### Common Issues

1. **Database connection**: Handled automatically by Docker health checks
2. **Slow startup**: Database health check allows 30s startup + 5 retries
3. **SSL issues**: Check certificate paths and permissions
4. **Service startup order**: Web service waits for database health check to pass
5. **Deployment failures**: Check `slm routine deploy` logs for specific errors

### Debug Commands

```bash
# Enter web container
docker compose exec web bash

# Check Django configuration
docker compose exec web uv run slm check

# Test database connection
docker compose exec web uv run slm dbshell

# View Django settings
docker compose exec web uv run slm diffsettings

# Run SLM-specific diagnostics
docker compose exec web uv run slm validate_db
```

---

## 📚 Additional Resources

- [SLM Documentation](https://igs-slm.readthedocs.io)
- [IGS Site Log Manager GitHub](https://github.com/International-GNSS-Service/SLM)
- [Docker Compose Documentation](https://docs.docker.com/compose/)
- [nginx Documentation](https://nginx.org/en/docs/)
