import logging
import os
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
        client.BatchV1Api().delete_namespaced_job(parent.name, pod.metadata.namespace)
        logger_, delete_status = logger.info, "Success"
    except Exception as e:
        logger_, delete_status = logger.error, "Failed"

    logger_(
        f"Job: {parent.name} Namespace: {pod.metadata.namespace} Delete Status: {delete_status}"
    )


def terminate_orphan_pods():
    pods = client.CoreV1Api().list_pod_for_all_namespaces().items

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


def terminate_unfinished_jobs():
    jobs = client.BatchV1Api().list_job_for_all_namespaces().items

    for job in jobs:
        job_name = job.metadata.name
        namespace = job.metadata.namespace

        pods_of_job = (
            client.CoreV1Api()
            .list_namespaced_pod(
                namespace=namespace, label_selector=f"job-name={job_name}"
            )
            .items
        )

        not_active_nor_succeeded = not job.status.active and not job.status.succeeded
        job_has_no_pod = not pods_of_job

        eligible = not_active_nor_succeeded or job_has_no_pod

        if eligible:
            try:
                client.BatchV1Api().delete_namespaced_job(job_name, namespace)
                logger_, delete_status = logger.info, "Success"
            except Exception as e:
                logger_, delete_status = logger.error, "Failed"

            logger_(
                f"Job: {job_name} Namespace: {namespace} Delete Status: {delete_status}"
            )
        else:
            logger.debug(f"Job: {job_name} Namespace: {namespace} Not Eligible")


LEVEL = os.environ.get("LOG_LEVEL", "INFO").upper()
INTERVAL = int(os.environ.get("INTERVAL", 60))
logger = get_logger(level=LEVEL)

if __name__ == "__main__":
    config.load_incluster_config()

    while True:
        try:
            terminate_unfinished_jobs()
            terminate_orphan_pods()
        except KeyboardInterrupt:
            logger.info("Exiting...")
            break
        except:
            logger.error(traceback.format_exc())

        logger.info(f"Sleeping for {INTERVAL} seconds...")
        time.sleep(INTERVAL)
