# 📦 Installation Instructions

This guide explains how to set up the Gremlin graph database example.

## ✅ Step 1: Install Python Dependencies

All required Python packages are now installed in the virtual environment at `.venv`.

Installed packages include:
- **gremlinpython** - For querying the Gremlin server
- **networkx** and **matplotlib** - For the standalone demo

## 🚀 Step 2: Choose Your Run Method

### Option A: Run with Docker (Recommended for full experience)

1. **Make sure Docker Desktop is running**
   - If not installed, download from https://www.docker.com/products/docker-desktop
   - Launch Docker Desktop from the Start menu

2. **Start the database** (choose one method):

   **Windows PowerShell:**
   ```powershell
   .\start_database.ps1
   ```

   **Linux/macOS Bash:**
   ```bash
   ./scripts/start_database.sh
   ```

   **Manual Docker command:**
   ```bash
   docker run -d -p 8182:8182 tinkerpop/gremlin-server
   ```

3. **Wait for the database to start** (about 30-60 seconds)

4. **Run the data loader and query script:**
   ```bash
   source .venv/Scripts/activate  # Activate the virtual environment
   python gremlin_query.py
   ```

5. **Stop the database when done:**

   **Windows PowerShell:**
   ```powershell
   .\stop_database.ps1
   ```

   **Linux/macOS Bash:**
   ```bash
   ./scripts/stop_database.sh
   ```

### Option B: Run Standalone Demo (No Docker Required)

If you can't use Docker, run the standalone demo:
```bash
source .venv/Scripts/activate
python standalone_demo.py
```

This uses NetworkX to simulate a graph database locally.

## 📚 Additional Notes

- All Python dependencies are installed in `.venv`
- The virtual environment is already activated in the scripts
- No additional setup needed!

## ❓ Troubleshooting

**Q: I get connection errors when running gremlin_query.py**
A: Wait a bit longer for Docker to fully start, or check that Docker Desktop is running.

**Q: The database doesn't start**
A: Make sure Docker Desktop is running and your user has permission to run Docker commands.

**Q: Module not found errors**
A: Activate the virtual environment first: `source .venv/Scripts/activate` (or `.venv\Scripts\activate` in cmd)

**Q: Port 8182 is already in use**
A: Stop any running Docker containers, or change the port in the scripts.
