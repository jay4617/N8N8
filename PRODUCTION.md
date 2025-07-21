# Production Deployment Guide

## 🚀 Quick Production Setup

### 1. Prerequisites
- Ubuntu 20.04+ or similar Linux distribution
- Python 3.8+
- 4GB+ RAM (recommended)
- SSD storage for vector database

### 2. Deploy to Production
```bash
# Clone your project
git clone <your-repo>
cd quantitative-finance-rag-bot

# Run deployment script
chmod +x deploy.sh
sudo ./deploy.sh
```

### 3. Configuration
```bash
# Copy production environment template
cp .env.production .env

# Edit with your actual credentials
nano .env
```

Required environment variables:
- `TELEGRAM_BOT_TOKEN` - From @BotFather
- `DEEPSEEK_API_KEY` - From Together.ai

### 4. Start Production Bot

**With Systemd (recommended for servers):**
```bash
sudo systemctl start qf-rag-bot
sudo systemctl enable qf-rag-bot  # Auto-start on boot
```

**With PM2 (recommended for VPS):**
```bash
pm2 start ecosystem.config.js
pm2 save
pm2 startup  # Follow instructions for auto-start
```

## 📊 Monitoring

### Check Status
```bash
# Systemd
sudo systemctl status qf-rag-bot
sudo journalctl -u qf-rag-bot -f

# PM2
pm2 status
pm2 logs qf-rag-bot
pm2 monit
```

### Health Monitoring
```bash
# Run health check
python3 monitor.py

# Or check bot manually
python3 -c "
import asyncio
from telegram import Bot
from config import Config
async def check():
    bot = Bot(Config.TELEGRAM_BOT_TOKEN)
    me = await bot.get_me()
    print(f'✅ Bot @{me.username} is healthy')
asyncio.run(check())
"
```

## 🔧 Production Features

### ✅ Implemented
- **Clean UI** - Professional responses without debug info
- **Rate Limiting** - Prevents API abuse
- **Rotating Logs** - Automatic log management (10MB max, 5 backups)
- **Process Management** - Auto-restart on crashes
- **Health Monitoring** - System resource checking
- **Error Handling** - Graceful failure recovery
- **Backup Scripts** - Vector database backup

### 📱 Available Commands
- `/start` - Welcome message with capabilities
- `/help` - Detailed usage instructions
- `/about` - Bot information and technology stack

### 🔒 Security Features
- Environment variable configuration
- No debug information in responses
- Secure API key management
- Process isolation

## 📈 Performance Tuning

### System Requirements
- **Minimum**: 2GB RAM, 2 CPU cores, 10GB storage
- **Recommended**: 4GB RAM, 4 CPU cores, 50GB SSD storage
- **For high load**: 8GB RAM, 8 CPU cores, 100GB SSD storage

### Optimization Tips
1. **SSD Storage** - Critical for vector database performance
2. **Memory** - More RAM = faster embeddings processing
3. **CPU** - Multiple cores help with concurrent requests
4. **Network** - Low latency to Together.ai API servers

### Scaling Options
- **Horizontal**: Multiple bot instances with load balancer
- **Vertical**: Increase server resources
- **Caching**: Redis for frequently accessed embeddings
- **CDN**: For static assets and documentation

## 🔄 Maintenance

### Regular Tasks
```bash
# Backup vector database (weekly)
./backup.sh

# Update dependencies (monthly)
pip3 install -r requirements-prod.txt --upgrade

# Clean logs (automatic via logrotate)
# Monitor disk space
df -h

# Check system resources
htop
```

### Troubleshooting

**Bot not responding:**
```bash
# Check if process is running
ps aux | grep bot.py

# Check logs
tail -f logs/bot.log

# Restart service
sudo systemctl restart qf-rag-bot
# OR
pm2 restart qf-rag-bot
```

**High memory usage:**
```bash
# Check memory
free -h

# Restart to clear memory
sudo systemctl restart qf-rag-bot
```

**API errors:**
```bash
# Check API key validity
python3 -c "
import asyncio
from llm_service import DeepSeekService
async def test():
    service = DeepSeekService()
    result = await service.test_connection()
    print(f'API Status: {result}')
asyncio.run(test())
"
```

## 📊 Monitoring Dashboard

### Key Metrics to Monitor
- **Response Time** - Average time to answer questions
- **API Calls** - Together.ai usage and rate limits
- **Memory Usage** - RAM consumption trends
- **Disk Space** - Vector database growth
- **Error Rate** - Failed requests percentage
- **User Activity** - Daily/hourly usage patterns

### Alerts to Set Up
- Bot unresponsive for >5 minutes
- Memory usage >85%
- Disk space <10%
- API error rate >5%
- CPU usage >80% for >10 minutes

## 🚀 Production Checklist

- [ ] Environment variables configured
- [ ] Vector database initialized
- [ ] Process manager configured (systemd/PM2)
- [ ] Log rotation enabled
- [ ] Backup script scheduled
- [ ] Monitoring alerts set up
- [ ] Bot tested with sample questions
- [ ] Documentation updated
- [ ] Team notified of deployment

## 📞 Support

### Common Issues
1. **Bot token invalid** - Get new token from @BotFather
2. **API key expired** - Refresh Together.ai API key
3. **Vector DB corrupted** - Restore from backup
4. **Out of memory** - Increase server RAM or restart service

### Performance Benchmarks
- **Cold start**: ~30 seconds (loading models)
- **Response time**: 2-5 seconds average
- **Concurrent users**: 50+ supported
- **Memory usage**: 1-3GB typical

Your Quantitative Finance RAG Bot is now ready for production! 🎉