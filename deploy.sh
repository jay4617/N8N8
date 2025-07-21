#!/bin/bash
# Production deployment script for Quantitative Finance RAG Bot

echo "🚀 Deploying Quantitative Finance RAG Bot to Production"
echo "=================================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if running as root (for systemd setup)
if [[ $EUID -eq 0 ]]; then
   echo -e "${YELLOW}Running as root - will set up systemd service${NC}"
   SETUP_SYSTEMD=true
else
   echo -e "${YELLOW}Running as user - will use PM2 for process management${NC}"
   SETUP_SYSTEMD=false
fi

# Function to check command existence
check_command() {
    if ! command -v $1 &> /dev/null; then
        echo -e "${RED}❌ $1 is not installed${NC}"
        return 1
    else
        echo -e "${GREEN}✅ $1 is available${NC}"
        return 0
    fi
}

# Check dependencies
echo -e "\n📋 Checking dependencies..."
check_command python3 || exit 1
check_command pip3 || exit 1

# Install Python dependencies
echo -e "\n📦 Installing Python dependencies..."
pip3 install -r requirements.txt

# Check environment file
echo -e "\n⚙️ Checking configuration..."
if [ ! -f .env ]; then
    echo -e "${RED}❌ .env file not found${NC}"
    echo "Please create .env file with your configuration"
    exit 1
else
    echo -e "${GREEN}✅ .env file found${NC}"
fi

# Check if vector database exists
if [ ! -d chroma_db ]; then
    echo -e "${YELLOW}⚠️ Vector database not found. Please run initialization first:${NC}"
    echo "python init_database.py"
    exit 1
else
    echo -e "${GREEN}✅ Vector database found${NC}"
fi

# Set up process management
if [ "$SETUP_SYSTEMD" = true ]; then
    echo -e "\n🔧 Setting up systemd service..."
    
    # Create systemd service file
    cat > /etc/systemd/system/qf-rag-bot.service << EOF
[Unit]
Description=Quantitative Finance RAG Telegram Bot
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=$(pwd)
Environment=PATH=$(which python3)
ExecStart=$(which python3) $(pwd)/bot.py
Restart=always
RestartSec=3
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

    # Reload systemd and enable service
    systemctl daemon-reload
    systemctl enable qf-rag-bot.service
    
    echo -e "${GREEN}✅ Systemd service created${NC}"
    echo "To start: sudo systemctl start qf-rag-bot"
    echo "To check status: sudo systemctl status qf-rag-bot"
    echo "To view logs: sudo journalctl -u qf-rag-bot -f"
    
else
    # Check if PM2 is installed
    if ! check_command pm2; then
        echo -e "\n📦 Installing PM2..."
        npm install -g pm2
    fi
    
    echo -e "\n🔧 Setting up PM2 process..."
    
    # Create PM2 ecosystem file
    cat > ecosystem.config.js << EOF
module.exports = {
  apps: [{
    name: 'qf-rag-bot',
    script: 'bot.py',
    interpreter: 'python3',
    cwd: '$(pwd)',
    instances: 1,
    autorestart: true,
    watch: false,
    max_memory_restart: '1G',
    env: {
      NODE_ENV: 'production'
    },
    error_file: './logs/err.log',
    out_file: './logs/out.log',
    log_file: './logs/combined.log',
    time: true
  }]
};
EOF

    # Create logs directory
    mkdir -p logs
    
    echo -e "${GREEN}✅ PM2 configuration created${NC}"
    echo "To start: pm2 start ecosystem.config.js"
    echo "To monitor: pm2 monit"
    echo "To view logs: pm2 logs qf-rag-bot"
    echo "To restart: pm2 restart qf-rag-bot"
fi

# Set up log rotation
echo -e "\n📝 Setting up log rotation..."
if [ "$SETUP_SYSTEMD" = true ]; then
    # Systemd handles log rotation automatically via journald
    echo -e "${GREEN}✅ Log rotation handled by journald${NC}"
else
    # Set up logrotate for PM2 logs
    cat > /etc/logrotate.d/qf-rag-bot << EOF
$(pwd)/logs/*.log {
    daily
    missingok
    rotate 52
    compress
    notifempty
    create 644 $(whoami) $(whoami)
    postrotate
        pm2 reloadLogs
    endscript
}
EOF
    echo -e "${GREEN}✅ Log rotation configured${NC}"
fi

# Create backup script
echo -e "\n💾 Creating backup script..."
cat > backup.sh << 'EOF'
#!/bin/bash
# Backup script for QF RAG Bot

BACKUP_DIR="/backup/qf-rag-bot"
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p $BACKUP_DIR

# Backup vector database
tar -czf $BACKUP_DIR/chroma_db_$DATE.tar.gz chroma_db/

# Backup configuration (without secrets)
cp .env.example $BACKUP_DIR/env_template_$DATE

echo "Backup completed: $BACKUP_DIR"
EOF

chmod +x backup.sh
echo -e "${GREEN}✅ Backup script created${NC}"

# Performance recommendations
echo -e "\n🚀 Production recommendations:"
echo "1. Use SSD storage for vector database"
echo "2. Allocate at least 4GB RAM"
echo "3. Monitor API rate limits"
echo "4. Set up monitoring alerts"
echo "5. Regular backups of vector database"

echo -e "\n${GREEN}🎉 Production deployment setup complete!${NC}"

# Final instructions
echo -e "\n📋 Next steps:"
if [ "$SETUP_SYSTEMD" = true ]; then
    echo "1. sudo systemctl start qf-rag-bot"
    echo "2. sudo systemctl status qf-rag-bot"
else
    echo "1. pm2 start ecosystem.config.js"
    echo "2. pm2 save"
    echo "3. pm2 startup (follow instructions)"
fi
echo "4. Test bot functionality"
echo "5. Set up monitoring and alerts"