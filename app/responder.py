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
Below is evidence from a failing pod.

Rules:
- Weigh the container logs and the exit code first. Events are secondary.
- Do not guess causes the evidence does not show.
- If the logs show the app exited on its own, say so.

Respond in this format:

ROOT CAUSE: one or two sentences
CONFIDENCE: low / medium / high
FIX: numbered steps, with kubectl commands where useful
SAFE TO AUTO-RESTART: yes / no, with a short reason

Pod: {namespace}/{pod} (container: {container})
Status: {reason}, restarts: {restarts}
{exit_info}

Logs (last lines):
{logs}

Events:
{events}
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