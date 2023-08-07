import logging
import os
import random
import re
import sys
import time
import traceback

from kubernetes import client, config
from kubernetes.client import V1Deployment, V1StatefulSet, exceptions
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

all_deployment_namespaces = split_or_empty_list(os.getenv("ALL_DEPLOYMENTS_IN", ""))
all_deployment_regex = os.getenv("ALL_DEPLOYMENTS_REGEX", "")
all_statefulset_namespaces = split_or_empty_list(os.getenv("ALL_STATEFULSETS_IN", ""))
all_statefulset_regex = os.getenv("ALL_STATEFULSETS_REGEX", "")

old_master_host = ""

logger = get_logger()


def extract_namespace_and_name(s: str) -> tuple[str, str] | None:
    rv = s.split("/")
    if len(rv) == 2:
        return rv


def get_all_deployments(namespace):
    api_client = client.ApiClient()

    return client.AppsV1Api(api_client).list_namespaced_deployment(namespace)


def get_all_statefulsets(namespace):
    api_client = client.ApiClient()

    return client.AppsV1Api(api_client).list_namespaced_stateful_set(namespace)


def annotate_pod_in_deployment(deployment_name, namespace):
    timestamp = str(int(time.time()))
    annotation = {"last-updated": timestamp}

    api_client = client.ApiClient()

    try:
        new_deployment: V1Deployment = client.AppsV1Api(
            api_client
        ).read_namespaced_deployment(deployment_name, namespace)
    except exceptions.ApiException as exp:
        if exp.status == 404:
            logger.warn(f"Deployment not found: {deployment_name}")
            return
        raise exp

    new_deployment.spec.template.metadata.annotations = annotation

    client.AppsV1Api(api_client).patch_namespaced_deployment(
        deployment_name, namespace, new_deployment
    )


def annotate_pod_in_statefulset(statefulset_name, namespace):
    timestamp = str(int(time.time()))
    annotation = {"last-updated": timestamp}

    api_client = client.ApiClient()

    try:
        new_statefulset: V1StatefulSet = client.AppsV1Api(
            api_client
        ).read_namespaced_stateful_set(statefulset_name, namespace)
    except exceptions.ApiException as exp:
        if exp.status == 404:
            logger.warn(f"Statefulset not found: {statefulset_name}")
            return
        raise exp

    new_statefulset.spec.template.metadata.annotations = annotation

    client.AppsV1Api(api_client).patch_namespaced_stateful_set(
        statefulset_name, namespace, new_statefulset
    )


def restart_static_resources():
    logger.info("Reloading deployments: " + str(deployments))

    for deployment in deployments:
        try:
            ns, name = extract_namespace_and_name(deployment)
        except:
            warn = f"Invalid/nonexistent deployment: {deployment}"
            logger.warn(warn)
            continue

        annotate_pod_in_deployment(name, ns)

        logger.info("Deployment " + deployment + " reloaded")

    logger.info("Reloading statefulsets: " + str(statefulsets))

    for statefulset in statefulsets:
        try:
            ns, name = extract_namespace_and_name(statefulset)
        except:
            warn = f"Invalid/nonexistent statefulset: {statefulset}"
            logger.warn(warn)
            continue

        annotate_pod_in_statefulset(name, ns)

        logger.info("Statefulset " + statefulset + " reloaded")


def resource_name_contains(resource_name: str, regex: str) -> bool:
    return re.search(regex, resource_name) is not None


def restart_dynamic_resources():
    for ns in all_deployment_namespaces:
        for deployment in get_all_deployments(ns).items:
            resource_name = deployment.metadata.name

            if all_deployment_regex and not resource_name_contains(
                resource_name, all_deployment_regex
            ):
                continue

            annotate_pod_in_deployment(deployment.metadata.name, ns)

            logger.info("Deployment " + deployment.metadata.name + " reloaded")

    for ns in all_statefulset_namespaces:
        for statefulset in get_all_statefulsets(ns).items:
            resource_name = statefulset.metadata.name

            if all_statefulset_regex and not resource_name_contains(
                resource_name, all_statefulset_regex
            ):
                continue

            annotate_pod_in_statefulset(statefulset.metadata.name, ns)

            logger.info("Statefulset " + statefulset.metadata.name + " reloaded")


def main(sentinel: Sentinel):
    global old_master_host

    current_master_host = sentinel.discover_master(redis_master_set)[0]
    logger.info("Current master host: " + current_master_host)

    if not old_master_host:
        old_master_host = current_master_host

    elif current_master_host != old_master_host:
        restart_static_resources()
        restart_dynamic_resources()

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
