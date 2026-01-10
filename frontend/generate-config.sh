#!/bin/bash
# Generate config.js from REACT_APP_API_URL environment variable
# This mirrors what docker-entrypoint.sh does for local development

CONFIG_FILE="public/static/config.js"

if [ -z "$REACT_APP_API_URL" ]; then
  echo "REACT_APP_API_URL not set, using same-origin API"
  API_URL=""
else
  echo "Using REACT_APP_API_URL: $REACT_APP_API_URL"
  API_URL="$REACT_APP_API_URL"
fi

# Create static directory if it doesn't exist
mkdir -p public/static

# Generate the config file
cat > "$CONFIG_FILE" << EOF
// Runtime configuration generated at startup
window.CONFIG = {
  API_URL: '${API_URL}'
};
EOF

echo "Generated $CONFIG_FILE"
cat "$CONFIG_FILE"
