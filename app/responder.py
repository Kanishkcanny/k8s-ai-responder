import os

from dotenv import load_dotenv
from google import genai
from kubernetes import client, config

from watcher import collect_evidence, find_unhealthy_pods

load_dotenv()
MODEL = os.getenv("GEMINI_MODEL", "gemini-3.5-flash")

PROMPT = """You are an expert Kubernetes SRE helping an on-call engineer.
Below is evidence from a failing pod. Respond in this format:

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
    response = ai.models.generate_content(model=MODEL, contents=prompt)
    return response.text


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