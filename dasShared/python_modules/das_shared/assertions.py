def assert_equal(a, b):
    if a != b:
        raise AssertionError('{} != {}'.format(repr(a), repr(b)))

def assert_not_equal(a, b):
    if a == b:
        raise AssertionError('{} == {}'.format(repr(a), repr(b)))

def assert_is_instance(x, cls):
    if not isinstance(x, cls):
        raise AssertionError('{} is not an instance of {}'.format(
            repr(x), repr(cls)))

def assert_is_file(fpath):
    if not path.isfile(fpath):
        raise AssertionError('This must be an existing file: {}'.format(fpath))

def assert_greater_equal(a, b):
    if a < b:
        raise AssertionError('{} < {}'.format(repr(a), repr(b)))

def assert_greater(a, b):
    if a <= b:
        raise AssertionError('{} <= {}'.format(repr(a), repr(b)))

def assert_less(a, b):
    if a >= b:
        raise AssertionError('{} >= {}'.format(repr(a), repr(b)))

def assert_less_equal(a, b):
    if a > b:
        raise AssertionError('{} > {}'.format(repr(a), repr(b)))

def assert_path_not_exists(fpath):
    if path.exists(fpath):
        raise AssertionError('Path must not exist: {}'.format(fpath))

def assert_is_none(x):
    if x is not None:
        raise AssertionError('Must be None: {}'.format(repr(x)))

def assert_in(x, container):
    if x not in container:
        raise AssertionError('{} is not in {}'.format(
            repr(x), repr(container)))

def assert_starts_with(s, prefix):
    if not s.startswith(prefix):
        raise AssertionError('"{}" must start with "{}"'.format(s, prefix))

def assert_not_in(x, container):
    if x in container:
        raise AssertionError('{} is not in {}'.format(
            repr(x), repr(container)))

def assert_empty(container):
    if len(container) > 0:
        raise AssertionError('Container must be empty: {}'.format(
            repr(container)))

def assert_container_of_instances(xs, cls):
    for x in xs:
        assert_is_instance(x, cls)

def assert_unique_elements(xs):
    dupes = [x for x, count in Counter(xs).items() if count > 1]
    if dupes:
        raise AssertionError('Non unique elements:\n{}'.format(
            '\n'.join(sorted(map(repr, dupes)))))
