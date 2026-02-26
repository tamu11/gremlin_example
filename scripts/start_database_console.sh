#!/bin/bash
# Start the Gremlin database stack

echo "Starting Gremlin database stack..."

# Remove any existing stopped container with the same name
if docker ps -a --format '{{.Names}}' | grep -q '^janusgraph$'; then
    echo "Removing existing janusgraph container..."
    docker rm -f janusgraph
fi

# Convert WSL path to a Docker-compatible path if running under WSL
CONF_PATH="$(pwd)/conf"
if grep -qi microsoft /proc/version 2>/dev/null; then
    CONF_PATH="$(wslpath -m "$(pwd)/conf")"
fi

# Only mount conf directory if it actually exists
VOLUME_ARG=""
if [ -d "./conf" ]; then
    VOLUME_ARG="-v ${CONF_PATH}:/janusgraph/conf"
fi

# Start JanusGraph
docker run -d --name janusgraph -p 8182:8182 $VOLUME_ARG janusgraph/janusgraph

if [ $? -ne 0 ]; then
    echo "❌ Failed to start JanusGraph container. Exiting."
    exit 1
fi

# Poll container logs until Gremlin Server reports it's ready
MAX_WAIT=120
ELAPSED=0
READY=false

echo "Waiting for JanusGraph to initialize..."
while [ $ELAPSED -lt $MAX_WAIT ]; do
    if docker logs janusgraph 2>&1 | grep -q "Channel started at port 8182"; then
        READY=true
        break
    fi

    # Check container is still running
    if ! docker ps --format '{{.Names}}' | grep -q '^janusgraph$'; then
        echo "❌ Container stopped unexpectedly. Logs:"
        docker logs janusgraph
        exit 1
    fi

    echo "  Still waiting... (${ELAPSED}s)"
    sleep 5
    ELAPSED=$((ELAPSED + 5))
done

# Check container status
echo "Checking service status:"
docker ps --filter name=janusgraph --format "table {{.Names}}\t{{.Status}}"

if [ "$READY" = false ]; then
    echo "❌ JanusGraph did not start within ${MAX_WAIT}s. Logs:"
    docker logs --tail 20 janusgraph
    exit 1
fi

echo "✅ JanusGraph is ready!"

# Test Gremlin Server connection
echo "Testing Gremlin Server connection..."
python3 -c "
from gremlin_python.driver import client
try:
    c = client.Client('ws://localhost:8182/gremlin', 'g')
    c.submit('g.V().limit(1).toList()').all().result()
    print('✅ Gremlin Server is ready!')
    c.close()
except Exception as e:
    print(f'⚠️  Gremlin Server may not be fully ready yet: {e}')
"

echo ""
echo "Database stack started successfully!"
echo "You can now run: python scripts/load_sample_data.py to load data"
echo "Or: python scripts/query_experts.py to query the graph"
echo ""
echo "Launching Gremlin console (connected to ws://localhost:8182)..."
echo "  Tip: use 'g.V().limit(5).toList()' to verify the graph."
echo "-----------------------------------------------"

# Launch the Gremlin console inside the running container
docker exec -it janusgraph sh -c "
cat > /tmp/remote-connect.groovy << 'EOF'
:remote connect tinkerpop.server conf/remote.yaml
:remote console
EOF
./bin/gremlin.sh -i /tmp/remote-connect.groovy
"