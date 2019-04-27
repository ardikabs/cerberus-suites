
import functools

def rsetattr(obj, attr, val):
    pre, _, post = attr.rpartition('.')
    return setattr(rgetattr(obj, pre) if pre else obj, post, val)

def rgetattr(obj, attr, *args):
    def _getattr(obj, attr):
        return getattr(obj, attr, *args)
    return functools.reduce(_getattr, [obj] + attr.split('.'))

def obj2dict(obj, attributes):
    dict_ = {}
    for attribute in attributes:
        dict_[attribute] = rgetattr(obj, attribute)
    return dict_

class dotdict(dict):
    """dot.notation access to dictionary attributes"""
    def __getattr__(*args): 
        val = dict.get(*args) 
        return dotdict(val) if type(val) is dict else val 
    
    __setattr__ = dict.__setitem__ 
    __delattr__ = dict.__delitem__

    def got(self, key):
        obj = self
        key = key.split(".")
        for k in key:
            if not isinstance(obj, dict):
                break
            obj=obj.get(k)
        return obj
        
def build_dict(seq, keys):
    if isinstance(keys, tuple):
        keysgroups = []
        for index, d in enumerate(seq):
            temp = [] 
            for key in keys:
                temp.append(d[key])
            keysgroups.append(".".join(temp))

        return dict((d[1], dict(d[0], index=index)) for (index, d) in enumerate(zip(seq, keysgroups)))

    else:
        return dict((d[keys], dict(d, index=index)) for (index, d) in enumerate(seq))

