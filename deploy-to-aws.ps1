# Deploy RAG Project to AWS App Runner
param(
    [string]$Region = "ap-south-1",
    [string]$RepoName = "rag-project-1",
    [string]$ServiceName = "rag-project-service",
    [string]$GroqApiKey = $env:GROQ_API_KEY
)

$ErrorActionPreference = "Stop"

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "  RAG Application AWS Deployment Script   " -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan

# 1. Check AWS credentials
Write-Host "[1/6] Validating AWS Credentials..." -ForegroundColor Yellow
try {
    $callerIdentity = uv run --with boto3 python -c "import boto3, json; sts = boto3.client('sts', region_name='$Region'); print(json.dumps(sts.get_caller_identity()))" | ConvertFrom-Json
    $AccountId = $callerIdentity.Account
    Write-Host "Authenticated as Account: $AccountId ($($callerIdentity.Arn))" -ForegroundColor Green
} catch {
    Write-Error "Failed to authenticate with AWS. Please run 'aws configure' or set active AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY in your environment."
    exit 1
}

# 2. Check Groq API Key
if (-not $GroqApiKey) {
    if (Test-Path ".env") {
        $envMatch = Get-Content ".env" | Select-String -Pattern "^GRO[KQ]_API_KEY=(.+)$"
        if ($envMatch) {
            $GroqApiKey = $envMatch.Matches[0].Groups[1].Value.Trim()
        }
    }
}
if (-not $GroqApiKey) {
    Write-Warning "GROQ_API_KEY not found in environment or .env. You will need to configure it in AWS App Runner console."
}

# 3. Create or Get ECR Repository
$EcrUri = "$AccountId.dkr.ecr.$Region.amazonaws.com/$RepoName"
Write-Host "[2/6] Ensuring ECR Repository '$RepoName' exists..." -ForegroundColor Yellow
uv run --with boto3 python -c "
import boto3
ecr = boto3.client('ecr', region_name='$Region')
try:
    ecr.create_repository(repositoryName='$RepoName', imageScanningConfiguration={'scanOnPush': True})
    print('Created repository $RepoName')
except ecr.exceptions.RepositoryAlreadyExistsException:
    print('Repository $RepoName already exists')
"

# 4. Authenticate Docker to ECR
Write-Host "[3/6] Authenticating Docker to Amazon ECR..." -ForegroundColor Yellow
$loginToken = uv run --with boto3 python -c "
import boto3, base64
ecr = boto3.client('ecr', region_name='$Region')
auth = ecr.get_authorization_token()
token = base64.b64decode(auth['authorizationData'][0]['authorizationToken']).decode('utf-8')
password = token.split(':')[1]
print(password)
"
$loginToken | docker login --username AWS --password-stdin "$AccountId.dkr.ecr.$Region.amazonaws.com"

# 5. Build and Push Container Image
Write-Host "[4/6] Building Docker Image..." -ForegroundColor Yellow
docker build -t "$RepoName`:latest" .
docker tag "$RepoName`:latest" "$EcrUri`:latest"

Write-Host "[5/6] Pushing Image to ECR ($EcrUri:latest)..." -ForegroundColor Yellow
docker push "$EcrUri`:latest"

# 6. Deploy or Update AWS App Runner
Write-Host "[6/6] Configuring AWS App Runner Service..." -ForegroundColor Yellow
uv run --with boto3 python -c "
import boto3, sys

apprunner = boto3.client('apprunner', region_name='$Region')
iam = boto3.client('iam')

# Ensure ECR access role exists for App Runner
role_name = 'AppRunnerECRAccessRole'
trust_policy = '''{
  \"Version\": \"2012-10-17\",
  \"Statement\": [
    {
      \"Effect\": \"Allow\",
      \"Principal\": { \"Service\": \"build.apprunner.amazonaws.com\" },
      \"Action\": \"sts:AssumeRole\"
    }
  ]
}'''

try:
    iam.create_role(RoleName=role_name, AssumeRolePolicyDocument=trust_policy)
    iam.attach_role_policy(RoleName=role_name, PolicyArn='arn:aws:iam::aws:policy/service-role/AWSAppRunnerServicePolicyForECRAccess')
    print('Created AppRunnerECRAccessRole')
except iam.exceptions.EntityAlreadyExistsException:
    pass

role_arn = iam.get_role(RoleName=role_name)['Role']['Arn']

# Check if App Runner service already exists
services = apprunner.list_services()
existing = [s for s in services.get('ServiceSummaryList', []) if s['ServiceName'] == '$ServiceName']

env_vars = {'PORT': '8000'}
if '$GroqApiKey':
    env_vars['GROQ_API_KEY'] = '$GroqApiKey'

if existing:
    service_arn = existing[0]['ServiceArn']
    print(f'Updating existing App Runner service: {service_arn}')
    apprunner.start_deployment(ServiceArn=service_arn)
    print('Deployment triggered!')
else:
    print(f'Creating new App Runner service: $ServiceName...')
    resp = apprunner.create_service(
        ServiceName='$ServiceName',
        SourceConfiguration={
            'ImageRepository': {
                'ImageIdentifier': '$EcrUri:latest',
                'ImageConfiguration': {
                    'Port': '8000',
                    'RuntimeEnvironmentVariables': env_vars
                },
                'ImageRepositoryType': 'ECR'
            },
            'AuthenticationConfiguration': {
                'AccessRoleArn': role_arn
            },
            'AutoDeploymentsEnabled': True
        },
        InstanceConfiguration={
            'Cpu': '1024',
            'Memory': '2048'
        }
    )
    service_url = resp['Service'].get('ServiceUrl', 'pending')
    print(f'Service creation initiated! Service URL: https://{service_url}')
"

Write-Host "`nDeployment process completed successfully!" -ForegroundColor Green
