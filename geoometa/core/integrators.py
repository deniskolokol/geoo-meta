# -*- coding: utf-8 -*-

"""Integration with other services."""

import re
import os
import glob
import json
import time
import urllib
import shutil
import zipfile
import logging

from genery.utils import RecordDict, URLNormalizer, \
     ensure_list, runcmd, as_file

from conf import settings
from core.exceptions import MissingDataError, UnsupportedValueError
from core.utils import read_github, format_error
from schema import elastic


LOG = logging.getLogger(settings.LOGGER)
USER = "whosonfirst-data"
TIMEOUT = 30
ZIP_CONTENT_TYPE = [
    "application/zip",
    "application/x-zip-compressed",
    "application/octet-stream"
    ]


def process_tree(path):
    data = []
    for filename in glob.iglob(path + '**/**/*.geojson', recursive=True):
        with open(filename, "r") as fp:
            try:
                geojson = json.load(fp)
            except Exception as exc:
                LOG.error(format_error(exc))
            else:
                if isinstance(geojson, list):
                    data.extend(geojson)
                else:
                    data.append(geojson)
                LOG.debug("processed %s", filename)
            fp.close()

    return data


def process_repo(url, filename=None):
    """
    - downloads from `url`
    - unZIPs inside `settings.DOWNLOAD_DIR`
    - recoursively processes directory tree
    - cleans up downloaded file and extracted directory
    - returns deserialized data
    """
    if not filename:
        filename = filename.split("/")[-1]

    path_zipfile = os.path.join(settings.DOWNLOAD_DIR, filename)
    path_dir = os.path.join(settings.DOWNLOAD_DIR, filename.rsplit(".", 1)[0])

    LOG.debug("Downloading from %s", url)
    urllib.request.urlretrieve(url, path_zipfile)

    LOG.debug("Unzipping to %s", path_dir)
    with zipfile.ZipFile(path_zipfile, "r") as fp:
        fp.extractall(path_dir)

    data = process_tree(path_dir)

    # Cleanup.
    LOG.debug("Cleaning up %s & %s", path_zipfile, path_dir)
    os.remove(path_zipfile)
    try:
        shutil.rmtree(path_dir)
    except OSError as err:
        LOG.error("Cannot delete %s - Error %s", path_dir, err.strerror)

    return data


class GazetteerCollector:
    html_url = "html_url"

    def __init__(self, user, **kwargs):
        """
        :param user: github user to obtain data from (default USER).
        :kwargs patterns: <list>
            repository names patterns to match (e.g.
            r'^.+\/whosonfirst-data-admin-[a-z]+')
        :kwargs repos: <list>
            If repo URLs are known in advance, they should be
            provided here to speed up the processing by avoiding
            the step of collecting the URLs.
            Warning! This will still be matched against patterns
            (if provided)!
        :kwargs wait: <int> seconds after processing one repo
            (necessary only when processing huge amount of repos).
        """
        self.user = user or USER
        self.errors = []
        self.init_stat()
        self.repos_url = "https://api.github.com/users/{}/repos".format(self.user)

        patterns = kwargs.pop("patterns", None)
        if patterns:
            kwargs.update({"patterns": ensure_list(patterns)})
        kwargs["wait"] = kwargs.get("wait", 0)
        self.params = RecordDict(**kwargs)
        self.repos = self.collect_repos()

    def _validate_url__match(self, url):
        try:
            return any(re.match(p, url) for p in self.params.patterns)
        except (AttributeError, KeyError):
            # No patterns defined, everything is accepted.
            return True

    def _validate_repo__pushed(self, repo):
        #TODO: add "modified_after" condition here
        # return repo["pushed_at"] >= self.pushed_after
        return True

    def clean(self, record):
        """Used for re-formatting, deleting unnecessary keys, etc."""
        return record

    def _validate_repo(self, record):
        """
        :param record: <dict>
        :return: <bool>
        """
        if not isinstance(record, dict):
            self.errors.append('Repository record should be <dict>!\n{}'\
                               .format(str(record)))
            return False

        try:
            url = record[self.html_url]
        except KeyError:
            self.errors.append("No `{}` found in the record: {}"\
                .format(self.html_url, json.dumps(record, indent=4)))
            return False

        if self._validate_url__match(url):
            return self.clean(record)

        #TODO: add "modified_after" condition here
        # if repo["pushed_at"] <= self.pushed_after:
        #     continue

        return False

    def collect_repos(self):
        repos_raw = self.params.get("repos", [])
        if repos_raw:
            assert isinstance(repos_raw, list),\
                UnsupportedValueError(
                    "Keyword argument `repos` should be of the type <list>! Currently: <{}>"\
                    .format(type(repos_raw).__name__))
        else:
            repos_raw = read_github(self.repos_url)

        repos = []
        for repo in repos_raw:
            validated = self._validate_repo(repo)
            if validated:
                repos.append(validated)

        return repos

    def ensure_repos(self):
        if not self.repos:
            self.repos = self.collect_repos()

    def init_stat(self):
        self.stat = RecordDict(errors=[], success=[])

    def register(self, data, stat=None):
        if isinstance(data, dict):
            data = [data]

        for feature in data:
            type_ = feature.get("type", "")
            if type_.lower() != "feature":
                msg = "Only records of the type 'feature' are supported (currently: {})\n{}"\
                    .format(type_, json.dumps(feature, indent=4))
                msg = format_error(UnsupportedValueError(msg))
                LOG.error(msg)
                self.stat.errors.append(msg)
                continue

            try:
                place = elastic.Place(meta={"remap": True}, **feature)
            except KeyError:
                msg = "Record doesn't contain 'properties':\n{}".format(
                    json.dumps(feature, indent=4))
                msg = format_error(MissingDataError(msg))
                LOG.error(msg)
                self.stat.errors.append(msg)
                continue

            except MissingDataError as exc:
                msg = format_error(exc)
                LOG.error(msg)
                self.stat.errors.append(msg)
                continue

            try:
                place.save()
            except Exception as exc:
                msg = format_error(exc)
                LOG.error(msg)
                self.stat.errors.append(msg)
            else:
                LOG.debug("Indexed: %s", place.meta["id"])
                self.stat.success.append(place.meta["id"])

    def process(self):
        self.ensure_repos()
        self.init_stat()
        elastic.setup()
        for record in self.repos:
            LOG.debug("Processing %s", record["name"])
            url_zip = record[self.html_url]
            if not url_zip.endswith("/"):
                url_zip += "/"
            url_zip += "archive/refs/heads/{}.zip".format(
                record["default_branch"])
            fname = record["name"] + ".zip"
            data = process_repo(url_zip, fname)
            self.register(data)

            # Wait if necessary...
            time.sleep(self.params.wait)

        LOG.debug("Done.\n\tTotal indexed: %d", len(self.stat.success))
        if self.stat.errors:
            LOG.debug("\tTotal errors: %d", len(self.stat.errors))
