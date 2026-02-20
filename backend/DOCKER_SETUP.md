# 🐳 Docker Setup Instructions

## Quick Start

### 1. Build the Agent Docker Image

```bash
# From backend directory
cd backend
docker build -f docker/Dockerfile.agent -t rift-agent:latest .
```

**This creates an isolated Python 3.11 environment with pytest installed.**

### 2. Verify the Image

```bash
docker images | grep rift-agent
```

You should see:
```
rift-agent    latest    <image-id>    <size>
```

### 3. Start the Backend

```bash
# From backend directory
python -m uvicorn app.main:app --reload --port 8000 --reload-dir app
```

The backend will automatically:
- ✅ Detect Docker is available
- ✅ Use the `rift-agent:latest` image
- ✅ Run tests in isolated containers
- ✅ Auto-cleanup containers after each run

---

## 🎯 How It Works

### Agent Execution Flow

```
1. User triggers agent run
   ↓
2. Backend clones repo to workspace/
   ↓
3. Backend checks: Is Docker available?
   ├─ YES → Use Docker (preferred)
   └─ NO  → Fall back to local execution
   ↓
4. Docker: Create container
   docker run --rm \
     -v workspace/repo:/workspace \
     --memory 512m \
     --cpus 1.0 \
     --network none \
     --read-only \
     rift-agent:latest
   ↓
5. Inside Container:
   - Install dependencies (pip install -r requirements.txt)
   - Run tests (pytest)
   - Return results as JSON
   ↓
6. Container auto-deleted (--rm flag)
   ↓
7. Backend parses errors
   ↓
8. Backend applies fixes (on host filesystem)
   ↓
9. Repeat until tests pass
   ↓
10. Push branch to GitHub
```

---

## 🔧 Docker Commands

### Build Agent Image
```bash
docker build -f docker/Dockerfile.agent -t rift-agent:latest .
```

### Rebuild (force)
```bash
docker build --no-cache -f docker/Dockerfile.agent -t rift-agent:latest .
```

### Test Container Manually
```bash
# Clone a test repo first
cd workspace
git clone https://github.com/r3b1e/ai-agent-test-python.git
cd ..

# Run container
docker run --rm \
  -v "$(pwd)/workspace/ai-agent-test-python:/workspace" \
  rift-agent:latest
```

### Check Running Containers
```bash
docker ps | grep rift-agent
```

### Clean Up Old Containers
```bash
docker ps -a | grep rift-agent
docker rm -f $(docker ps -aq --filter "name=rift-agent")
```

### View Container Logs
```bash
docker logs <container-id>
```

### Remove Image
```bash
docker rmi rift-agent:latest
```

---

## 🛡️ Security Features

The Docker container has these security restrictions:

1. **No Network Access**
   ```bash
   --network none
   ```
   Container can't make external requests (prevents data exfiltration)

2. **Read-Only Filesystem**
   ```bash
   --read-only
   --tmpfs /tmp:rw,noexec,nosuid,size=100m
   ```
   Container can't modify system files

3. **Resource Limits**
   ```bash
   --memory 512m   # Max 512MB RAM
   --cpus 1.0      # Max 1 CPU core
   ```
   Prevents resource exhaustion attacks

4. **Non-Root User**
   ```dockerfile
   USER agent  # UID 1000
   ```
   Container doesn't run as root

5. **Auto-Cleanup**
   ```bash
   --rm  # Delete container after exit
   ```
   No container pollution

---

## 🔍 Troubleshooting

### Issue: "Docker not found"

**Solution:**
```bash
# Check Docker is installed
docker --version

# Check Docker is running
docker ps

# On Windows: Start Docker Desktop
```

### Issue: "Permission denied" on Windows

**Solution:**
```bash
# Run PowerShell as Administrator
# Or: Share the drive in Docker Desktop settings
```

### Issue: "Image not found"

**Solution:**
```bash
# Build the image
docker build -f docker/Dockerfile.agent -t rift-agent:latest .

# Verify it exists
docker images | grep rift-agent
```

### Issue: "Container timeout"

**Solution:**
- Tests take longer than 3 minutes
- Increase timeout in `docker_executor.py`:
  ```python
  timeout=300  # 5 minutes
  ```

### Issue: "Disk space full"

**Solution:**
```bash
# Clean up old images
docker image prune -a

# Clean up old containers
docker container prune

# Clean up everything (careful!)
docker system prune -a --volumes
```

---

## 📊 Performance Comparison

| Metric | Local (venv) | Docker |
|--------|-------------|--------|
| **Setup Time** | ~10s (create venv) | ~2s (container start) |
| **Test Execution** | ~5s | ~6s (+1s overhead) |
| **Cleanup** | Manual (disk waste) | Automatic (0s) |
| **Memory** | Uncontrolled | Limited (512MB) |
| **Security** | Low (host access) | High (isolated) |
| **Parallel Runs** | No | Yes |

**Verdict: Docker is 1s slower per run, but MUCH safer and cleaner!**

---

## 🎯 Production Deployment

### Option 1: Docker-in-Docker (DinD)

```yaml
# docker-compose.yml
services:
  api:
    image: rift-api:latest
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
    environment:
      - DOCKER_HOST=unix:///var/run/docker.sock
```

### Option 2: Pre-Built Images on Registry

```bash
# Push to Docker Hub
docker tag rift-agent:latest your-username/rift-agent:latest
docker push your-username/rift-agent:latest

# Pull on server
docker pull your-username/rift-agent:latest
```

### Option 3: Kubernetes

```yaml
# kubernetes/agent-job.yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: rift-agent
spec:
  template:
    spec:
      containers:
      - name: agent
        image: rift-agent:latest
        volumeMounts:
        - name: workspace
          mountPath: /workspace
      restartPolicy: Never
```

---

## 🚀 CI/CD Integration

### GitHub Actions

```yaml
# .github/workflows/build-agent.yml
name: Build Agent Image

on:
  push:
    paths:
      - 'backend/docker/Dockerfile.agent'

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Build Docker image
        run: |
          cd backend
          docker build -f docker/Dockerfile.agent -t rift-agent:latest .
      
      - name: Test image
        run: |
          docker run --rm rift-agent:latest --version
```

---

## 📈 Monitoring

### View Resource Usage

```bash
# Real-time stats
docker stats

# Specific container
docker stats <container-name>
```

### Check Logs

```bash
# Backend logs
tail -f backend/logs/app.log

# Container logs (if still running)
docker logs -f <container-name>
```

---

## ✅ Quick Test

Test the Docker setup with this command:

```bash
# From backend directory
python -c "
from app.docker_executor import DockerExecutor
executor = DockerExecutor()
print('Docker available:', executor.check_docker_available())
print('Image exists:', executor.check_image_exists())
"
```

Expected output:
```
Docker available: True
Image exists: True
```

---

## 🎉 Success!

If you see:
- ✅ `🐳 Docker detected, using containerized execution`
- ✅ `🐳 Starting Docker container: rift-agent-...`
- ✅ `✅ Tests completed successfully`

**You're running with Docker! 🐳🎉**
