# Stop the Gremlin database stack

Write-Host "Stopping Gremlin database stack..."

# Stop the container
docker stop janusgraph 2>&1 | Out-Null

# Remove container
docker rm -f janusgraph 2>&1 | Out-Null

Write-Host "✅ Database stack stopped successfully!"
