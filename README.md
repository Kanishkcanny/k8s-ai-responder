# 🚀 K8s AI Responder

### AI-Powered Kubernetes Incident Diagnosis Assistant

K8s AI Responder is a Python-based tool that detects unhealthy Kubernetes pods, collects diagnostic evidence, and uses Google Gemini AI to identify root causes and recommend troubleshooting steps.

The project explores how AI can assist DevOps and Site Reliability Engineering (SRE) teams in investigating Kubernetes incidents.

## 🎯 Key Features

- Detect unhealthy Kubernetes pods across namespaces.
- Collect container logs and exit information.
- Inspect container images, commands and arguments.
- Collect Kubernetes events for additional context.
- Generate AI-powered root-cause analysis.
- Support primary and fallback Gemini models.
- Produce structured JSON diagnostic reports.
- Recommend corrective actions.
- Evaluate whether restarting a container is safe.
- No automatic remediation or cluster modifications.

## 🏗️ Architecture

The application uses a Python-based diagnostic workflow integrated with the Kubernetes API and Google Gemini AI.

See [ARCHITECTURE.md](ARCHITECTURE.md) for the system architecture and workflow diagram.

## 🛠️ Technology Stack

| Technology | Purpose |
|---|---|
| Python 3.12 | Application development |
| Kubernetes | Container orchestration |
| Kubernetes Python Client | Cluster API communication |
| Google Gemini AI | Incident diagnosis |
| Google Gen AI SDK | AI integration |
| Docker Desktop | Local Kubernetes environment |
| Git & GitHub | Version control |

## 📂 Project Structure

```text
k8s-ai-responder/
│
├── app/
│   ├── responder.py
│   └── watcher.py
│
├── deploy/              # Reserved for deployment manifests
├── docs/                # Reserved for additional documentation
├── tests/               # Reserved for automated tests
│
├── .gitignore
├── requirements.txt
├── README.md
└── ARCHITECTURE.md
```

## ⚙️ Prerequisites

- Python 3.12
- Docker Desktop
- Kubernetes enabled and accessible
- kubectl
- Google Gemini API key
- Git

## 🚀 Installation and Setup

### 1. Clone the repository

```bash
git clone https://github.com/Kanishkcanny/k8s-ai-responder.git

cd k8s-ai-responder
```

### 2. Create a virtual environment

```bash
python3 -m venv .venv

source .venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment variables

Create a `.env` file in the project root.

```env
GOOGLE_API_KEY=your_gemini_api_key

GEMINI_MODEL=your_primary_model

GEMINI_FALLBACK_MODELS=your_fallback_model
```

Never upload your `.env` file or expose your API key on GitHub.

### 5. Verify Kubernetes connectivity

```bash
kubectl get nodes

kubectl get pods -A
```

Make sure your cluster is running and accessible.

### 6. Run the application

```bash
python app/responder.py
```

## 🔍 How It Works

1. Loads Kubernetes configuration.
2. Connects to the Kubernetes API.
3. Identifies unhealthy pods.
4. Collects diagnostic evidence:
   - Container logs
   - Exit codes and termination information
   - Container image and configuration
   - Kubernetes events
5. Builds a diagnostic prompt using the collected evidence.
6. Sends the evidence to the primary Gemini model.
7. Uses a fallback model when supported API errors occur.
8. Generates a structured JSON diagnosis.
9. Displays troubleshooting recommendations.

## 🧪 Practical Test Scenario

The application was tested using a deliberately failing Kubernetes pod.

**Test workload:**

| Property | Value |
|---|---|
| Namespace | default |
| Pod | broken-app |
| Image | busybox |
| Command | sh |
| Arguments | echo starting; exit 1 |
| Exit code | 1 |
| Status | CrashLoopBackOff |

### AI Diagnosis

The AI successfully identified:

- The container explicitly executes `exit 1`.
- The process terminates unsuccessfully with exit code 1.
- Kubernetes repeatedly restarts the failed container.
- Restarting without correcting the container configuration would reproduce the failure.

**Fallback testing:** The primary Gemini model returned HTTP 503. The fallback model successfully generated the diagnosis.

## 🔐 Safety and Reliability

The application follows an evidence-first diagnostic approach.

- Prioritizes container configuration, logs and exit codes.
- Uses Kubernetes events as supporting evidence.
- Distinguishes confirmed facts from possible causes.
- Avoids unsupported root-cause assumptions.
- Does not execute remediation commands automatically.
- Provides a restart safety recommendation.

## 📌 Current Project Status

**Version:** 1.0  
**Status:** Core prototype implemented

### Implemented

- Kubernetes API connectivity
- Unhealthy pod detection
- Diagnostic evidence collection
- Gemini AI integration
- Primary and fallback model handling
- Structured JSON diagnosis
- Remediation recommendations
- Restart safety assessment

### Future Improvements

- Additional Kubernetes failure scenarios.
- Automated unit and integration testing.
- Prometheus metrics integration.
- Grafana monitoring dashboard.
- Slack or email alert integration.
- Web-based incident dashboard.
- CI/CD pipeline.
- Kubernetes deployment manifests.

## 👨‍💻 Author

**Kanishka Bhardwaj**

DevOps | Kubernetes | Linux | Docker | AWS | Terraform

- GitHub: https://github.com/Kanishkcanny
- LinkedIn: https://www.linkedin.com/in/kanishka-bhardwaj-a88a09193/

---

*Built as a hands-on DevOps and SRE project exploring AI-assisted Kubernetes troubleshooting.*
