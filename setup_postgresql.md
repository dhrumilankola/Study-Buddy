# PostgreSQL Setup Guide for Study Buddy

This guide will help you set up PostgreSQL for the Study Buddy application.

## Prerequisites

- Python 3.8+ installed
- Administrative privileges on your system

## Step 1: Install PostgreSQL

### Windows
1. Download PostgreSQL from https://www.postgresql.org/download/windows/
2. Run the installer and follow the setup wizard
3. Remember the password you set for the `postgres` user
4. Default port is 5432 (keep this unless you have conflicts)

### macOS
```bash
# Using Homebrew
brew install postgresql
brew services start postgresql

# Create a database user
createuser -s postgres
```

### Linux (Ubuntu/Debian)
```bash
sudo apt update
sudo apt install postgresql postgresql-contrib
sudo systemctl start postgresql
sudo systemctl enable postgresql
```

## Step 2: Configure PostgreSQL

1. **Connect to PostgreSQL as superuser:**
   ```bash
   # Windows (using psql from Start Menu or Command Prompt)
   psql -U postgres -h localhost
   
   # macOS/Linux
   sudo -u postgres psql
   ```

2. **Set password for postgres user (if not already set):**
   ```sql
   ALTER USER postgres PASSWORD 'postgres';
   ```

3. **Exit psql:**
   ```sql
   \q
   ```

## Step 3: Install Python Dependencies

Navigate to the Study Buddy backend directory and install the new dependencies:

```bash
cd backend
pip install sqlalchemy asyncpg alembic psycopg2-binary
```

Or install from requirements.txt:
```bash
pip install -r requirements.txt
```

## Step 4: Configure Database Settings

The database configuration is already set in `backend/app/config.py`:

```python
DATABASE_URL = "postgresql+asyncpg://study_buddy:study_buddy_password@localhost:5432/study_buddy_db"
DATABASE_HOST = "localhost"
DATABASE_PORT = 5432
DATABASE_NAME = "study_buddy_db"
DATABASE_USER = "study_buddy"
DATABASE_PASSWORD = "study_buddy_password"
```

**Note:** For production, you should change these credentials and store them in environment variables.

## Step 5: Create Database and User

Run the database setup script:

```bash
cd backend
python setup_database.py
```

This script will:
- Create the `study_buddy` user
- Create the `study_buddy_db` database
- Grant necessary privileges
- Test the connection

## Step 6: Initialize Database Tables

The application will automatically create the database tables when it starts. The tables include:

- **documents**: Stores document metadata
- **chat_sessions**: Stores chat session information
- **chat_messages**: Stores individual chat messages

## Step 7: Run Database Migrations (Optional)

If you want to use Alembic for database migrations:

```bash
cd backend
alembic init alembic  # Only if not already initialized
alembic revision --autogenerate -m "Initial migration"
alembic upgrade head
```

## Step 8: Test the Setup

1. **Start the Study Buddy application:**
   ```bash
   cd backend
   python main.py
   ```

2. **Check the logs** for successful database initialization:
   ```
   INFO - Database initialized successfully
   INFO - Study Buddy API started successfully
   ```

3. **Test database endpoints** by visiting:
   - http://localhost:8000/docs
   - Look for the "database" section in the API documentation

## Troubleshooting

### Connection Issues

1. **PostgreSQL not running:**
   ```bash
   # Windows
   net start postgresql-x64-14  # Version may vary
   
   # macOS
   brew services start postgresql
   
   # Linux
   sudo systemctl start postgresql
   ```

2. **Authentication failed:**
   - Verify the postgres user password
   - Check pg_hba.conf file for authentication settings
   - Ensure the database user and password match the configuration

3. **Port conflicts:**
   - Check if port 5432 is available
   - Modify the DATABASE_PORT in config.py if needed

### Permission Issues

1. **User creation failed:**
   ```sql
   -- Connect as postgres superuser and run:
   CREATE USER study_buddy WITH PASSWORD 'study_buddy_password';
   CREATE DATABASE study_buddy_db OWNER study_buddy;
   GRANT ALL PRIVILEGES ON DATABASE study_buddy_db TO study_buddy;
   ```

### Python Package Issues

1. **psycopg2 installation fails:**
   ```bash
   # Try the binary version
   pip install psycopg2-binary
   
   # Or install system dependencies first (Linux)
   sudo apt-get install libpq-dev python3-dev
   pip install psycopg2
   ```

## Verification

After successful setup, you should be able to:

1. ✅ Connect to PostgreSQL
2. ✅ Start the Study Buddy application without database errors
3. ✅ Access database API endpoints at `/api/v1/db/`
4. ✅ See database tables created automatically

## Next Steps

Once PostgreSQL is set up:

1. **Upload documents** - They will now be tracked in the database
2. **Start chat sessions** - Chat history will be persisted
3. **Monitor usage** - Database provides insights into model usage patterns
4. **Scale the application** - Database provides foundation for multi-user support

## Production Considerations

For production deployment:

1. **Change default passwords**
2. **Use environment variables** for database credentials
3. **Set up database backups**
4. **Configure connection pooling**
5. **Monitor database performance**
6. **Set up SSL connections**
