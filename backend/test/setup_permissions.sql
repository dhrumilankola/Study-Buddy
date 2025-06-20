-- PostgreSQL setup script for Study Buddy database
-- Run this as the postgres superuser

-- Create user if not exists
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'study_buddy') THEN
        CREATE USER study_buddy WITH PASSWORD 'study_buddy_password';
    END IF;
END
$$;

-- Create database if not exists
SELECT 'CREATE DATABASE study_buddy_db OWNER study_buddy'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'study_buddy_db')\gexec

-- Grant database privileges
GRANT ALL PRIVILEGES ON DATABASE study_buddy_db TO study_buddy;

-- Connect to the study_buddy_db database
\c study_buddy_db

-- Grant schema privileges
GRANT ALL ON SCHEMA public TO study_buddy;
GRANT CREATE ON SCHEMA public TO study_buddy;
GRANT USAGE ON SCHEMA public TO study_buddy;

-- Grant default privileges for future objects
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO study_buddy;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO study_buddy;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON FUNCTIONS TO study_buddy;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TYPES TO study_buddy;

-- Additional permissions that might be needed
GRANT CREATE ON DATABASE study_buddy_db TO study_buddy;

-- Show current privileges
\dp

-- Verify user can create objects
SET ROLE study_buddy;
SELECT current_user;

-- Reset to superuser
RESET ROLE;

-- Success message
SELECT 'Database setup completed successfully!' as status;
