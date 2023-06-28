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


deployments = split_or_empty_list(os.getenv("DEPLOYMENTS", ""))
deployment_ns = os.getenv("DEPLOYMENT_NAMESPACE", "default")
statefulsets = split_or_empty_list(os.getenv("STATEFULSETS", ""))
statefulset_ns = os.getenv("STATEFULSET_NAMESPACE", "default")

old_master_host = ""

logger = get_logger()


def force_restart_pods():
    timestamp = str(int(time.time()))
    annotation = {"last-updated": timestamp}

    api_client = client.ApiClient()

    logger.info("Reloading deployments: " + str(deployments))

    for deployment_name in deployments:
        deployment: V1Deployment = client.AppsV1Api(
            api_client
        ).read_namespaced_deployment(deployment_name, deployment_ns)

        deployment.spec.template.metadata.annotations = annotation

        client.AppsV1Api(api_client).patch_namespaced_deployment(
            deployment_name, deployment_ns, deployment
        )

        logger.info("Deployment " + deployment_name + " reloaded")

    logger.info("Reloading statefulsets: " + str(statefulsets))

    for statefulset_name in statefulsets:
        statefulset: V1StatefulSet = client.AppsV1Api(
            api_client
        ).read_namespaced_stateful_set(statefulset_name, statefulset_ns)

        statefulset.spec.template.metadata.annotations = annotation

        client.AppsV1Api(api_client).patch_namespaced_stateful_set(
            statefulset_name, statefulset_ns, statefulset
        )

        logger.info("Statefulset " + statefulset_name + " reloaded")


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
