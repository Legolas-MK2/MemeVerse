#!/bin/bash

# Backup-Verzeichnis
BACKUP_DIR="./db_backup"
# Datenbank-Zugangsdaten
DB_HOST="192.168.178.23"
DB_PORT="5433"
DB_NAME="memedb"
DB_USER="discord_meme"

# Stelle sicher, dass das Backup-Verzeichnis existiert
mkdir -p $BACKUP_DIR

# Erstelle Zeitstempel
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/memedb_backup_$TIMESTAMP.sql.gz"

# Environment-Variable für das Passwort aus der .env-Datei laden
source ./.env
export PGPASSWORD=$POSTGREST_PASSWORD

# Backup erstellen und direkt komprimieren
pg_dump -h $DB_HOST -p $DB_PORT -U $DB_USER $DB_NAME | gzip > $BACKUP_FILE

# Backup-Status überprüfen
if [ $? -eq 0 ]; then
    echo "Backup erfolgreich erstellt: $BACKUP_FILE"
    
    # Alte Backups aufräumen (behalte die letzten 7 Tage)
    find $BACKUP_DIR -name "memedb_backup_*.sql.gz" -mtime +7 -delete
else
    echo "Backup fehlgeschlagen!"
    exit 1
fi

# Passwort aus der Umgebung entfernen
unset PGPASSWORD