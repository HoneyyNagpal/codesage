# Deployment Guide

## Prerequisites

- **Server**: Ubuntu 20.04+ or similar Linux distribution
- **Node.js**: 18.x or higher
- **Python**: 3.10 or higher
- **PostgreSQL**: 15 or higher
- **Redis**: 7 or higher
- **Docker** (optional but recommended)
- **Domain name** (for production)
- **SSL certificate** (Let's Encrypt recommended)

---

## Deployment Options

### Option 1: Docker Deployment (Recommended)

This is the easiest and most reliable deployment method.

#### 1. Server Setup

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Install Docker Compose
sudo apt install docker-compose-plugin

# Add user to docker group
sudo usermod -aG docker $USER
newgrp docker
```

#### 2. Clone and Configure

```bash
# Clone repository
git clone https://github.com/yourusername/codesage.git
cd codesage

# Copy environment files
cp backend/.env.example backend/.env
cp analyzer/.env.example analyzer/.env
cp frontend/.env.example frontend/.env

# Edit environment files with production values
nano backend/.env
nano analyzer/.env
nano frontend/.env
```

#### 3. Configure Environment Variables

**backend/.env**
```env
NODE_ENV=production
PORT=5000
DATABASE_URL=postgresql://codesage:STRONG_PASSWORD@postgres:5432/codesage
REDIS_URL=redis://redis:6379
JWT_SECRET=generate-a-strong-random-secret
GITHUB_CLIENT_ID=your-github-client-id
GITHUB_CLIENT_SECRET=your-github-client-secret
FRONTEND_URL=https://yourdomain.com
ANALYZER_URL=http://analyzer:8000
```

**analyzer/.env**
```env
DEBUG=False
LOG_LEVEL=INFO
DATABASE_URL=postgresql://codesage:STRONG_PASSWORD@postgres:5432/codesage
REDIS_URL=redis://redis:6379
OPENAI_API_KEY=your-openai-key
ANTHROPIC_API_KEY=your-anthropic-key
DEFAULT_LLM_PROVIDER=anthropic
```

**frontend/.env**
```env
VITE_API_URL=https://yourdomain.com/api
VITE_WS_URL=wss://yourdomain.com
VITE_GITHUB_CLIENT_ID=your-github-client-id
```

#### 4. Build and Deploy

```bash
# Build images
docker-compose -f docker-compose.prod.yml build

# Start services
docker-compose -f docker-compose.prod.yml up -d

# Check status
docker-compose -f docker-compose.prod.yml ps

# View logs
docker-compose -f docker-compose.prod.yml logs -f
```

#### 5. Initialize Database

```bash
# Run migrations
docker-compose -f docker-compose.prod.yml exec backend npm run migrate

# Or manually
docker-compose -f docker-compose.prod.yml exec postgres psql -U codesage -d codesage -f /docker-entrypoint-initdb.d/01-schema.sql
```

---

### Option 2: Manual Deployment

#### 1. Install Dependencies

```bash
# Node.js
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt install -y nodejs

# Python
sudo apt install -y python3.10 python3.10-venv python3-pip

# PostgreSQL
sudo apt install -y postgresql postgresql-contrib

# Redis
sudo apt install -y redis-server

# Nginx
sudo apt install -y nginx certbot python3-certbot-nginx
```

#### 2. Setup PostgreSQL

```bash
# Create user and database
sudo -u postgres psql << EOF
CREATE USER codesage WITH PASSWORD 'STRONG_PASSWORD';
CREATE DATABASE codesage OWNER codesage;
GRANT ALL PRIVILEGES ON DATABASE codesage TO codesage;
\q
EOF

# Initialize schema
psql -U codesage -d codesage -f database/schema.sql
```

#### 3. Setup Backend

```bash
cd backend
npm ci --production
npm run migrate

# Install PM2 for process management
sudo npm install -g pm2

# Start backend
pm2 start src/server.js --name codesage-backend
pm2 save
pm2 startup
```

#### 4. Setup Analyzer

```bash
cd analyzer
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Start with systemd
sudo nano /etc/systemd/system/codesage-analyzer.service
```

**codesage-analyzer.service**
```ini
[Unit]
Description=CodeSage Analyzer
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/var/www/codesage/analyzer
Environment="PATH=/var/www/codesage/analyzer/venv/bin"
ExecStart=/var/www/codesage/analyzer/venv/bin/uvicorn src.api.app:app --host 0.0.0.0 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable codesage-analyzer
sudo systemctl start codesage-analyzer
```

#### 5. Setup Celery Worker

```bash
sudo nano /etc/systemd/system/codesage-celery.service
```

**codesage-celery.service**
```ini
[Unit]
Description=CodeSage Celery Worker
After=network.target redis.service

[Service]
Type=simple
User=www-data
WorkingDirectory=/var/www/codesage/analyzer
Environment="PATH=/var/www/codesage/analyzer/venv/bin"
ExecStart=/var/www/codesage/analyzer/venv/bin/celery -A src.workers.analysis_worker worker --loglevel=info
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable codesage-celery
sudo systemctl start codesage-celery
```

#### 6. Build Frontend

```bash
cd frontend
npm ci
npm run build
```

#### 7. Configure Nginx

```bash
sudo nano /etc/nginx/sites-available/codesage
```

**nginx configuration**
```nginx
upstream backend {
    server localhost:5000;
}

upstream analyzer {
    server localhost:8000;
}

server {
    listen 80;
    server_name yourdomain.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name yourdomain.com;

    ssl_certificate /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;

    # Frontend
    location / {
        root /var/www/codesage/frontend/dist;
        try_files $uri $uri/ /index.html;
    }

    # Backend API
    location /api {
        proxy_pass http://backend;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
    }

    # WebSocket
    location /socket.io {
        proxy_pass http://backend;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }

    # Analyzer (internal only)
    location /analyzer {
        proxy_pass http://analyzer;
        allow 127.0.0.1;
        deny all;
    }
}
```

```bash
sudo ln -s /etc/nginx/sites-available/codesage /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

#### 8. SSL Certificate

```bash
sudo certbot --nginx -d yourdomain.com
```

---

## GitHub OAuth Setup

1. Go to GitHub Settings → Developer settings → OAuth Apps
2. Create new OAuth App:
   - **Application name**: CodeSage
   - **Homepage URL**: `https://yourdomain.com`
   - **Authorization callback URL**: `https://yourdomain.com/api/github/callback`
3. Copy Client ID and Client Secret to environment files

---

## Monitoring & Maintenance

### Health Checks

```bash
# Check services
curl https://yourdomain.com/health
curl http://localhost:5000/health
curl http://localhost:8000/health

# Docker logs
docker-compose logs -f backend
docker-compose logs -f analyzer

# PM2 logs
pm2 logs codesage-backend
```

### Database Backups

```bash
# Automated daily backups
sudo nano /etc/cron.daily/backup-codesage-db
```

**backup script**
```bash
#!/bin/bash
DATE=$(date +%Y%m%d)
BACKUP_DIR="/var/backups/codesage"
mkdir -p $BACKUP_DIR

# Backup database
pg_dump -U codesage codesage | gzip > $BACKUP_DIR/codesage_$DATE.sql.gz

# Keep only last 7 days
find $BACKUP_DIR -name "*.sql.gz" -mtime +7 -delete
```

```bash
sudo chmod +x /etc/cron.daily/backup-codesage-db
```

### Scaling

#### Horizontal Scaling

1. Deploy multiple backend instances behind load balancer
2. Use Redis for session storage
3. Add more Celery workers for analysis queue

#### Database Scaling

1. Enable PostgreSQL replication
2. Use read replicas for queries
3. Consider connection pooling (PgBouncer)

---

## Troubleshooting

### Service Won't Start

```bash
# Check logs
docker-compose logs [service-name]
journalctl -u codesage-analyzer -n 50
pm2 logs

# Check ports
sudo netstat -tlnp | grep :5000
sudo netstat -tlnp | grep :8000
```

### Database Connection Issues

```bash
# Test PostgreSQL connection
psql -U codesage -d codesage -h localhost

# Check PostgreSQL status
sudo systemctl status postgresql
```

### High Memory Usage

```bash
# Check resource usage
docker stats
htop

# Restart services
docker-compose restart
pm2 restart all
```

### Analysis Queue Issues

```bash
# Check Redis
redis-cli ping
redis-cli INFO

# Check Celery workers
celery -A src.workers.analysis_worker inspect active
```

---

## Security Checklist

- [ ] Use strong passwords for database
- [ ] Generate secure JWT secret
- [ ] Enable HTTPS with valid SSL certificate
- [ ] Configure firewall (UFW)
- [ ] Set up fail2ban
- [ ] Regular security updates
- [ ] Backup database regularly
- [ ] Monitor logs for suspicious activity
- [ ] Use environment variables for secrets
- [ ] Enable PostgreSQL SSL connections

---

## Performance Optimization

1. **Enable Redis caching** for file analysis results
2. **Use CDN** for frontend assets
3. **Enable gzip compression** in Nginx
4. **Optimize database** with proper indexes
5. **Scale Celery workers** based on queue size
6. **Monitor** with tools like Prometheus + Grafana

---

## Support

For issues, contact: support@codesage.io
Documentation: https://docs.codesage.io