
from cerberus import utils

class JSONParser:

    def __init__(self, name, dict_={}):
        self._name = name
        self._keys = list()
        for attr in dict_:
            if isinstance(dict_.get(attr), dict):
                dict_[attr] = self.__class__.from_dict(attr, dict_.get(attr, None))
            elif isinstance(dict_.get(attr), list):
                dict_[attr] = list(self.__class__(attr, dt) for dt in dict_.get(attr))
            self._keys.append(attr)
        self.__dict__.update(dict_)

    def __repr__(self):
        items = (f"{k}={self.__dict__.get(k) !r}" for k in self._keys)
        return f"{self._name}({', '.join(items)})"
    
    def __str__(self):
        items = (f"{k}={self.__dict__.get(k) !s}" for k in self._keys)
        return f"{self._name}({', '.join(items)})"
    
    def to_dict(self):
        todict = {}
        for key in self.__dict__:
            if key in self._keys:
                if isinstance(self.__dict__[key], JSONParser):
                    todict[key] = self.__dict__[key].to_dict()
                else:
                    todict[key] = self.__dict__[key]
        return todict

    def export(self, name=None):
        """  
            >>>
            json_response = {
                "success": True,
                "data": {
                    "uid": "2110141010",
                    "full_name": "Ardika Bagus Saputro",
                    "first_name": "Ardika",
                    "middle_name": "Bagus",
                    "last_name": "Saputro",
                    "hobbies": ["Read", "Hiking", "Code"],
                    "skills": [
                        "Python", "Golang", "Distributed System", 
                        "Infrastructure Best Practice", "DevOps Related", 
                        "Linux", "Monitoring", "Containerization"
                    ],
                    "tools":["Docker", "Consul", "Ansible", "Packer", "Terraform"],
                    "role": "Infrastructure with Code guy",
                    "title": "Site Infrastructure Engineer"
                }
            }
            obj = JSONParser("ObjResponse", json_response)
            data_obj = obj.data.export("DataObj")
            return:
                DataObj(uid='2110141010', full_name='Ardika Bagus Saputro', first_name='Ardika', ...)
        """
        if isinstance(self, JSONParser):
            if name:
                self._name = name
            return self 
        else:
            raise ValueError("Field is not a dict type, so it can't convert to object")

    @classmethod
    def from_dict(cls, name, dict_={}):
        if dict_ is None:
            return None

        doc = cls(name, dict_)
        return doc
        


class BeautifyFormat(object):

    @staticmethod
    def get_length(d):
        if d and isinstance(d, list):
            return len(str(d[0]))
        return len(str(d))

    @classmethod
    def from_object(cls, data, headers=[], attr=[], padding=5):
        arr = [headers]
        arr.extend(cls.create_arr_from_object(data, attr))
        widths = [max(map(cls.get_length, col)) for col in zip(*arr)]

        result = [" ".join(map(cls._get(padding), zip(ar, widths))) for ar in arr]
        return result

    @classmethod
    def from_dict(cls, data, headers=[], attr=[], padding=5, nested=False):
        arr = [headers]
        arr.extend(cls.create_arr_from_dict(data, attr, nested=nested))
        widths = [max(map(cls.get_length, col)) for col in zip(*arr)]

        result = [" ".join(map(cls._get(padding), zip(ar, widths))) for ar in arr]
        return result

    @classmethod
    def from_arr(cls, data, headers=[], padding=5):
        arr = [headers]
        arr.extend(data)
        widths = [max(map(cls.get_length, col)) for col in zip(*arr)]

        result = [" ".join(map(cls._get(padding), zip(ar, widths))) for ar in arr]
        return result

    @staticmethod
    def _get(padding):
        def func(data):
            val, width = data
            if val and isinstance(val, list):
                val = val[0]

            return f"{val if val else '-':<{width+padding}}"
        return func

    @staticmethod
    def create_arr_from_dict(data, attr, nested=False):
        if isinstance(data, list):
            for dict_ in data:
                if nested:
                    dict_ = utils.dotdict(dict_)
                    yield [dict_.got(at) for at in attr]
                else:
                    yield [dict_.get(at, '-') for at in attr]
        else:
            if nested:
                data = utils.dotdict(data)
                yield [data.got(at) for at in attr]
            else:
                yield [data.get(at, '-') for at in attr]

    @staticmethod
    def create_arr_from_object(data, attr=None):
        if isinstance(data, list):
            for obj in data:
                if isinstance(obj, object) and not attr:
                    raise AttributeError("Object attribute are not defined")

                yield [utils.rgetattr(obj, at) for at in attr]
        else:
            yield [utils.rgetattr(data, at) for at in attr]