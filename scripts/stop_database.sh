#!/bin/bash
# Stop the Gremlin database stack

echo "Stopping Gremlin database stack..."

# Stop the containers
docker stop janusgraph 2>/dev/null || true

# Remove containers
docker rm -f janusgraph 2>/dev/null || true

echo "Database stack stopped successfully!"
