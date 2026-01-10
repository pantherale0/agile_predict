#!/bin/bash
# Generate config.js from environment variables at container startup
# This allows runtime configuration without rebuilding the React app

CONFIG_FILE="/app/frontend/public/config.js"

# Use REACT_APP_API_URL if provided, otherwise auto-detect
if [ -z "$REACT_APP_API_URL" ]; then
  echo "REACT_APP_API_URL not set, will use runtime detection (same-origin API)"
  API_URL=""
else
  echo "Using REACT_APP_API_URL: $REACT_APP_API_URL"
  API_URL="$REACT_APP_API_URL"
fi

# Generate the config file
cat > "$CONFIG_FILE" << EOF
// Runtime configuration generated at container startup
window.CONFIG = {
  API_URL: '${API_URL}'
};
EOF

echo "Generated $CONFIG_FILE"
cat "$CONFIG_FILE"

# Start the application
exec "$@"
