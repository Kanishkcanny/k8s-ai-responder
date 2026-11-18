from kubernetes import client, config

RESTART_THRESHOLD = 1
BAD_REASONS = {"CrashLoopBackOff", "ImagePullBackOff", "ErrImagePull", "OOMKilled", "Error"}


def find_unhealthy_pods(v1):
    problems = []
    pods = v1.list_pod_for_all_namespaces().items
    for pod in pods:
        if pod.metadata.namespace == "kube-system":
            continue
        for cs in pod.status.container_statuses or []:
            reason = None
            if cs.state.waiting and cs.state.waiting.reason in BAD_REASONS:
                reason = cs.state.waiting.reason
            elif cs.state.terminated and cs.state.terminated.reason in BAD_REASONS:
                reason = cs.state.terminated.reason
            elif cs.restart_count >= RESTART_THRESHOLD and not cs.ready:
                reason = "Restarting"
            if reason:
                problems.append({
                    "namespace": pod.metadata.namespace,
                    "pod": pod.metadata.name,
                    "container": cs.name,
                    "reason": reason,
                    "restarts": cs.restart_count,
                })
    return problems


def collect_evidence(v1, problem):
    ns, name = problem["namespace"], problem["pod"]

    # 1. Collect container logs
    logs = None
    for previous in (True, False):
        try:
            logs = v1.read_namespaced_pod_log(
                name,
                ns,
                container=problem["container"],
                tail_lines=50,
                previous=previous,
            )
            if logs:
                break
        except Exception:
            continue

    if not logs:
        logs = "(no logs available)"

    # 2. Read pod details
    pod = v1.read_namespaced_pod(name, ns)

    # 3. Collect container configuration
    container_spec = next(
        (
            c for c in pod.spec.containers
            if c.name == problem["container"]
        ),
        None,
    )

    if container_spec:
        container_config = {
            "image": container_spec.image,
            "command": container_spec.command or [],
            "args": container_spec.args or [],
        }
    else:
        container_config = {
            "image": "unknown",
            "command": [],
            "args": [],
        }

    # 4. Collect previous termination details
    exit_info = ""
    for cs in pod.status.container_statuses or []:
        t = cs.last_state.terminated
        if cs.name == problem["container"] and t:
            exit_info = (
                f"Last exit code: {t.exit_code}, "
                f"reason: {t.reason}"
            )

    # 5. Collect Kubernetes events
    events = v1.list_namespaced_event(
        ns,
        field_selector=f"involvedObject.name={name}",
    )

    all_lines = [
        f"{e.type} {e.reason}: {e.message}"
        for e in events.items
    ]

    useful = [
        line for line in all_lines
        if not line.startswith("Normal Pulled")
    ]

    event_lines = (useful or all_lines)[-10:]

    # 6. Return complete incident evidence
    return {
        "logs": logs,
        "exit_info": exit_info,
        "events": event_lines,
        "container_config": container_config,
    }


def main():
    config.load_kube_config()
    v1 = client.CoreV1Api()
    problems = find_unhealthy_pods(v1)
    if not problems:
        print("All pods healthy.")
        return
    for p in problems:
        print(f"\n=== PROBLEM: {p['namespace']}/{p['pod']} -> {p['reason']} (restarts: {p['restarts']})")
        evidence = collect_evidence(v1, p)
        print("--- logs ---")
        print(evidence["logs"])
        print("--- exit info ---")
        print(evidence["exit_info"])
        print("--- events ---")
        print("\n".join(evidence["events"]))
        print("--- container config ---")
        print(evidence["container_config"])

if __name__ == "__main__":
    main()