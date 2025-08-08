"""
Production Disaster Recovery and Backup System
Handles database backups, configuration backups, and disaster recovery procedures
"""
import os
import asyncio
import logging
import shutil
import subprocess
import boto3
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional
from dataclasses import dataclass
import psycopg2
import redis
import schedule
import time

logger = logging.getLogger('backup')

@dataclass
class BackupConfig:
    """Backup configuration"""
    database_url: str
    redis_host: str
    redis_port: int
    s3_bucket: str
    s3_region: str
    retention_days: int
    backup_frequency_hours: int
    local_backup_dir: str
    encrypt_backups: bool = True

class DatabaseBackup:
    """Database backup and recovery operations"""
    
    def __init__(self, config: BackupConfig):
        self.config = config
        self.backup_dir = Path(config.local_backup_dir) / "database"
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        
    async def create_database_backup(self) -> str:
        """Create a complete database backup"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_filename = f"trading_db_backup_{timestamp}.sql"
        backup_path = self.backup_dir / backup_filename
        
        try:
            # Create PostgreSQL dump
            cmd = [
                'pg_dump',
                self.config.database_url,
                '--no-password',
                '--verbose',
                '--clean',
                '--no-acl',
                '--no-owner',
                '--format=custom',
                '--file', str(backup_path)
            ]
            
            logger.info(f"Creating database backup: {backup_filename}")
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            
            if result.returncode == 0:
                logger.info(f"Database backup created successfully: {backup_path}")
                
                # Compress the backup
                compressed_path = await self._compress_backup(backup_path)
                
                # Encrypt if enabled
                if self.config.encrypt_backups:
                    encrypted_path = await self._encrypt_backup(compressed_path)
                    os.remove(compressed_path)
                    return str(encrypted_path)
                    
                return str(compressed_path)
            else:
                raise Exception(f"pg_dump failed: {result.stderr}")
                
        except Exception as e:
            logger.error(f"Database backup failed: {e}")
            raise
            
    async def _compress_backup(self, backup_path: Path) -> Path:
        """Compress backup file"""
        compressed_path = backup_path.with_suffix('.sql.gz')
        
        cmd = ['gzip', str(backup_path)]
        result = subprocess.run(cmd, capture_output=True)
        
        if result.returncode == 0:
            return compressed_path
        else:
            raise Exception(f"Compression failed: {result.stderr}")
            
    async def _encrypt_backup(self, backup_path: Path) -> Path:
        """Encrypt backup file using GPG"""
        encrypted_path = backup_path.with_suffix(backup_path.suffix + '.gpg')
        
        # Use environment variable for GPG passphrase
        passphrase = os.getenv('BACKUP_ENCRYPTION_KEY')
        if not passphrase:
            logger.warning("No encryption key found, skipping encryption")
            return backup_path
            
        cmd = [
            'gpg',
            '--symmetric',
            '--cipher-algo', 'AES256',
            '--compress-algo', '1',
            '--s2k-mode', '3',
            '--s2k-digest-algo', 'SHA512',
            '--s2k-count', '65011712',
            '--force-mdc',
            '--quiet',
            '--no-greeting',
            '--batch',
            '--yes',
            '--passphrase', passphrase,
            '--output', str(encrypted_path),
            str(backup_path)
        ]
        
        result = subprocess.run(cmd, capture_output=True)
        
        if result.returncode == 0:
            os.remove(backup_path)  # Remove unencrypted file
            return encrypted_path
        else:
            raise Exception(f"Encryption failed: {result.stderr}")

class RedisBackup:
    """Redis backup operations"""
    
    def __init__(self, config: BackupConfig):
        self.config = config
        self.backup_dir = Path(config.local_backup_dir) / "redis"
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        self.redis_client = redis.Redis(
            host=config.redis_host, 
            port=config.redis_port, 
            decode_responses=True
        )
        
    async def create_redis_backup(self) -> str:
        """Create Redis backup"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_filename = f"redis_backup_{timestamp}.rdb"
        backup_path = self.backup_dir / backup_filename
        
        try:
            # Trigger Redis BGSAVE
            self.redis_client.bgsave()
            
            # Wait for background save to complete
            while self.redis_client.lastsave() == self.redis_client.lastsave():
                await asyncio.sleep(1)
                
            # Copy the RDB file
            redis_rdb_path = "/var/lib/redis/dump.rdb"  # Default Redis RDB location
            if os.path.exists(redis_rdb_path):
                shutil.copy2(redis_rdb_path, backup_path)
                logger.info(f"Redis backup created: {backup_path}")
                return str(backup_path)
            else:
                raise Exception("Redis RDB file not found")
                
        except Exception as e:
            logger.error(f"Redis backup failed: {e}")
            raise

class S3BackupManager:
    """AWS S3 backup management"""
    
    def __init__(self, config: BackupConfig):
        self.config = config
        self.s3_client = boto3.client(
            's3',
            region_name=config.s3_region,
            aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
            aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY')
        )
        
    async def upload_backup(self, local_path: str, s3_key: str) -> bool:
        """Upload backup to S3"""
        try:
            logger.info(f"Uploading backup to S3: {s3_key}")
            
            # Add metadata
            metadata = {
                'backup_type': 'trading_app',
                'created_at': datetime.now().isoformat(),
                'environment': os.getenv('ENVIRONMENT', 'production')
            }
            
            self.s3_client.upload_file(
                local_path,
                self.config.s3_bucket,
                s3_key,
                ExtraArgs={
                    'Metadata': metadata,
                    'ServerSideEncryption': 'AES256'
                }
            )
            
            logger.info(f"Backup uploaded successfully: s3://{self.config.s3_bucket}/{s3_key}")
            return True
            
        except Exception as e:
            logger.error(f"S3 upload failed: {e}")
            return False
            
    async def cleanup_old_backups(self):
        """Remove old backups from S3 based on retention policy"""
        try:
            cutoff_date = datetime.now() - timedelta(days=self.config.retention_days)
            
            # List objects in the backup bucket
            response = self.s3_client.list_objects_v2(
                Bucket=self.config.s3_bucket,
                Prefix='trading-app-backups/'
            )
            
            if 'Contents' not in response:
                return
                
            deleted_count = 0
            for obj in response['Contents']:
                if obj['LastModified'].replace(tzinfo=None) < cutoff_date:
                    self.s3_client.delete_object(
                        Bucket=self.config.s3_bucket,
                        Key=obj['Key']
                    )
                    deleted_count += 1
                    logger.info(f"Deleted old backup: {obj['Key']}")
                    
            logger.info(f"Cleanup complete: {deleted_count} old backups removed")
            
        except Exception as e:
            logger.error(f"S3 cleanup failed: {e}")

class ConfigurationBackup:
    """Backup application configurations and secrets"""
    
    def __init__(self, config: BackupConfig):
        self.config = config
        self.backup_dir = Path(config.local_backup_dir) / "configuration"
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        
    async def create_config_backup(self) -> str:
        """Create backup of configuration files"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_filename = f"config_backup_{timestamp}.tar.gz"
        backup_path = self.backup_dir / backup_filename
        
        # Files and directories to backup
        backup_items = [
            'alembic.ini',
            'alembic/',
            'monitoring/',
            'scripts/',
            'CLAUDE.md',
            '.github/',
            'netlify.toml',
            'requirements.txt'
        ]
        
        try:
            # Create tar archive
            cmd = ['tar', '-czf', str(backup_path)] + backup_items
            result = subprocess.run(cmd, cwd=Path.cwd(), capture_output=True)
            
            if result.returncode == 0:
                logger.info(f"Configuration backup created: {backup_path}")
                return str(backup_path)
            else:
                raise Exception(f"Configuration backup failed: {result.stderr}")
                
        except Exception as e:
            logger.error(f"Configuration backup failed: {e}")
            raise

class DisasterRecoveryManager:
    """Main disaster recovery and backup orchestrator"""
    
    def __init__(self):
        self.config = BackupConfig(
            database_url=os.getenv('DATABASE_URL'),
            redis_host=os.getenv('REDIS_HOST', 'localhost'),
            redis_port=int(os.getenv('REDIS_PORT', '6379')),
            s3_bucket=os.getenv('BACKUP_S3_BUCKET'),
            s3_region=os.getenv('AWS_REGION', 'us-east-1'),
            retention_days=int(os.getenv('BACKUP_RETENTION_DAYS', '30')),
            backup_frequency_hours=int(os.getenv('BACKUP_FREQUENCY_HOURS', '6')),
            local_backup_dir=os.getenv('LOCAL_BACKUP_DIR', './backups'),
            encrypt_backups=os.getenv('ENCRYPT_BACKUPS', 'true').lower() == 'true'
        )
        
        self.db_backup = DatabaseBackup(self.config)
        self.redis_backup = RedisBackup(self.config)
        self.s3_manager = S3BackupManager(self.config)
        self.config_backup = ConfigurationBackup(self.config)
        
    async def create_full_backup(self) -> Dict[str, str]:
        """Create complete system backup"""
        backup_info = {
            'timestamp': datetime.now().isoformat(),
            'type': 'full_backup',
            'status': 'started'
        }
        
        try:
            logger.info("Starting full system backup...")
            
            # Create database backup
            db_backup_path = await self.db_backup.create_database_backup()
            backup_info['database_backup'] = db_backup_path
            
            # Create Redis backup
            redis_backup_path = await self.redis_backup.create_redis_backup()
            backup_info['redis_backup'] = redis_backup_path
            
            # Create configuration backup
            config_backup_path = await self.config_backup.create_config_backup()
            backup_info['config_backup'] = config_backup_path
            
            # Upload to S3 if configured
            if self.config.s3_bucket:
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                
                # Upload database backup
                db_s3_key = f"trading-app-backups/database/db_backup_{timestamp}.sql.gz"
                await self.s3_manager.upload_backup(db_backup_path, db_s3_key)
                
                # Upload Redis backup
                redis_s3_key = f"trading-app-backups/redis/redis_backup_{timestamp}.rdb"
                await self.s3_manager.upload_backup(redis_backup_path, redis_s3_key)
                
                # Upload configuration backup
                config_s3_key = f"trading-app-backups/config/config_backup_{timestamp}.tar.gz"
                await self.s3_manager.upload_backup(config_backup_path, config_s3_key)
                
            backup_info['status'] = 'completed'
            logger.info("Full system backup completed successfully")
            
            # Clean up old local backups
            await self._cleanup_local_backups()
            
            # Clean up old S3 backups
            if self.config.s3_bucket:
                await self.s3_manager.cleanup_old_backups()
                
            return backup_info
            
        except Exception as e:
            backup_info['status'] = 'failed'
            backup_info['error'] = str(e)
            logger.error(f"Full system backup failed: {e}")
            raise
            
    async def _cleanup_local_backups(self):
        """Clean up old local backup files"""
        cutoff_date = datetime.now() - timedelta(days=7)  # Keep local backups for 7 days
        
        for backup_type in ['database', 'redis', 'configuration']:
            backup_dir = Path(self.config.local_backup_dir) / backup_type
            if backup_dir.exists():
                for backup_file in backup_dir.iterdir():
                    if backup_file.is_file():
                        file_time = datetime.fromtimestamp(backup_file.stat().st_mtime)
                        if file_time < cutoff_date:
                            backup_file.unlink()
                            logger.info(f"Removed old local backup: {backup_file}")

    def schedule_backups(self):
        """Schedule automated backups"""
        logger.info(f"Scheduling backups every {self.config.backup_frequency_hours} hours")
        
        schedule.every(self.config.backup_frequency_hours).hours.do(
            lambda: asyncio.run(self.create_full_backup())
        )
        
        # Schedule daily cleanup
        schedule.every().day.at("02:00").do(
            lambda: asyncio.run(self.s3_manager.cleanup_old_backups())
        )

    def run_backup_scheduler(self):
        """Run the backup scheduler"""
        logger.info("Starting backup scheduler...")
        
        while True:
            schedule.run_pending()
            time.sleep(60)  # Check every minute

# CLI interface for manual backups
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Trading App Backup System')
    parser.add_argument('--backup', action='store_true', help='Create full backup')
    parser.add_argument('--schedule', action='store_true', help='Run backup scheduler')
    parser.add_argument('--cleanup', action='store_true', help='Clean up old backups')
    
    args = parser.parse_args()
    
    dr_manager = DisasterRecoveryManager()
    
    if args.backup:
        asyncio.run(dr_manager.create_full_backup())
    elif args.schedule:
        dr_manager.schedule_backups()
        dr_manager.run_backup_scheduler()
    elif args.cleanup:
        asyncio.run(dr_manager.s3_manager.cleanup_old_backups())
    else:
        parser.print_help()