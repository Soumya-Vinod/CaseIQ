import os

# Ensure config validation passes without a real .env during tests.
os.environ.setdefault("SECRET_KEY", "test-secret-key-that-is-long-enough-to-pass-min-length")
os.environ.setdefault("ENV", "development")
