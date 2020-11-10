import logging
from pprint import pformat
from contextlib import contextmanager


@contextmanager
def log_on_exception(**kwargs):
    try:
        yield
    except Exception:
        logging.error('Exception occurred in the following context:\n' +
            pformat(kwargs))
        raise

