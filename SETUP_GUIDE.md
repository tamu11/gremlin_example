# Gremlin Graph Database Setup - Complete Guide

## Overview

This setup provides a working Gremlin graph database using JanusGraph that you can use to find subject matter experts by traversing relationships between people, documents, and knowledge areas.

## 🚀 Quick Start

### Windows Users

You have two main options:

#### Option A: Use PowerShell (Recommended)

We've created PowerShell scripts for you:

```powershell
# Start the database
./start_database.ps1

# Load sample data (wait until container is ready)
python scripts/load_sample_data.py

# Query for experts
python scripts/query_experts.py

# Stop when done
./stop_database.ps1
```

Run PowerShell scripts by right-clicking them and selecting "Run with PowerShell".

#### Option B: Use Git Bash or WSL

If you have Git Bash or WSL installed:

```bash
# Start the database
./scripts/start_database.sh

# Load sample data
python scripts/load_sample_data.py

# Query for experts
python scripts/query_experts.py

# Stop when done
./scripts/stop_database.sh
```

#### Option C: Run Docker Directly

You can also run the Docker command directly in PowerShell/CMD:

```powershell
# Start JanusGraph
docker run -d --name janusgraph -p 8182:8182 -v ${env:PWD}\conf:/janusgraph/conf janusgraph/janusgraph

# Wait 30 seconds, then run:
python scripts/load_sample_data.py
python scripts/query_experts.py

# When done:
docker stop janusgraph
```

### Linux/macOS Users

```bash
# Start the database
./scripts/start_database.sh

# Wait a minute or two for initialization

# Load sample data
python scripts/load_sample_data.py

# Query for experts
python scripts/query_experts.py

# Stop when done
./scripts/stop_database.sh
```

### Method 2: Using Docker Compose

```bash
# Start using docker-compose
docker-compose up -d

# Then load data and query as above
```

### Method 3: Standalone Demo (No Docker Required)

```bash
# Run the standalone demo with NetworkX
python standalone_networkx_demo.py

# This generates a visualization file: expert_graph.png
```

## What's in This Setup

### Graph Structure

```
People  ——AUTHORED—–>>  Documents  ——COVERS—–>>  Knowledge Areas
```

### Sample Data Included

**People (7 employees):**
- Alice Johnson (Engineering)
- Bob Smith (Engineering)
- Carol Davis (Data Science)
- David Lee (Data Science)
- Eve Wilson (Product Management)
- Frank Miller (DevOps)
- Grace Brown (Data Science)

**Documents (6 publications):**
- Machine Learning in Production
- Deep Learning Architectures
- Data Pipeline Optimization
- Cloud Migration Guide
- Kubernetes Best Practices
- Data Governance Framework

**Knowledge Areas (6 topics):**
- Machine Learning
- Deep Learning
- Data Engineering
- Cloud Computing
- DevOps
- Data Governance

## Key Features

1. **Graph Traversal**: Find experts by following relationships
2. **Flexible Queries**: Search by single or multiple topics
3. **Visualization**: Generate graph diagrams
4. **Self-contained**: Includes everything needed to run

## Troubleshooting

### If Docker can't connect:
- Make sure Docker Desktop is running
- Check port 8182 is available: `netstat -tuln | grep 8182`
- Restart Docker: `sudo systemctl restart docker`

### If Gremlin server doesn't respond:
- Wait 1-2 minutes after starting for initialization
- Check logs: `docker logs janusgraph`
- Try restarting: `./scripts/stop_database.sh && ./scripts/start_database.sh`

### If you get permission errors:
- Make scripts executable: `chmod +x scripts/*.sh scripts/*.py`

## Customizing

### Add More Data

Edit `scripts/load_sample_data.py` and add more entries to the people, documents, or knowledge areas lists, then add corresponding edges in the `create_relationships()` function.

### Add More Queries

Edit `scripts/query_experts.py` and add new traversal patterns to the `find_experts_by_topic()` or `find_experts_by_topics()` functions.

### Change Graph Structure

Modify the node types and edge types in the loading scripts to match your specific use case.

## Understanding the Queries

The core query pattern is:

```python
# Find people who authored documents that cover a specific topic
g.V().has('KnowledgeArea', 'name', 'Machine Learning').
  out('COVERS').      # Follow COVERS edges to documents
  out('AUTHORED').    # Follow AUTHORED edges to people
  valueMap()         # Return the person details
```

This traverses: KnowledgeArea → Document → Person

## Why This Works

Graph databases excel at relationship traversal. Instead of writing complex SQL joins or nested loops, you simply specify the path you want to follow through the graph. JanusGraph with Gremlin provides a powerful query language optimized for these kinds of traversals.

## Next Steps

1. Try modifying the sample data
2. Add more complex queries (e.g., find people with expertise in multiple areas)
3. Connect to real data sources
4. Build a web interface to query the graph

Enjoy exploring graph databases! 🚀
