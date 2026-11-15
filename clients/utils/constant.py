import os

# Get API URL from environment or use default
api_url = os.environ.get("API_URL", "http://localhost:8030").rstrip("/") + "/"
# Browser-visible API origin; keep separate from the Docker-internal API_URL.
public_api_url = os.environ.get("PUBLIC_API_URL", "http://localhost:8030").rstrip("/")
