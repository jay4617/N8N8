#!/usr/bin/env python3
"""
Simple monitoring script for the RAG bot.
"""

import asyncio
import logging
import time
import psutil
from datetime import datetime
from telegram import Bot
from config import Config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class BotMonitor:
    def __init__(self):
        self.bot = Bot(token=Config.TELEGRAM_BOT_TOKEN)
        self.start_time = time.time()
        
    async def check_bot_health(self):
        """Check if bot is responding."""
        try:
            me = await self.bot.get_me()
            return True, f"Bot @{me.username} is responsive"
        except Exception as e:
            return False, f"Bot health check failed: {e}"
    
    def check_system_resources(self):
        """Check system resources."""
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('.')
        
        return {
            'cpu_percent': cpu_percent,
            'memory_percent': memory.percent,
            'memory_available_gb': memory.available / (1024**3),
            'disk_percent': disk.percent,
            'disk_free_gb': disk.free / (1024**3)
        }
    
    def get_uptime(self):
        """Get bot uptime."""
        uptime_seconds = time.time() - self.start_time
        uptime_hours = uptime_seconds / 3600
        return uptime_hours
    
    async def run_health_check(self):
        """Run complete health check."""
        logger.info("🔍 Running health check...")
        
        # Check bot
        bot_healthy, bot_message = await self.check_bot_health()
        logger.info(f"Bot Status: {bot_message}")
        
        # Check resources
        resources = self.check_system_resources()
        logger.info(f"CPU: {resources['cpu_percent']:.1f}%")
        logger.info(f"Memory: {resources['memory_percent']:.1f}% ({resources['memory_available_gb']:.1f}GB free)")
        logger.info(f"Disk: {resources['disk_percent']:.1f}% ({resources['disk_free_gb']:.1f}GB free)")
        
        # Check uptime
        uptime = self.get_uptime()
        logger.info(f"Uptime: {uptime:.1f} hours")
        
        # Alert conditions
        alerts = []
        if not bot_healthy:
            alerts.append("🚨 Bot not responding")
        if resources['cpu_percent'] > 80:
            alerts.append(f"🚨 High CPU usage: {resources['cpu_percent']:.1f}%")
        if resources['memory_percent'] > 85:
            alerts.append(f"🚨 High memory usage: {resources['memory_percent']:.1f}%")
        if resources['disk_percent'] > 90:
            alerts.append(f"🚨 Low disk space: {resources['disk_free_gb']:.1f}GB free")
        
        if alerts:
            logger.warning("ALERTS:")
            for alert in alerts:
                logger.warning(alert)
        else:
            logger.info("✅ All systems healthy")
        
        return {
            'timestamp': datetime.now().isoformat(),
            'bot_healthy': bot_healthy,
            'resources': resources,
            'uptime_hours': uptime,
            'alerts': alerts
        }

async def main():
    """Main monitoring function."""
    monitor = BotMonitor()
    
    while True:
        try:
            health_data = await monitor.run_health_check()
            
            # Sleep for 5 minutes
            await asyncio.sleep(300)
            
        except KeyboardInterrupt:
            logger.info("Monitoring stopped")
            break
        except Exception as e:
            logger.error(f"Monitor error: {e}")
            await asyncio.sleep(60)  # Wait 1 minute on error

if __name__ == "__main__":
    asyncio.run(main())