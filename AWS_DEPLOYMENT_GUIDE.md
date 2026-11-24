# AWS Deployment Guide for RAG Project

This project contains a **FastAPI backend**, an in-memory/local embedding and reranking pipeline (`sentence-transformers` + `CrossEncoder`), persistent ChromaDB vector store, file upload management, and a static Web frontend.

---

## 1. Configured AWS MCP Servers

The following AWS Model Context Protocol (MCP) servers have been installed and configured in your global Antigravity config (`~/.gemini/config/mcp_config.json`):

1. **`aws-docs`** (`awslabs.aws-documentation-mcp-server`):
   - Real-time search and retrieval of official AWS documentation, best practices, and architecture guidelines.
   - Works immediately without credentials.

2. **`aws-api`** (`awslabs.aws-api-mcp-server`):
   - Allows AI models to inspect and execute AWS API operations directly using your configured IAM credentials or active AWS profile.

---

## 2. Setting Up / Refreshing AWS Credentials

Your existing AWS credentials in `~/.aws/credentials` returned an `InvalidClientTokenId` error (expired or inactive token).

To update them:

### Option A: Edit `~/.aws/credentials` directly
Open `C:\Users\rehan\.aws\credentials` and update:
```ini
[default]
aws_access_key_id = YOUR_NEW_ACCESS_KEY_ID
aws_secret_access_key = YOUR_NEW_SECRET_ACCESS_KEY
```

And in `C:\Users\rehan\.aws\config`:
```ini
[default]
region = ap-south-1
output = json
```

### Option B: Set via Environment Variables
In your terminal or PowerShell session:
```powershell
$env:AWS_ACCESS_KEY_ID="YOUR_ACCESS_KEY_ID"
$env:AWS_SECRET_ACCESS_KEY="YOUR_SECRET_ACCESS_KEY"
$env:AWS_DEFAULT_REGION="ap-south-1"
```

---

## 3. Deployment Options

### Recommended: AWS App Runner (Serverless Container)
AWS App Runner is the optimal choice for this FastAPI RAG application:
- **Fully Managed**: Automatic HTTPS endpoint, zero server patching, auto-scaling.
- **Cost Effective**: Automatically scales to minimum instances when idle.
- **Containerized**: Runs the container image built from `Dockerfile` with all PyTorch & HuggingFace models pre-baked.

#### One-Click Deployment Script
Once Docker Desktop is open and your AWS credentials are valid, run:
```powershell
.\deploy-to-aws.ps1
```
The script automatically:
1. Validates your AWS IAM credentials.
2. Creates an Amazon ECR repository (`rag-project-1`).
3. Authenticates Docker to your ECR registry.
4. Builds the production image with pre-cached models (`all-MiniLM-L6-v2` & `ms-marco-MiniLM-L-6-v2`).
5. Pushes the image to Amazon ECR.
6. Deploys or updates the **AWS App Runner** service with your `GROQ_API_KEY` and outputs your public `https://...` URL.

---

### Alternative: AWS EC2 (Single VM with Docker or systemd)
If you require long-lived disk persistence for ChromaDB and uploaded files without using AWS EFS:
1. Launch an `Ubuntu 24.04 LTS` instance (recommended: `t3.medium` or `t3.large` with 20GB+ gp3 EBS).
2. SSH into your instance:
   ```bash
   sudo apt-get update && sudo apt-get install -y docker.io git
   git clone <your-repo-url> rag-project
   cd rag-project
   sudo docker build -t rag-app .
   sudo docker run -d -p 80:8000 \
     -v $(pwd)/uploads:/app/uploads \
     -v $(pwd)/vectorstore:/app/vectorstore \
     -e GROQ_API_KEY="your-groq-key" \
     --name rag-app --restart always rag-app
   ```
3. Your app is accessible directly at `http://<EC2-PUBLIC-IP>/app`.
