import os
import time

from dotenv import load_dotenv
from google import genai
from google.genai import errors
from kubernetes import client, config

from watcher import collect_evidence, find_unhealthy_pods

load_dotenv()

PRIMARY_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.8-flash")
FALLBACK_MODELS = [
    m.strip()
    for m in os.getenv("GEMINI_FALLBACK_MODELS", "gemini-3.5-flash").split(",")
    if m.strip()
]
MODELS = [PRIMARY_MODEL] + FALLBACK_MODELS
RETRIES = 3

PROMPT = """You are an expert Kubernetes SRE helping an on-call engineer.

You are analyzing evidence from an unhealthy Kubernetes pod.

Rules:
- Prioritize container configuration, logs and exit codes.
- Use Kubernetes events as supporting evidence.
- Identify the configured image, command and arguments.
- Distinguish confirmed facts from possible causes.
- Never invent a root cause that evidence does not support.
- Exit code 0 means successful process termination.
- Non-zero exit codes indicate unsuccessful termination.
- If the command explicitly contains exit 1, identify it as a direct cause.
- Do not recommend restarting a container if its command will fail again.
- Never execute remediation commands automatically.
Incident details:

Namespace: {namespace}
Pod: {pod}
Container: {container}
Status: {reason}
Restarts: {restarts}

Previous termination:
{exit_info}

Container configuration:
{container_config}

Container logs:
{logs}

Kubernetes events:
{events}


Return ONLY valid JSON. Do not use Markdown code fences.

Use this exact JSON structure:

{{
    "severity": "CRITICAL / HIGH / MEDIUM / LOW",
    "root_cause": "Explain the confirmed root cause.",
    "evidence": [
        "Exact evidence from Kubernetes"
    ],
    "confidence": "HIGH / MEDIUM / LOW",
    "remediation_steps": [
        "First troubleshooting step",
        "Second troubleshooting step"
    ],
    "safe_to_auto_restart": false,
    "restart_reason": "Explain whether restarting is safe."
}}

Rules:
- Severity must reflect the actual incident impact.
- Evidence must come from the supplied data.
- Never invent missing evidence.
- Remediation steps must be actionable.
- Never execute remediation commands.
- safe_to_auto_restart must be a boolean.
- If evidence is insufficient, say so.
- Return valid JSON only.

"""



def call_model(ai, model, prompt):
    for attempt in range(1, RETRIES + 1):
        try:
            return ai.models.generate_content(model=model, contents=prompt).text
        except errors.APIError as e:
            code = getattr(e, "code", None)
            if code in (429, 500, 503) and attempt < RETRIES:
                wait = 2 ** attempt * 2
                print(f"  [{model}] busy ({code}), retry {attempt}/{RETRIES - 1} in {wait}s...")
                time.sleep(wait)
                continue
            raise


def diagnose(problem, evidence):
    prompt = PROMPT.format(
        namespace=problem["namespace"],
        pod=problem["pod"],
        container=problem["container"],
        reason=problem["reason"],
        restarts=problem["restarts"],
        exit_info=evidence["exit_info"],
        logs=evidence["logs"][-3000:],
        events="\n".join(evidence["events"]),
        container_config=evidence.get("container_config", {}),
    )
    ai = genai.Client()
    for model in MODELS:
        try:
            return f"(model: {model})\n" + call_model(ai, model, prompt)
        except errors.APIError as e:
            print(f"  [{model}] failed ({getattr(e, 'code', '?')}), trying next model...")
    return "AI diagnosis unavailable right now. Raw evidence was collected; check logs and events manually."


def main():
    config.load_kube_config()
    v1 = client.CoreV1Api()
    problems = find_unhealthy_pods(v1)
    if not problems:
        print("All pods healthy.")
        return
    for p in problems:
        print(f"\n=== {p['namespace']}/{p['pod']} -> {p['reason']}")
        evidence = collect_evidence(v1, p)
        print(diagnose(p, evidence))


if __name__ == "__main__":
    main()