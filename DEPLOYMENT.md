# 🚀 Deployment Guide - EC2 Ubuntu Instance

Complete guide to deploy the RIFT AI DevOps Agent backend on AWS EC2 Ubuntu instance.

## 📋 Prerequisites

- **EC2 Instance**: Ubuntu 22.04 LTS (t3.large recommended)
- **Resources**: 16GB RAM, 20GB storage ✓ (sufficient for initial deployment)
- **Access**: SSH key pair for EC2 instance
- **Domain** (Optional): For SSL/HTTPS setup

---

## 🔧 Step 1: Initial Server Setup

### 1.1 Connect to EC2 Instance

```bash
# Replace with your instance IP and key file
ssh -i your-key.pem ubuntu@your-ec2-ip-address
```

### 1.2 Update System Packages

```bash
sudo apt update && sudo apt upgrade -y
```

### 1.3 Install Essential Tools

```bash
sudo apt install -y git curl wget vim build-essential software-properties-common
```

---

## 🐍 Step 2: Install Python 3.11+

```bash
# Add deadsnakes PPA for latest Python
sudo add-apt-repository ppa:deadsnakes/ppa -y
sudo apt update

# Install Python 3.11
sudo apt install -y python3.11 python3.11-venv python3.11-dev python3-pip

# Set Python 3.11 as default (optional)
sudo update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.11 1
sudo update-alternatives --install /usr/bin/python python /usr/bin/python3.11 1

# Verify installation
python3 --version  # Should show Python 3.11.x
```

---

## 📦 Step 3: Install Node.js 18+

```bash
# Install Node.js 18 LTS using NodeSource
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt install -y nodejs

# Verify installation
node --version  # Should show v18.x.x
npm --version   # Should show 9.x.x or 10.x.x

# Install global packages
sudo npm install -g pm2
```

---

## 🐳 Step 4: Install Docker

```bash
# Remove old Docker versions
sudo apt remove docker docker-engine docker.io containerd runc

# Install Docker dependencies
sudo apt install -y apt-transport-https ca-certificates curl gnupg lsb-release

# Add Docker GPG key
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg

# Add Docker repository
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# Install Docker
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# Start Docker service
sudo systemctl start docker
sudo systemctl enable docker

# Add ubuntu user to docker group (to run docker without sudo)
sudo usermod -aG docker ubuntu

# IMPORTANT: Log out and log back in for group changes to take effect
exit
# Then reconnect: ssh -i your-key.pem ubuntu@your-ec2-ip-address

# Verify Docker installation
docker --version
docker run hello-world
```

---

## 📂 Step 5: Clone Repository

```bash
# Navigate to home directory
cd ~

# Clone your repository
git clone https://github.com/r3b1e/RFIT_PUNE_HACK122.git
cd RFIT_PUNE_HACK122

# Or if you need authentication
git clone https://YOUR_GITHUB_TOKEN@github.com/r3b1e/RFIT_PUNE_HACK122.git
```

---

## 🏗️ Step 6: Build Docker Images

### 6.1 Build Python Agent Image

```bash
cd ~/RFIT_PUNE_HACK122

# Build Python agent Docker image
docker build -f backend/docker/Dockerfile.agent -t rift-agent:latest backend

# Verify image
docker images | grep rift-agent
```

### 6.2 Build Node.js Agent Image

```bash
# Build Node.js agent Docker image
docker build -f backend/docker/Dockerfile.agent.node -t rift-agent-node:latest backend

# Verify image
docker images | grep rift-agent-node
```

Expected output:
```
rift-agent          latest    <image-id>   5 minutes ago   765MB
rift-agent-node     latest    <image-id>   3 minutes ago   493MB
```

---

## 🔐 Step 7: Setup Environment Variables

```bash
cd ~/RFIT_PUNE_HACK122/backend

# Create .env file
nano .env
```

Add the following configuration:

```bash
# GitHub Configuration
GITHUB_TOKEN=your_github_personal_access_token

# OpenAI Configuration (if using AI features)
OPENAI_API_KEY=your_openai_api_key

# Server Configuration
HOST=0.0.0.0
PORT=8000

# Docker Configuration
DOCKER_ENABLED=true

# CORS Configuration
CORS_ORIGINS=http://localhost:3000,http://your-domain.com

# Workspace Configuration
WORKSPACE_PATH=/home/ubuntu/RFIT_PUNE_HACK122/backend/workspace
```

**Save and exit**: Press `Ctrl+X`, then `Y`, then `Enter`

### 7.1 Generate GitHub Token

1. Go to https://github.com/settings/tokens
2. Click "Generate new token (classic)"
3. Select scopes:
   - ✓ `repo` (Full control of private repositories)
   - ✓ `workflow` (Update GitHub Action workflows)
   - ✓ `write:packages` (Upload packages)
4. Generate and copy the token
5. Paste it in your `.env` file

---

## 📦 Step 8: Install Python Dependencies

```bash
cd ~/RFIT_PUNE_HACK122/backend

# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip

# Install dependencies
pip install -r requirements.txt

# Verify installation
pip list
```

---

## 🚀 Step 9: Start Backend Server

### Option A: Direct Run (for testing)

```bash
cd ~/RFIT_PUNE_HACK122/backend
source venv/bin/activate

# Run with uvicorn
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Keep terminal open. Access at: `http://your-ec2-ip:8000`

### Option B: Using PM2 (recommended for production)

```bash
cd ~/RFIT_PUNE_HACK122/backend

# Create PM2 ecosystem file
cat > ecosystem.config.js << 'EOF'
module.exports = {
  apps: [{
    name: 'rift-backend',
    script: 'venv/bin/uvicorn',
    args: 'app.main:app --host 0.0.0.0 --port 8000',
    cwd: '/home/ubuntu/RFIT_PUNE_HACK122/backend',
    instances: 1,
    autorestart: true,
    watch: false,
    max_memory_restart: '1G',
    env: {
      NODE_ENV: 'production'
    },
    error_file: 'logs/err.log',
    out_file: 'logs/out.log',
    log_file: 'logs/combined.log',
    time: true
  }]
};
EOF

# Create logs directory
mkdir -p logs

# Start with PM2
pm2 start ecosystem.config.js

# Save PM2 configuration
pm2 save

# Setup PM2 to start on system boot
pm2 startup
# Copy and run the command that PM2 outputs

# View logs
pm2 logs rift-backend

# Other PM2 commands
pm2 status           # Check status
pm2 restart rift-backend  # Restart
pm2 stop rift-backend     # Stop
pm2 delete rift-backend   # Remove from PM2
```

---

## 🌐 Step 10: Configure Security Groups (AWS)

### 10.1 Required Ports

Go to EC2 Console → Security Groups → Your Instance Security Group → Inbound Rules

Add these rules:

| Type       | Protocol | Port Range | Source        | Description           |
|------------|----------|------------|---------------|-----------------------|
| SSH        | TCP      | 22         | Your IP/0.0.0.0/0 | SSH access     |
| HTTP       | TCP      | 80         | 0.0.0.0/0     | HTTP traffic          |
| HTTPS      | TCP      | 443        | 0.0.0.0/0     | HTTPS traffic         |
| Custom TCP | TCP      | 8000       | 0.0.0.0/0     | Backend API (temp)    |

**Note**: Port 8000 can be removed once nginx is configured.

---

## 🔄 Step 11: Setup Nginx (Reverse Proxy)

### 11.1 Install Nginx

```bash
sudo apt install -y nginx

# Start and enable
sudo systemctl start nginx
sudo systemctl enable nginx
```

### 11.2 Configure Nginx

```bash
# Create backend configuration
sudo nano /etc/nginx/sites-available/rift-backend
```

Add this configuration:

```nginx
upstream rift_backend {
    server 127.0.0.1:8000;
}

server {
    listen 80;
    server_name your-domain.com www.your-domain.com;  # Replace with your domain or EC2 IP

    client_max_body_size 50M;

    # API routes
    location /api {
        proxy_pass http://rift_backend;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;
        proxy_read_timeout 300s;
        proxy_connect_timeout 300s;
    }

    # WebSocket support
    location /ws {
        proxy_pass http://rift_backend;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_read_timeout 86400;
    }

    # Root routes
    location / {
        proxy_pass http://rift_backend;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

**Save and exit**: Press `Ctrl+X`, then `Y`, then `Enter`

```bash
# Enable the site
sudo ln -s /etc/nginx/sites-available/rift-backend /etc/nginx/sites-enabled/

# Remove default site
sudo rm /etc/nginx/sites-enabled/default

# Test nginx configuration
sudo nginx -t

# Reload nginx
sudo systemctl reload nginx
```

Now access your backend at: `http://your-ec2-ip/` or `http://your-domain.com/`

---

## 🔒 Step 12: Setup SSL with Let's Encrypt (Optional)

### 12.1 Install Certbot

```bash
sudo apt install -y certbot python3-certbot-nginx
```

### 12.2 Obtain SSL Certificate

```bash
# Replace with your domain
sudo certbot --nginx -d your-domain.com -d www.your-domain.com

# Follow the prompts:
# - Enter email address
# - Agree to terms
# - Choose whether to redirect HTTP to HTTPS (recommended: Yes)
```

### 12.3 Auto-renewal

```bash
# Test renewal
sudo certbot renew --dry-run

# Certbot automatically sets up a cron job for renewal
# Check it with:
sudo systemctl status certbot.timer
```

---

## 🔍 Step 13: Verify Deployment

### 13.1 Test Backend API

```bash
# Test health endpoint
curl http://localhost:8000/health
# Expected: {"status":"healthy","docker":true}

# Test from outside
curl http://your-ec2-ip:8000/health
```

### 13.2 Test Docker Images

```bash
# Test Python agent
docker run --rm rift-agent:latest echo "Python agent works!"

# Test Node.js agent
docker run --rm rift-agent-node:latest echo "Node.js agent works!"
```

### 13.3 Check Logs

```bash
# PM2 logs
pm2 logs rift-backend

# Nginx logs
sudo tail -f /var/log/nginx/access.log
sudo tail -f /var/log/nginx/error.log

# System logs
sudo journalctl -u nginx -f
```

---

## 📊 Step 14: Monitoring and Management

### 14.1 System Resources

```bash
# Check memory usage
free -h

# Check disk usage
df -h

# Check Docker disk usage
docker system df

# Clean up Docker
docker system prune -a  # Warning: removes unused images
```

### 14.2 PM2 Monitoring

```bash
# Real-time monitoring
pm2 monit

# Process info
pm2 info rift-backend

# Restart if needed
pm2 restart rift-backend

# View logs
pm2 logs rift-backend --lines 100
```

---

## 🔄 Step 15: Update Deployment

When you push code updates:

```bash
cd ~/RFIT_PUNE_HACK122

# Pull latest changes
git pull origin main

# If Docker images changed, rebuild
docker build -f backend/docker/Dockerfile.agent -t rift-agent:latest backend
docker build -f backend/docker/Dockerfile.agent.node -t rift-agent-node:latest backend

# Update Python dependencies if needed
cd backend
source venv/bin/activate
pip install -r requirements.txt

# Restart backend
pm2 restart rift-backend

# Check status
pm2 status
pm2 logs rift-backend --lines 50
```

---

## 🛡️ Step 16: Security Best Practices

### 16.1 Firewall Setup

```bash
# Install UFW
sudo apt install -y ufw

# Default policies
sudo ufw default deny incoming
sudo ufw default allow outgoing

# Allow SSH (IMPORTANT: do this first!)
sudo ufw allow 22/tcp

# Allow HTTP and HTTPS
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# Enable firewall
sudo ufw enable

# Check status
sudo ufw status verbose
```

### 16.2 Secure SSH

```bash
# Edit SSH config
sudo nano /etc/ssh/sshd_config
```

Make these changes:
```
PermitRootLogin no
PasswordAuthentication no
PubkeyAuthentication yes
```

```bash
# Restart SSH
sudo systemctl restart sshd
```

### 16.3 Keep System Updated

```bash
# Create update script
cat > ~/update-system.sh << 'EOF'
#!/bin/bash
sudo apt update
sudo apt upgrade -y
sudo apt autoremove -y
sudo apt autoclean
docker system prune -f
EOF

chmod +x ~/update-system.sh

# Run weekly updates
sudo crontab -e
# Add this line:
# 0 3 * * 0 /home/ubuntu/update-system.sh > /home/ubuntu/update.log 2>&1
```

---

## 🐛 Troubleshooting

### Issue 1: Port 8000 Already in Use

```bash
# Find process using port 8000
sudo lsof -i :8000

# Kill the process
sudo kill -9 <PID>
```

### Issue 2: Docker Permission Denied

```bash
# Make sure user is in docker group
sudo usermod -aG docker $USER

# Log out and log back in
exit
```

### Issue 3: Out of Disk Space

```bash
# Check disk usage
df -h

# Clean Docker
docker system prune -a -f --volumes

# Clean logs
sudo journalctl --vacuum-time=7d
pm2 flush
```

### Issue 4: Backend Not Starting

```bash
# Check logs
pm2 logs rift-backend

# Check if port is available
netstat -tuln | grep 8000

# Try running manually to see errors
cd ~/RFIT_PUNE_HACK122/backend
source venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### Issue 5: Docker Build Fails

```bash
# Clean docker build cache
docker builder prune -a -f

# Rebuild with no cache
docker build --no-cache -f backend/docker/Dockerfile.agent -t rift-agent:latest backend
```

### Issue 6: Nginx 502 Bad Gateway

```bash
# Check if backend is running
pm2 status

# Check nginx error logs
sudo tail -f /var/log/nginx/error.log

# Restart services
pm2 restart rift-backend
sudo systemctl restart nginx
```

---

## 📈 Performance Optimization

### Increase Docker Resources

Edit `/etc/docker/daemon.json`:

```json
{
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "10m",
    "max-file": "3"
  },
  "default-ulimits": {
    "nofile": {
      "Name": "nofile",
      "Hard": 64000,
      "Soft": 64000
    }
  }
}
```

```bash
sudo systemctl restart docker
```

### Enable Swap (if needed)

```bash
# Create 4GB swap file
sudo fallocate -l 4G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile

# Make permanent
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab

# Verify
free -h
```

---

## ✅ Deployment Checklist

- [ ] EC2 instance created and accessible via SSH
- [ ] Python 3.11+ installed
- [ ] Node.js 18+ installed
- [ ] Docker installed and running
- [ ] Repository cloned
- [ ] Docker images built (rift-agent, rift-agent-node)
- [ ] Environment variables configured (.env file)
- [ ] Python dependencies installed
- [ ] Backend started with PM2
- [ ] Security groups configured (ports 22, 80, 443, 8000)
- [ ] Nginx installed and configured
- [ ] SSL certificate obtained (optional)
- [ ] Firewall (UFW) configured
- [ ] System monitoring setup
- [ ] Backup strategy planned

---

## 📞 Quick Commands Reference

```bash
# Backend Management
pm2 status                          # Check status
pm2 logs rift-backend               # View logs
pm2 restart rift-backend            # Restart
pm2 stop rift-backend               # Stop

# Docker Management
docker ps                           # Running containers
docker images                       # List images
docker system df                    # Disk usage
docker system prune -a              # Clean up

# Nginx Management
sudo nginx -t                       # Test config
sudo systemctl reload nginx         # Reload
sudo systemctl restart nginx        # Restart
sudo tail -f /var/log/nginx/error.log  # Error logs

# System Management
free -h                             # Memory usage
df -h                               # Disk usage
htop                                # CPU/Memory monitor
sudo ufw status                     # Firewall status
```

---

## 🎉 Success!

Your RIFT AI DevOps Agent backend is now deployed on EC2!

**Access Points:**
- API: `http://your-domain.com/` or `http://your-ec2-ip/`
- Health Check: `http://your-domain.com/health`
- WebSocket: `ws://your-domain.com/ws/runs/{run_id}`

**Next Steps:**
1. Deploy frontend application
2. Configure CI/CD pipeline
3. Set up monitoring and alerts
4. Configure backups
5. Scale as needed

---

## 📚 Additional Resources

- [FastAPI Deployment](https://fastapi.tiangolo.com/deployment/)
- [Docker Best Practices](https://docs.docker.com/develop/dev-best-practices/)
- [Nginx Documentation](https://nginx.org/en/docs/)
- [PM2 Documentation](https://pm2.keymetrics.io/docs/usage/quick-start/)
- [AWS EC2 Guide](https://docs.aws.amazon.com/ec2/)

---

**Need Help?** Check the troubleshooting section or review the logs for specific error messages.
