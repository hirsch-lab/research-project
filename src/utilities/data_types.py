
def static_vars(**kwargs):
    '''
    Function decorator to create static, resetable variables.
    Call the function method function.reset() to reset the static variables.

    Usage:
        @static_vars(counter=0)
        def f():
            f.counter += 1
            print("Count:", f.counter)

        f()         # Count: 1
        f()         # Count: 2
        f.reset()
        f()         # Count: 1

    Further reading:
        https://stackoverflow.com/a/279586/3388962
        https://realpython.com/primer-on-python-decorators/
    '''
    def decorate(func):
        def reset():
            # TODO: maybe use properties to control access
            # via setters and getters.
            for k,v in kwargs.items():
                setattr(func, k, v)
            # Return the function, to permit access chains.
            # E.g: print(func.reset().attr),
            #      func.reset()(x,y)
            # The latter is a bit cryptic.
            return func
        reset()
        setattr(func, 'reset', reset)
        return func
    return decorate



################################################################################
class StructContainer():
    '''
    Build a type that behaves similar to a struct.

    Usage:
        # Construction from named arguments.
        settings = StructContainer(option1 = False,
                                   option2 = True)
        # Construction from dictionary.
        settings = StructContainer({'option1': False,
                                    'option2': True})
        print(settings.option1)
        settings.option2 = False
        for k,v in settings.items():
            print(k,v)

    Note: Before python3.6, the order of kwargs is not preserved!
          https://stackoverflow.com/questions/26748097/

    Note: The internal __dict__ object is not guaranteed to respect the order
          of insertion prior to python 3.7, (for CPython prior to python 3.6).
          https://stackoverflow.com/a/39980744/3388962

          It is not possible to override the __dict__ object with an
          OrderedDict, as explained by Martijn Pieters:
          https://stackoverflow.com/a/27941731/3388962

    '''
    def __init__(self, dictionary=None, **kwargs):
        if dictionary is not None:
            assert(isinstance(dictionary, (dict, StructContainer)))
            # TODO: test if keys are valid python expressions.
            self.__dict__.update(dictionary)
        self.__dict__.update(kwargs)

    def __iter__(self):
        for i in self.__dict__:
            yield i

    def __getitem__(self, key):
        return self.__dict__[key]

    def __setitem__(self, key, value):
        self.__dict__[key] = value

    def __len__(self):
        return sum( 1 for k in self.keys() )

    def __repr__(self):
        return "struct(**%s)" % str(self.__dict__)

    def __str__(self):
        return str(self.__dict__)

    def items(self):
        for k, v in self.__dict__.items():
            if not k.startswith('_'):
                yield (k,v)

    def keys(self):
        for k in self.__dict__:
            if not k.startswith('_'):
                yield k

    def values(self):
        for k, v in self.__dict__.items():
            if not k.startswith('_'):
                yield v

    def update(self, data):
        self.__dict__.update(data)

    def asdict(self):
        return dict(self.items())

    def first(self):
        # This function makes only sense starting for python 3.6+
        # where the insertion order is respected by a dict.
        key, value = next(self.items())
        return key, value

    def last(self):
        # This function makes only sense starting for python 3.6+
        # where the insertion order is respected by a dict.
        # See also: https://stackoverflow.com/questions/58413076
        key = list(self.keys())[-1]
        return key, self[key]

    def get(self, key, default=None):
        return self.__dict__.get(key, default)

    def setdefault(self, key, default=None):
        return self.__dict__.setdefault(key, default)
