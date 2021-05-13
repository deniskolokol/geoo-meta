"""SemExp Feed settings."""

import os
from logging import config


DEVELOPER = "Denis Kolokol"
PROJECT_TITLE = "GEOO: GEOparser - One of many..."
PROJECT_DOMAIN = os.environ.get("PROJECT_DOMAIN", "geoo.com")
PROJECT_MOTTO = "Just another geo-parser which pins the right place on a map"
SSL_ENABLED = bool(int(os.environ.get("SSL_ENABLED", 0)))
if SSL_ENABLED:
    PROJECT_URL = "https://{}/".format(PROJECT_DOMAIN)
else:
    PROJECT_URL = "http://{}/".format(PROJECT_DOMAIN)


# Project base directory
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# Printing
_, COLUMNS = os.popen('stty size', 'r').read().split()
COLUMNS = int(COLUMNS) - 2 # leave 2 spaces on the right.


def __rel(*x):
    """Relative paths inside project directory."""
    return os.path.join(BASE_DIR, *x)


def __ensure_dir(path):
    directory = os.path.dirname(path)
    if not os.path.exists(directory):
        os.makedirs(directory)

    return path


def __frame_print(*inputs, **kwargs):
    """
    Frame printable lines (useful for headers).
    If no inputs provided, simply prints a line
    and exists (useful for summaries).
    """
    print("-" * COLUMNS)
    if not inputs:
        return

    align = kwargs.get("align", "center")
    if align not in ("center", "left", "right"):
        align = "center"

    inside = COLUMNS - 2
    for line in inputs:
        if align == "center":
            print('|{1:^{0}}|'.format(inside, line))
        elif align == "left":
            print('|{1:<{0}}|'.format(inside, line))
        else:
            print('|{1:>{0}}|'.format(inside, line))
    print("-" * COLUMNS)


# Logging is pure console
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "default": {
            "format": "[%(asctime)s %(levelname)s] %(message)s",
            "datefmt": "%Y-%m-%d %H:%M:%S %z",
        },
        "verbose": {
            "format" : "[%(asctime)s %(levelname)s] [%(module)s:%(funcName)s @%(lineno)s] %(message)s",
            "datefmt" : "%Y-%m-%d %H:%M:%S %z",
        },

    },
    "handlers": {
        "console": {
            "level": "DEBUG",
            "class": "logging.StreamHandler",
            "formatter": "default",
        },
        "console_ver": {
            "level": "DEBUG",
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        }
    },
    "loggers": {
        "root": {
            "handlers": ["console"],
            "level": "DEBUG",
            "propagate": True,
        },
        "dev": {
            "handlers": ["console_ver"],
            "level": "DEBUG",
            "propagate": True,
        },
        "request": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": True,
        },
        "test": {
            "handlers": ["console"],
            "level": "WARNING",
            "propagate": False,
        }
    }
}
config.dictConfig(LOGGING)
LOGGER = os.environ.get("LOGGER", "root")

LANG_DEFAULT = "en"
TIME_ZONE = os.environ.get("TIME_ZONE", "UTC")

DOWNLOAD_DIR = __rel('downloads')
if not os.path.exists(DOWNLOAD_DIR):
    os.makedirs(DOWNLOAD_DIR)

# Separate connection reports.
__frame_print("Connections")

# Elasticsearch
from elasticsearch import Elasticsearch
from elasticsearch_dsl.connections import connections as elastic_connections

ES_ALIAS = os.environ.get("ES_ALIAS", "default")
ES_INDEX_LOC = os.environ.get("ES_INDEX_LOC", "geoo")
ES_INDEX_ADM = os.environ.get("ES_INDEX_ADM", "gadm")
ES_SHARDS = os.environ.get("ES_SHARDS", 1)
ES_REPLICAS = os.environ.get("ES_REPLICAS", 0)
ES_HOST = os.environ.get("ES_HOST", "127.0.0.1")
ES_PORT = int(os.environ.get("ES_PORT", 9200))
ES_HTTP_AUTH = os.environ.get("ES_CREDENTIALS", "").split(":")
ES_MAIN_TIMESTAMP_FIELD = "last_updated"
ES_ADM_TIMESTAMP_FIELD = "created_at"
ES_MAX_RESULTS = 5000
ES_CONN = {
    "port": ES_PORT,
    "http_auth": ES_HTTP_AUTH,
    "timeout": 30,
    "max_retries": 10,
    "retry_on_timeout": True
    }
ES_CLIENT = Elasticsearch([ES_HOST], **ES_CONN)
elastic_connections.add_connection(alias=ES_ALIAS, conn=ES_CLIENT)
print("\n[>] Elasticsearch: {}:{}".format(ES_HOST, ES_PORT))
print("Alias: {}".format(ES_ALIAS))
print("Indices: {}, {}".format(ES_INDEX_LOC, ES_INDEX_ADM))

__frame_print()
# Separate connection reports - END.
