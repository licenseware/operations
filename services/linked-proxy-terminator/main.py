import logging
import sys
import time
import traceback

from kubernetes import client, config


def get_logger(name=__name__, level="INFO"):
    logger = logging.getLogger(name)
    logger.setLevel(level)
    handler = logging.StreamHandler(sys.stdout)
    sharp = "#" * 80
    formatter = logging.Formatter(
        sharp
        + "\n[%(levelname)s] %(asctime)s (%(pathname)s:%(lineno)d): \n%(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    return logger


def remove_parent_of_pod(pod: client.V1Pod):
    if not pod.metadata.owner_references:
        logger.debug(f"Pod: {pod.metadata.name} has no owner")
        return

    parent = pod.metadata.owner_references[0]
    if parent.kind != "Job":
        logger.debug(f"Pod: {pod.metadata.name} has no Job parent")
        return

    try:
        client_api = client.BatchV1Api()
        client_api.delete_namespaced_job(parent.name, pod.metadata.namespace)
        logger_, delete_status = logger.info, "Success"
    except Exception as e:
        logger_, delete_status = logger.error, "Failed"

    logger_(
        f"Job: {parent.name} Namespace: {pod.metadata.namespace} Delete Status: {delete_status}"
    )


def main():
    client_api = client.CoreV1Api()

    pods = client_api.list_pod_for_all_namespaces().items

    for pod in pods:
        pod_name = pod.metadata.name
        namespace = pod.metadata.namespace

        container_statuses = {
            container.name: container.ready
            for container in pod.status.container_statuses
        }
        proxy_running = container_statuses.pop("linkerd-proxy", False)
        only_proxy = proxy_running and not any(container_statuses.values())

        if only_proxy:
            try:
                remove_parent_of_pod(pod)
                logger_, delete_status = logger.info, "Success"
            except Exception as e:
                logger_, delete_status = logger.error, "Failed"
        else:
            logger_, delete_status = logger.debug, "Not Eligible"

        logger_(
            f"Pod: {pod_name} Namespace: {namespace} Delete Status: {delete_status}"
        )


logger = get_logger()

if __name__ == "__main__":
    config.load_incluster_config()

    while True:
        try:
            main()
        except KeyboardInterrupt:
            logger.info("Exiting...")
            break
        except:
            logger.error(traceback.format_exc())

        logger.info("Sleeping for 60 seconds...")
        time.sleep(60)
