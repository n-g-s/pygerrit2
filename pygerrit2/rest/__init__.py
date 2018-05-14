# The MIT License
#
# Copyright 2013 Sony Mobile Communications. All rights reserved.
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

""" Interface to the Gerrit REST API. """

import json
import logging
import requests
from six.moves.urllib.parse import urlencode, quote_plus

from requests.auth import HTTPBasicAuth

from pygerrit2.rest.model import GerritChange, GerritProject

GERRIT_MAGIC_JSON_PREFIX = ")]}\'\n"
GERRIT_AUTH_SUFFIX = "/a"


def _decode_response(response):
    """ Strip off Gerrit's magic prefix and decode a response.

    :returns:
        Decoded JSON content as a dict, or raw text if content could not be
        decoded as JSON.

    :raises:
        requests.HTTPError if the response contains an HTTP error status code.

    """
    content = response.content.strip()
    if response.encoding:
        content = content.decode(response.encoding)
    response.raise_for_status()
    content_type = response.headers.get('content-type', '')
    if content_type.split(';')[0] != 'application/json':
        return content
    if content.startswith(GERRIT_MAGIC_JSON_PREFIX):
        content = content[len(GERRIT_MAGIC_JSON_PREFIX):]
    try:
        return json.loads(content)
    except ValueError:
        logging.error('Invalid json content: %s' % content)
        raise


def _merge_dict(result, overrides):
    """ Deep-merge dictionaries.

    :arg dict result: The resulting dictionary
    :arg dict overrides: Dictionay being merged into the result

    :returns:
        The resulting dictionary

    """
    for key in overrides:
        if (
            key in result and
            isinstance(result[key], dict) and
            isinstance(overrides[key], dict)
        ):
            _merge_dict(result[key], overrides[key])
        else:
            result[key] = overrides[key]
    return result


class GerritRestAPI(object):

    """ Interface to the Gerrit REST API.

    :arg str url: The full URL to the server, including the `http(s)://` prefix.
        If `auth` is given, `url` will be automatically adjusted to include
        Gerrit's authentication suffix.
    :arg auth: (optional) Authentication handler.  Must be derived from
        `requests.auth.AuthBase`.
    :arg boolean verify: (optional) Set to False to disable verification of
        SSL certificates.

    """

    def __init__(self, url, auth=None, verify=True):
        headers = {'Accept': 'application/json',
                   'Accept-Encoding': 'gzip'}
        self.kwargs = {'auth': auth,
                       'verify': verify,
                       'headers': headers}
        self.url = url.rstrip('/')
        self.session = requests.session()

        if auth:
            if not isinstance(auth, requests.auth.AuthBase):
                raise ValueError('Invalid auth type; must be derived '
                                 'from requests.auth.AuthBase')

            if not self.url.endswith(GERRIT_AUTH_SUFFIX):
                self.url += GERRIT_AUTH_SUFFIX
        else:
            if self.url.endswith(GERRIT_AUTH_SUFFIX):
                self.url = self.url[: - len(GERRIT_AUTH_SUFFIX)]

        if not self.url.endswith('/'):
            self.url += '/'

    def make_url(self, endpoint):
        """ Make the full url for the endpoint.

        :arg str endpoint: The endpoint.

        :returns:
            The full url.

        """
        endpoint = endpoint.lstrip('/')
        return self.url + endpoint

    def get(self, endpoint, return_response=False, **kwargs):
        """ Send HTTP GET to the endpoint.

        :arg str endpoint: The endpoint to send to.
        :arg bool return_response: If true will also return the response

        :returns:
            JSON decoded result.

        :raises:
            requests.RequestException on timeout or connection error.

        """
        kwargs.update(self.kwargs.copy())
        response = self.session.get(self.make_url(endpoint), **kwargs)

        decoded_response = _decode_response(response)

        if return_response:
            return decoded_response, response
        return decoded_response

    def put(self, endpoint, return_response=False, **kwargs):
        """ Send HTTP PUT to the endpoint.

        :arg str endpoint: The endpoint to send to.

        :returns:
            JSON decoded result.

        :raises:
            requests.RequestException on timeout or connection error.

        """
        args = {}
        if ("data" in kwargs and isinstance(kwargs["data"], dict)) or \
                "json" in kwargs:
            _merge_dict(
                args, {
                    "headers": {
                        "Content-Type": "application/json;charset=UTF-8"
                    }
                }
            )
        _merge_dict(args, self.kwargs.copy())
        _merge_dict(args, kwargs)
        response = self.session.put(self.make_url(endpoint), **args)

        decoded_response = _decode_response(response)

        if return_response:
            return decoded_response, response
        return decoded_response

    def post(self, endpoint, return_response=False, **kwargs):
        """ Send HTTP POST to the endpoint.

        :arg str endpoint: The endpoint to send to.

        :returns:
            JSON decoded result.

        :raises:
            requests.RequestException on timeout or connection error.

        """
        args = {}
        if ("data" in kwargs and isinstance(kwargs["data"], dict)) or \
                "json" in kwargs:
            _merge_dict(
                args, {
                    "headers": {
                        "Content-Type": "application/json;charset=UTF-8"
                    }
                }
            )
        _merge_dict(args, self.kwargs.copy())
        _merge_dict(args, kwargs)
        response = self.session.post(self.make_url(endpoint), **args)

        decoded_response = _decode_response(response)

        if return_response:
            return decoded_response, response
        return decoded_response

    def delete(self, endpoint, return_response=False, **kwargs):
        """ Send HTTP DELETE to the endpoint.

        :arg str endpoint: The endpoint to send to.

        :returns:
            JSON decoded result.

        :raises:
            requests.RequestException on timeout or connection error.

        """
        args = {}
        if "data" in kwargs or "json" in kwargs:
            _merge_dict(
                args, {
                    "headers": {
                        "Content-Type": "application/json;charset=UTF-8"
                    }
                }
            )
        _merge_dict(args, self.kwargs.copy())
        _merge_dict(args, kwargs)
        response = self.session.delete(self.make_url(endpoint), **args)

        decoded_response = _decode_response(response)

        if return_response:
            return decoded_response, response
        return decoded_response

    def review(self, change_id, revision, review):
        """ Submit a review.

        :arg str change_id: The change ID.
        :arg str revision: The revision.
        :arg str review: The review details as a :class:`GerritReview`.

        :returns:
            JSON decoded result.

        :raises:
            requests.RequestException on timeout or connection error.

        """

        endpoint = "changes/%s/revisions/%s/review" % (change_id, revision)
        self.post(endpoint, data=str(review))


class GerritClient(GerritRestAPI):
    def __init__(self, url, username, password, auth_class=HTTPBasicAuth):
        super(GerritClient, self).__init__(url, auth=auth_class(username, password))

    def get_project(self, project_name):
        """
        Find a project
        :param project_name: The name of the project
        :return: object you can use to operate on the project
        """
        return GerritProject(self, **self.get('/projects/%s' % quote_plus(project_name)))

    def query_changes(self, **kwargs):
        """
        :keyword change: The Change-Id of the change.
        :keyword project: The name of the project.
        :keyword branch: The name of the target branch. The refs/heads/ prefix is omitted.
        :keyword message: The subject of the change (header line of the commit message).
        :keyword status: The status of the change (NEW, MERGED, ABANDONED, DRAFT).
        :keyword topic: The topic to which this change belongs
        :return:
        """
        options = ['CURRENT_REVISION', 'CURRENT_COMMIT', 'CURRENT_FILES'] if 'options' not in kwargs else kwargs.pop(
            'options')

        def _encode_query(query):
            query_string = urlencode(query, doseq=True) if query else ''
            return query_string

        query = ' '.join('{}:{}'.format(k, v.replace(' ', '+')) for k, v in kwargs.items() if v)
        return [GerritChange(self, **c) for c in self.get('/changes/?' + _encode_query({
            'o': options,
            'q': query
        }))]

    def get_change(self, **kwargs):
        return next(iter(self.query_changes(**kwargs) or []), None)

    def create_change(self, project, branch, subject, **optional_args):
        """
        :param project: The name of the project.
        :param branch: The name of the target branch. The refs/heads/ prefix is omitted.
        :param subject: The subject of the change (header line of the commit message).
        :keyword change_id: The Change-Id of the change.
        :keyword status: The status of the change (NEW, MERGED, ABANDONED, DRAFT).
        :keyword topic: The topic to which this change belongs
        :return:
        """
        args = {
            'project': project,
            'branch': branch,
            'subject': subject
        }
        args.update(optional_args)
        return GerritChange(self, **self.post('/changes/', json=args))
