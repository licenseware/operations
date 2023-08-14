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
                client_api.delete_namespaced_pod(pod_name, namespace)
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
    # config.load_incluster_config()
    config.load_kube_config(context="lware-dev-frankfurt")  # TODO: remove

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
