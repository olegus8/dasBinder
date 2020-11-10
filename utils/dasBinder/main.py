import sys
from os import path

if __name__ == '__main__':
    sys.path.append(path.join(path.dirname(__file__),
        '..', '..', 'src', 'python'))
    from das.binder.binder import Binder
    Binder(argv=sys.argv).run()
