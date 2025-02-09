import aiohttp
import urllib.parse
from urllib.parse import quote, urlencode

from ._http_client import HTTPClient
from .querybuilders import TableQueryBuilder

from .supebase_exceptions import (
    UnexpectedValueTypeError,
    ClientConnectorError,
    SupabaseError,
)

from collections import namedtuple

Error = namedtuple("SupabaseError", ("error", "data", "status"))


class TableClient(TableQueryBuilder):

    """
    This class abstracts access to the endpoint to the
    READ, INSERT, UPDATE, and DELETE operations on an existing table

    :param api_url: supabase app API_URL
    :type  api_url: String
    :param table_name: an exising supabase table
    :type  table_name: String
    :param headers: request headers
    :type  headers: Dictionary

    Example
    -------

    >>> table_client = TableClient(
    ...     api_url    = "http://app-name.supabase.co",
    ...     table_name = "posts",
    ...     headers    = {
    ...        "apiKey": "SUPABASE_API_KEY",
    ...         "Authorization": "SUPABASE_API_KEY"
    ...     }
    ... )
    >>>
    """

    def __init__(self, api_url, table_name, headers={}, raise_error=True):
        self.base_url = api_url + "/" + table_name
        self.name = table_name
        self.headers = headers
        self.success_status_codes = list(range(200, 300))
        self.raise_error = raise_error

        super().__init__(self.base_url)

    async def get(self, row):
        """
        Lets you READ the data in the specified `row`

        :return: serialized JSON
        """
        return self.select(row).query()

    async def update(self, target, data):
        """
        Lets you UPDATE rows.

        :params column_values: (column, value)
        :type   column_values: Tuple<String, Any>
        :params new_value: (column, value)
        :type   new_value: Tuple<String, Any>

        :return: the replaced values.

        Example
        --------
        ...
        >>> # Provided there is an existing table called `posts`
        >>> supabase.table("posts").update(("id", 1), ("title", "new title"))
        """

        headers = self.headers.copy()
        headers.update({"Prefer": "return=representation"})

        endpoint = f"{self.base_url}?{urllib.parse.urlencode(target)}"

        try:
            async with HTTPClient(endpoint, headers=headers) as session:
                response, json_data = await session.requests("PATCH", json=data)
                return self._error(response, json_data), json_data
        except aiohttp.ClientConnectorError as err:
            raise ClientConnectorError(str(err))

    async def insert(self, data):
        """
        Lets you INSERT into your tables.
        You can also insert in bulk.

        :param data: the data you wish to insert
        :type  data: List<Dictionary>

        :return: the replaced values.

        Example
        --------
        ...
        >>> # Provided there is an existing table called `posts`
        >>> supabase.table("posts").insert([{"title": "Hello, world!"}])
        """

        if type(data) is not list:
            raise UnexpectedValueTypeError("Expected a list for: `value`")

        headers = self.headers.copy()
        headers.update({"Prefer": "return=representation"})

        endpoint = self.base_url

        try:
            async with HTTPClient(endpoint, headers=headers) as session:
                response, json_data = await session.requests("POST", json=data)
                return self._error(response, json_data), json_data
        except aiohttp.ClientConnectorError as err:
            raise ClientConnectorError(str(err))

    async def delete(self, target):
        """
        Lets you DELETE rows.

        :param column: an existing column
        :type  column: String
        :param value: matching value

        :return: None

        Example
        --------
        ...
        >>> # Provided there is an existing table called `posts`
        >>> supabase.table("posts").delete("id", 3)
        """
        data = target.items()
        endpoint = f"{self.base_url}?"
        for k, v in data:
            endpoint += f"{k}={v}&"
        endpoint = endpoint[:-1]
        try:
            async with HTTPClient(endpoint, headers=self.headers) as session:
                response, json_data = await session.requests("DELETE")
                return self._error(response, json_data), json_data
        except aiohttp.ClientConnectorError as err:
            raise ClientConnectorError(str(err))

    async def customqeury(self, data):
        url = self.base_url + "?" + data

        try:
            async with HTTPClient(url, headers=self.headers) as session:
                response, json_data = await session.requests("GET")
                return self._error(response, json_data), json_data
        except aiohttp.ClientConnectorError as err:
            raise ClientConnectorError(str(err))

    async def query(self):
        """
        Executes a sequence of queries.

        :return: serialized JSON
        """
        if self._as_url:
            try:
                async with HTTPClient(self._as_url, headers=self.headers) as session:
                    response, json_data = await session.requests("GET")
                    return self._error(response, json_data), json_data
            except aiohttp.ClientConnectorError as err:
                raise ClientConnectorError(str(err))

    def is_ok(self, response):
        return response.status in self.success_status_codes

    def _error(self, response, data=None):
        """
        If there's an error with the query,
        we'd raise the error instead of returning it as part of a successful response.
        """

        if not self.is_ok(response):
            error = SupabaseError(data)

            if self.raise_error:
                raise error
            else:
                return Error(error=error, data=data, status=response.status)

        return None
