# Deployment Guide

This guide explains how to deploy the AI Video Generation application in different environments.

## Table of Contents
- [Environment Configuration](#environment-configuration)
- [Development Deployment](#development-deployment)
- [Staging Deployment](#staging-deployment)
- [Production Deployment](#production-deployment)
- [Environment Variables](#environment-variables)
- [Security Considerations](#security-considerations)

## Environment Configuration

The application supports three environments:
- **Development**: Local development with hot-reload and relaxed security
- **Staging**: Pre-production testing with production-like settings
- **Production**: Production deployment with strict security

Each environment has its own configuration file:
- `.env.development` - Development settings
- `.env.staging` - Staging settings
- `.env.production` - Production settings

## Development Deployment

### Using Make (Recommended)

```bash
# Start development environment
make dev

# Start in detached mode
make dev-d

# View logs
make logs

# Stop all services
make stop
```

### Using Docker Compose Directly

```bash
# Start development environment
docker-compose -f docker-compose.dev.yml up --build

# Start in detached mode
docker-compose -f docker-compose.dev.yml up -d --build

# Stop services
docker-compose -f docker-compose.dev.yml down
```

### Development Features
- Hot-reload enabled for both backend and frontend
- Rate limiting disabled
- More verbose logging (DEBUG level)
- CORS allows all localhost variations
- Faster video encoding (ultrafast preset)

## Staging Deployment

### Configuration

1. Update `.env.staging` with your staging credentials:
```bash
# Update CORS origins
CORS_ORIGINS=https://staging.yourdomain.com,https://staging-api.yourdomain.com

# Update AWS credentials
AWS_ACCESS_KEY_ID=your_staging_key
AWS_SECRET_ACCESS_KEY=your_staging_secret
S3_BUCKET_NAME=video-gen-staging
CLOUDFRONT_DOMAIN=staging-cdn.yourdomain.com
```

2. Deploy:
```bash
# Using Make
make staging

# Or using Docker Compose
docker-compose -f docker-compose.yml --env-file .env.staging up -d --build
```

### Staging Features
- Moderate rate limiting
- Production-like settings
- Separate S3 bucket
- INFO level logging

## Production Deployment

### Prerequisites

1. **Domain Setup**
   - Configure DNS for your domain
   - Set up SSL certificates (recommended: Let's Encrypt)

2. **AWS Setup**
   - Create production S3 bucket
   - Set up CloudFront distribution
   - Create IAM user with appropriate permissions

3. **Server Requirements**
   - NVIDIA GPU with CUDA support
   - Docker with NVIDIA Container Toolkit
   - Minimum 32GB RAM
   - 100GB+ storage

### Configuration

1. Update `.env.production`:
```bash
# Application
ENVIRONMENT=production
DEBUG=false

# CORS - Production domains only
CORS_ORIGINS=https://yourdomain.com,https://www.yourdomain.com,https://api.yourdomain.com

# Rate Limiting - Strict
RATE_LIMIT_ENABLED=true
RATE_LIMIT_PER_MINUTE=60
RATE_LIMIT_GENERATE_PER_HOUR=10
RATE_LIMIT_UPLOAD_PER_HOUR=20

# AWS
AWS_ACCESS_KEY_ID=your_production_key
AWS_SECRET_ACCESS_KEY=your_production_secret
S3_BUCKET_NAME=video-gen-production
CLOUDFRONT_DOMAIN=cdn.yourdomain.com

# Redis Password
REDIS_PASSWORD=your_strong_redis_password

# Flower Authentication
FLOWER_USER=admin
FLOWER_PASSWORD=your_secure_flower_password
```

2. Deploy:
```bash
# Using Make
make prod

# Or using Docker Compose
docker-compose -f docker-compose.prod.yml up -d --build
```

### Production Features
- Strict CORS policy
- Rate limiting enabled
- Multiple web workers (4)
- Redis password protection
- Flower authentication
- Better video quality (slow preset, CRF 20)
- Health checks enabled
- Auto-restart on failure

## Environment Variables

### Application Settings
- `ENVIRONMENT`: Environment name (development/staging/production)
- `DEBUG`: Enable debug mode (true/false)
- `APP_NAME`: Application name
- `APP_VERSION`: Application version

### CORS Settings
- `CORS_ORIGINS`: Comma-separated list of allowed origins
- `CORS_ALLOW_CREDENTIALS`: Allow credentials (true/false)
- `CORS_ALLOW_METHODS`: Allowed HTTP methods
- `CORS_ALLOW_HEADERS`: Allowed headers

### Rate Limiting
- `RATE_LIMIT_ENABLED`: Enable rate limiting (true/false)
- `RATE_LIMIT_PER_MINUTE`: General API calls per minute
- `RATE_LIMIT_GENERATE_PER_HOUR`: Video generation calls per hour
- `RATE_LIMIT_UPLOAD_PER_HOUR`: Image upload calls per hour

### AWS Configuration
- `AWS_ACCESS_KEY_ID`: AWS access key
- `AWS_SECRET_ACCESS_KEY`: AWS secret key
- `AWS_REGION`: AWS region
- `S3_BUCKET_NAME`: S3 bucket name
- `CLOUDFRONT_DOMAIN`: CloudFront domain (optional)

### GPU Settings
- `CUDA_VISIBLE_DEVICES`: GPU device IDs (default: 0)
- `ENABLE_CPU_OFFLOAD`: Enable CPU offloading (true/false)
- `USE_BF16`: Use BFloat16 precision (true/false)
- `USE_FP16`: Use Float16 precision (true/false)

## Security Considerations

### Production Security Checklist

- [ ] Update all default passwords
- [ ] Configure strict CORS origins (no wildcards)
- [ ] Enable rate limiting
- [ ] Use HTTPS for all endpoints
- [ ] Set up firewall rules
- [ ] Configure Redis password
- [ ] Enable Flower authentication
- [ ] Use strong AWS IAM policies
- [ ] Set up monitoring and alerts
- [ ] Configure automatic backups
- [ ] Enable log rotation
- [ ] Use environment-specific S3 buckets
- [ ] Implement API authentication (recommended)
- [ ] Set up DDoS protection (e.g., Cloudflare)
- [ ] Regular security updates

### Network Security

1. **Firewall Rules**
```bash
# Allow only necessary ports
ufw allow 80/tcp    # HTTP
ufw allow 443/tcp   # HTTPS
ufw allow 22/tcp    # SSH (restrict to your IP)
ufw enable
```

2. **Reverse Proxy (Nginx)**
```nginx
server {
    listen 80;
    server_name api.yourdomain.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name api.yourdomain.com;

    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /ws {
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

## Monitoring

### Health Checks

```bash
# Check API health
curl https://api.yourdomain.com/health

# Check Flower (Celery monitoring)
# Access: https://yourdomain.com:5555
```

### Logs

```bash
# View all logs
make logs

# View specific service logs
make logs-web
make logs-worker
make logs-frontend

# Production logs location
./backend/logs/api_*.log
./backend/logs/worker_*.log
```

### Metrics to Monitor

- API response times
- Video generation success rate
- Queue length (Celery)
- GPU utilization
- Memory usage
- Disk space
- Rate limit violations
- Error rates

## Backup and Recovery

### Database Backup (Redis)

```bash
# Create Redis backup
docker exec video-gen-redis-prod redis-cli SAVE

# Backup file location
/data/dump.rdb
```

### Model Cache Backup

```bash
# Backup Hugging Face models
docker run --rm -v huggingface_cache_prod:/data -v $(pwd):/backup \
  alpine tar czf /backup/models-backup.tar.gz /data
```

### S3 Backup

S3 videos are already backed up. Consider enabling:
- S3 versioning
- Cross-region replication
- Lifecycle policies for old videos

## Scaling

### Horizontal Scaling

To scale workers:

```yaml
# docker-compose.prod.yml
worker:
  deploy:
    replicas: 3  # Run 3 worker instances
```

### Load Balancing

For multiple web instances:

```yaml
web:
  deploy:
    replicas: 3
```

Then use Nginx or HAProxy for load balancing.

## Troubleshooting

### Common Issues

1. **GPU Not Detected**
```bash
# Check GPU
nvidia-smi

# Verify Docker GPU access
docker run --rm --gpus all nvidia/cuda:12.1.0-base-ubuntu22.04 nvidia-smi
```

2. **Redis Connection Failed**
```bash
# Check Redis
docker exec video-gen-redis-prod redis-cli ping
```

3. **Rate Limit Too Strict**
```bash
# Temporarily disable in .env.production
RATE_LIMIT_ENABLED=false
```

4. **S3 Upload Failed**
```bash
# Check AWS credentials
docker exec video-gen-web-prod python -c "import boto3; print(boto3.client('s3').list_buckets())"
```

## Rollback

To rollback to previous version:

```bash
# Stop current deployment
make stop

# Checkout previous version
git checkout <previous-commit>

# Rebuild and deploy
make prod
```

## Support

For issues or questions:
- Check logs: `make logs`
- Review health: `curl https://api.yourdomain.com/health`
- Open GitHub issue
