PORT="${PORT:-8080}"

mcpo --config mcp-config.json &

uvicorn open_webui.main:app --port $PORT --host 0.0.0.0 --forwarded-allow-ips '*' --reload