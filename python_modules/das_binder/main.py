import sys
import doctest
from os import path

if __name__ == '__main__':
    sys.path += [
        path.join(path.dirname(__file__), '..'),
        path.join(path.dirname(__file__), '..',
            '..', 'dasShared', 'python_modules'),
    ]
    import binder
    from binder import Binder
    doctest.testmod(binder)
    binder.Binder(argv=sys.argv).run()
