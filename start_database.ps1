# Start the Gremlin database stack

Write-Host "Starting Gremlin database stack..."

# Start JanusGraph using the official image
docker run -d --name janusgraph -p 8182:8182 -v ${env:PWD}\conf:/janusgraph/conf janusgraph/janusgraph

# Wait for services to initialize
Write-Host "Waiting for services to initialize..."
Start-Sleep -Seconds 30

# Check if container is running
$container = docker ps --filter name=janusgraph --format "{{.Names}}"
if ($container -eq "janusgraph") {
    Write-Host "✅ JanusGraph container is running on port 8182"
} else {
    Write-Host "❌ Failed to start container"
    exit 1
}

Write-Host "✅ Setup complete! You can now run:"
Write-Host "   python scripts/load_sample_data.py"
Write-Host "   python scripts/query_experts.py"
