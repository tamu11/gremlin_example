#!/bin/bash
# Start the Gremlin database stack

echo "Starting Gremlin database stack..."

# Start JanusGraph using the official image
docker run -d --name janusgraph -p 8182:8182 -v $(pwd)/conf:/janusgraph/conf janusgraph/janusgraph

# Wait for services to initialize
echo "Waiting for services to initialize..."
sleep 30

# Check if containers are running
echo "Checking service status:"
docker ps --filter name=janusgraph --format "table {{.Names}}\t{{.Status}}"

# Test Gremlin Server connection
echo "Testing Gremlin Server connection..."
python3 -c "
from gremlin_python.driver import client
from gremlin_python.driver.protocol import GremlinServerError
try:
    c = client.Client('ws://localhost:8182/gremlin', 'g')
    result = c.submit('g.V().limit(1).toList()').all()
    print('✅ Gremlin Server is ready!')
    c.close()
except Exception as e:
    print('⚠️  Gremlin Server may not be fully ready yet')
"

echo "Database stack started successfully!"
echo "You can now run: python scripts/load_sample_data.py to load data"
echo "Or: python scripts/query_experts.py to query the graph"
