# Gremlin Graph Database Setup for Finding Subject Matter Experts

This project sets up a working Gremlin graph database using JanusGraph to find subject matter experts by traversing relationships between people, documents, and knowledge areas.

## ✅ Setup Complete!

All dependencies are installed and ready to use:

- **gremlinpython** - For querying the Gremlin server ✅
- **networkx** and **matplotlib** - For the standalone demo ✅
- **JanusGraph Docker image** - Ready to run ✅
- **Configuration files** - All set up ✅

## 🚀 Quick Start

### Option 1: Full JanusGraph Setup (Recommended)

```bash
# Start the database
./scripts/start_database.sh

# Wait 30-60 seconds for initialization

# Load sample data
python scripts/load_sample_data.py

# Query for experts
python scripts/query_experts.py

# Stop when done
./scripts/stop_database.sh
```

### Option 2: Standalone Demo (No Docker)

```bash
# Run without Docker
python standalone_networkx_demo.py
```

### Windows Users

Use the PowerShell scripts:

```powershell
# Start database
./start_database.ps1

# Load and query
python scripts/load_sample_data.py
python scripts/query_experts.py

# Stop when done
./stop_database.ps1
```

## 📦 What's Included

- **Docker setup** - Uses official JanusGraph image
- **Bash scripts** - For Linux/macOS: start/stop database
- **PowerShell scripts** - For Windows: start/stop database
- **Python scripts** - Load data and query for experts
- **Sample data** - 7 people, 6 documents, 6 knowledge areas
- **Documentation** - Complete setup guides

## 📚 Documentation

- **[SETUP_GUIDE.md](SETUP_GUIDE.md)** - Detailed setup instructions
- **[INSTALLATION.md](INSTALLATION.md)** - Installation guide
- **[WINDOWS_SETUP.txt](WINDOWS_SETUP.txt)** - Windows-specific instructions
- **[SETUP_SUMMARY.txt](SETUP_SUMMARY.txt)** - Complete overview

## 🎯 How It Works

The graph models relationships:
- **People** → AUTHORED → **Documents** → COVERS → **Knowledge Areas**

Queries traverse these relationships to find experts for specific topics!

## 💡 Example Output

```
Finding experts for: Machine Learning

#1
Name: Alice Johnson
ID: p1
Email: alice.johnson@company.com
Department: Engineering
Topics: Machine Learning

#2
Name: Bob Smith
ID: p2
Email: bob.smith@company.com
Department: Engineering
Topics: Machine Learning, Deep Learning
```

## 🔧 Customization

Want to add your own data?

1. Edit `scripts/load_sample_data.py` - Add more people, documents, or topics
2. Edit `scripts/query_experts.py` - Add new query patterns
3. Run your modified scripts!

## 🐳 Docker Notes

- Make sure Docker Desktop is running
- Port 8182 is used by default
- Configuration files are in the `conf/` directory

## 🎓 What You'll Learn

- Graph database concepts with JanusGraph
- Gremlin query language
- Modeling relationships
- Graph traversal patterns

Enjoy exploring graph databases! 🚀

**Need help?** Check the documentation files for detailed guidance.
