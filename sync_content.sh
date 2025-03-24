#!/bin/bash
# sync_content.sh
# Sync the local content directory with the remote server directory.
# Adjust the REMOTE_* variables to match your server details.

# Check that rsync is installed.
if ! command -v rsync >/dev/null 2>&1; then
    echo "rsync is not installed. Please install rsync and try again."
    exit 1
fi

# Configuration - modify these variables.
REMOTE_USER="rsp"
REMOTE_HOST="jessica.athnex.com"
REMOTE_PATH="/home/rsp/voidfemme_website/content"  # remote directory where content should be synced

# Local content directory (relative to project root)
LOCAL_DIR="content/"

# Rsync options: archive, verbose, compress, and delete extraneous remote files.
RSYNC_OPTIONS="-avz --delete"

echo "Starting sync from ${LOCAL_DIR} to ${REMOTE_USER}@${REMOTE_HOST}:${REMOTE_PATH}..."
rsync ${RSYNC_OPTIONS} "${LOCAL_DIR}" "${REMOTE_USER}@${REMOTE_HOST}:${REMOTE_PATH}"

# Check if the rsync command was successful.
if [ $? -eq 0 ]; then
    echo "Sync completed successfully."
else
    echo "Sync encountered an error."
fi
