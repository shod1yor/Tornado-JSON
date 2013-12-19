import logging

from tornado.web import RequestHandler
from jsonschema import ValidationError

from tornado_json.jsend import JSendMixin
from tornado_json.utils import APIError


class BaseHandler(RequestHandler):

    """
    The mother of all handlers; all handlers should be subclassed from this.
    """

    @property
    def db_conn(self):
        """Returns database connection abstraction

        If no database connection is available, raises an AttributeError
        """
        db_conn = self.application.db_conn
        if not db_conn:
            raise AttributeError("No database connection was provided.")
        return db_conn


class ViewHandler(BaseHandler):

    """Handler for views"""

    def initialize(self):
        """
        - Set Content-type for HTML
        """
        self.set_header("Content-Type", "text/html")


class APIHandler(BaseHandler, JSendMixin):

    """
    RequestHandler for API calls
      - Sets header as application/json
      - Provides custom write_error that writes error back as JSON
         rather than as the standard HTML template
    """

    def initialize(self):
        """
        - Set Content-type for JSON
        """
        self.set_header("Content-Type", "application/json")

    def write_error(self, status_code, **kwargs):
        """Override of RequestHandler.write_error

        Calls `error()` or `fail()` from JSendMixin depending on which
        exception was raised with provided reason and status code.

        :type  status_code: int
        :param status_code: HTTP status code
        """
        self.clear()

        # If exc_info is not in kwargs, something is very fubar
        if not "exc_info" in kwargs.keys():
            logging.error("exc_info not provided")
            self.set_status(500)
            self.error(message="Internal Server Error", code=500)
            self.finish()

        self.set_status(status_code)

        # Any APIError exceptions raised will result in a JSend fail written
        # back with the log_message as data. Hence, log_message should NEVER
        # expose internals. Since log_message is proprietary to HTTPError
        # class exceptions, all exceptions without it will return their
        # __str__ representation.
        # All other exceptions result in a JSend error being written back,
        # with log_message only written if debug mode is enabled
        exception = kwargs["exc_info"][1]
        if any(isinstance(exception, c) for c in [APIError, ValidationError]):
            self.fail(exception.log_message if
                      hasattr(exception, "log_message") else str(exception))
        else:
            self.error(message=self._reason,
                       data=exception.log_message if self.settings.get(
                           "debug") else None,
                       code=status_code)
        self.finish()
