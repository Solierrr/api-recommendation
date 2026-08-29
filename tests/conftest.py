import os

os.environ.setdefault("APP_ENVIRONMENT", "test")
os.environ.setdefault("NEO4J_URI", "bolt://localhost:7687")
os.environ.setdefault("NEO4J_USER", "neo4j")
os.environ.setdefault("NEO4J_PASSWORD", "test-password")
os.environ.setdefault("DB_URL", "jdbc:postgresql://localhost:5432/test")
os.environ.setdefault("DB_USERNAME", "test")
os.environ.setdefault("DB_PASSWORD", "test-password")
os.environ.setdefault("SYNC_API_KEY", "test-sync-key-with-at-least-32-characters")
