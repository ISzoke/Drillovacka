# Server part
**Author:** Dominik Horut (`xhorut01`)

## Server development setup

### 1. Install dependencies
```sh
pip install -r requirements.txt
```

### 2. Environment setup
Before running the application, ensure that the database has already been created. To seed the database, use the `.sql` file located in the `db_init` directory.

Next, configure the required environment variables in your `.env` file:

```sh
DJANGO_SETTINGS_MODULE=be.settings
MYSQLHOST=localhost
MYSQLUSER=root
MYSQLPASSWORD=YOUR_PASSWORD
MYSQLDATABASE=YOUR_DATABASE_NAME
MYSQLPORT=YOUR_PORT
```

Additionally, the application uses **Azure Speech-to-Text** and **Gemini** services. To authenticate these services, add your respective API keys to the `.env` file:
```sh
AZURE_API_KEY=YOUR_AZURE_API_KEY
AZURE_REGION=YOUR_AZURE_REGION
GEMINI_API_KEY=YOUR_GEMINI_API_KEY
```

### 3. Run database migrations
```sh
python manage.py migrate
```

### 4. Start the Server with Uvicorn
```sh
uvicorn be.asgi:application --host 0.0.0.0 --port 8000 --reload
```

## Automatic upload of recordings to Dropbox

Use `rclone` to move audio/JSON files from local storage to Dropbox periodically.

### 1. Install rclone on the VPS
```sh
sudo apt update
sudo apt install -y rclone
```

### 2. Configure Dropbox remote
```sh
rclone config
```

Create a remote named `dropbox`.

### 3. Configure sync script
```sh
cd be/scripts
cp dropbox-sync.env.example dropbox-sync.env
chmod +x sync_to_dropbox.sh
```

Adjust paths and remote destination in `dropbox-sync.env`.

### 4. Test manually
```sh
cd be/scripts
./sync_to_dropbox.sh
tail -n 100 ../dropbox-sync.log
```

### 5. Run automatically via cron (every 10 minutes)
```sh
crontab -e
```

Add:
```sh
*/10 * * * * /home/debian/BP/be/scripts/sync_to_dropbox.sh
```

The script moves `*.wav` and `*.json` from `be/audioprompts` and `be/survey` to Dropbox after they are at least 2 minutes old (`MIN_AGE=2m`).