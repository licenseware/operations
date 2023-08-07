import logging
import os
import random
import sys
import time
import traceback

from kubernetes import client, config
from kubernetes.client import V1Deployment, V1StatefulSet
from redis import Sentinel


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


redis_password = os.getenv("REDIS_PASSWORD")

redis_sentinel_host = os.getenv("REDIS_SENTINEL_HOST", "localhost")
redis_sentinel_port = int(os.getenv("REDIS_SENTINEL_PORT", "26379"))

redis_master_set = os.getenv("REDIS_MASTER_SET", "mymaster")


def split_or_empty_list(s: str) -> list[str]:
    if s == "":
        return []
    else:
        return s.split(",")


# in the form of "namespace/name"
deployments = split_or_empty_list(os.getenv("DEPLOYMENTS", ""))
statefulsets = split_or_empty_list(os.getenv("STATEFULSETS", ""))

old_master_host = ""

logger = get_logger()


def extract_namespace_and_name(s: str) -> tuple[str, str] | None:
    rv = s.split("/")
    if len(rv) == 2:
        return rv


def force_restart_pods():
    timestamp = str(int(time.time()))
    annotation = {"last-updated": timestamp}

    api_client = client.ApiClient()

    logger.info("Reloading deployments: " + str(deployments))

    for deployment in deployments:
        try:
            ns, name = extract_namespace_and_name(deployment)
        except:
            warn = "Invalid/nonexistent deployment: {deployment}"
            logger.warn(warn)
            continue

        new_deployment: V1Deployment = client.AppsV1Api(
            api_client
        ).read_namespaced_deployment(name, ns)

        new_deployment.spec.template.metadata.annotations = annotation

        client.AppsV1Api(api_client).patch_namespaced_deployment(
            name, ns, new_deployment
        )

        logger.info("Deployment " + deployment + " reloaded")

    logger.info("Reloading statefulsets: " + str(statefulsets))

    for statefulset in statefulsets:
        try:
            ns, name = extract_namespace_and_name(statefulset)
        except:
            warn = "Invalid/nonexistent statefulset: {statefulset}"
            logger.warn(warn)
            continue

        new_statefulset: V1StatefulSet = client.AppsV1Api(
            api_client
        ).read_namespaced_stateful_set(name, ns)

        new_statefulset.spec.template.metadata.annotations = annotation

        client.AppsV1Api(api_client).patch_namespaced_stateful_set(
            name, ns, new_statefulset
        )

        logger.info("Statefulset " + statefulset + " reloaded")


def main(sentinel: Sentinel):
    global old_master_host

    current_master_host = sentinel.discover_master(redis_master_set)[0]
    logger.info("Current master host: " + current_master_host)

    if not old_master_host:
        old_master_host = current_master_host

    elif current_master_host != old_master_host:
        force_restart_pods()

        old_master_host = current_master_host


if __name__ == "__main__":
    logger.info("Starting restarter...")

    sentinel = Sentinel(
        [(redis_sentinel_host, redis_sentinel_port)],
        sentinel_kwargs=dict(password=redis_password),
        socket_timeout=5,
    )
    logger.info("Reading in-cluster config...")
    config.load_incluster_config()

    logger.info("Starting main loop...")
    while True:
        try:
            main(sentinel)
        except KeyboardInterrupt:
            logger.info("Exiting...")
            break
        except:
            traceback.print_exc()
        finally:
            time.sleep(random.randint(5, 10))
