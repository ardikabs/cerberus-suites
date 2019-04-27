
import threading
import time
import inspect
from cerberus.utils import (
    build_dict
)


class Threading(object):
    """ Threading example class
    The run() method will be started and it will run in the background
    until the application exits.
    """

    def __init__(self, func, *args, **kwargs):
        """ Constructor
        :type interval: int
        :param interval: Check interval, in seconds
        """
        self.result = None
        self.exception = None
        thread = threading.Thread(target=self.run(func), args=args, kwargs=kwargs)
        thread.daemon = True                  # Daemonize thread
        thread.start()                        # Start the execution

    @property
    def progress(self):
        while True:
            yield self.result        

    def run(self, func):
        """ Method that runs forever """
        def function(*args, **kwargs):
            try:
                self.result = func(*args, **kwargs)
            except Exception as e:
                self.exception = str(e)
        return function


def prompt_for_password(prompt):
    import getpass
    return getpass.getpass(
        prompt=prompt
    )
    
def prompt_y_n_question(question, default="no"):
    valid = {
        "yes": True, "y": True, "ye": True,
        "no": False, "n": False
    }
    if default is None:
        prompt = " [y/n] "
    elif default == "yes":
        prompt = " [Y/n] "
    elif default == "no":
        prompt = " [y/N] "
    else:
        raise ValueError("Invalid default answer: '{}'".format(default))

    while True:
        print(question + prompt)
        choice = input().lower()
        if default is not None and choice == '':
            return valid[default]
        elif choice in valid:
            return valid[choice]
        else:
            print("Please, respond with 'yes' or 'no' or 'y' or 'n'.")
import json
from click.types import convert_type

def key_name(key):

    def decorator(cls):
        class_key_name = getattr(cls, "key_name", None)
        if class_key_name is None:
            cls.key_name = key
        return cls
    return decorator

class StateParam(object):

    def __init__(self, name=None, type=None, multiple=None, default=None,
                 help=None):
        self.name = name
        self.type = convert_type(type, default)
        self.multiple = multiple
        self.default = default
        self.help = help

    def parse(self, text):
        if self.multiple:
            parts = text.strip().split()
            values = [self.type.convert(value, self, ctx=None)
                      for value in parts]
            return values
        else:
            return self.type.convert(text, self, ctx=None)

class StateComponent(object):

    @key_name("services")
    class Services(object):
        name = StateParam(type=str)
        count = StateParam(type=int)
        environment = StateParam(type=str)
        category = StateParam(type=str)
    
    @key_name("instances")
    class Instances(object):
        name = StateParam(type=str)
        hostname = StateParam(type=str)
        domain = StateParam(type=str)
        ipv4 = StateParam(name="guest.ipAddress", type=str)
        num_cpus = StateParam(type=int)
        memory = StateParam(type=int)
        folder = StateParam(type=str)
        datacenter = StateParam(type=str)
        datastore = StateParam(type=str)
        compute = StateParam(type=str)
        network = StateParam(type=str)
        template = StateParam(type=str)


class StateReader(object):
    state_files = ["cerberus.state.json", "coba.json"]
    state_components = [
        StateComponent.Instances,
        StateComponent.Services
    ]

    def __init__(self, state_file=None, auto_save=False):
        self.state_files = [state_file] if state_file else self.__class__.state_files
        self.state_used = None
        self.auto_save = auto_save
        self.data = {}

    def add(self, name, data, check_keys="name"):
        cls = self.__class__
        err = None
        for component in cls.state_components:
            if name == component.key_name:
                if isinstance(check_keys, tuple) or isinstance(check_keys, list):
                    check = build_dict(self.data[component.key_name], keys=check_keys)
                    key = f"{'.'.join([data[key] for key in check_keys])}"
                    if check.get(data.get(key)):
                        err = ValueError(f"Duplication in [{name}] state component: "
                            f"{','.join(data[key].split('.'))} already exists"
                        )

                else:
                    check = build_dict(self.data[component.key_name], keys=check_keys)
                    key = check_keys
                    if check.get(data.get(key)):
                        err = ValueError(f"Duplication in [{name}] state component: "
                            f"{data[key]} already exists"
                        )
                if err:
                    raise err

                new_data = parse_data_to_component(
                    component, 
                    data
                )
                self.data[component.key_name].append(new_data)
        
        if self.auto_save:
            self.save()
    
    def update(self, name, data, check_keys="name"):
        cls = self.__class__
        for component in cls.state_components:
            if name == component.key_name:
                if isinstance(check_keys, tuple) or isinstance(check_keys, list):
                    check = build_dict(self.data[component.key_name], keys=check_keys)
                    key = f"{'.'.join([data[key] for key in check_keys])}"
                    index = check.get(key).get('index')
                else:
                    check = build_dict(self.data[component.key_name], keys=check_keys)
                    index = check.get(key).get('index')
                data = parse_data_to_component(
                    component, 
                    data
                )
                self.data[component.key_name][index] = data

    def delete(self, name, data, check_keys="name"):
        cls = self.__class__
        for component in cls.state_components:
            if name == component.key_name:
                if isinstance(check_keys, tuple) or isinstance(check_keys, list):
                    check = build_dict(self.data[component.key_name], keys=check_keys)
                    key = f"{'.'.join([data[key] for key in check_keys])}"
                    index = check.get(key).get('index')
                else:
                    check = build_dict(self.data[component.key_name], keys=check_keys)
                    index = check.get(key).get('index')
                data = parse_data_to_component(
                    component, 
                    data
                )
                self.data[component.key_name].pop(index)
        
        if self.auto_save:
            self.save()
        
    def get(self, name, filters=None):
        data = self.data[name]
        return build_dict(data, keys=filters)
        


    def read(self):
        fail = 0
        for state in self.state_files:
            try:
                fileused = open(state, "r")
                self.data = json.load(fileused)
                self.state_used = fileused.name
                break
            except FileNotFoundError:
                fail += 1
                
        if fail == len(self.__class__.state_files):
            raise ValueError("No state file found")
                

    def save(self):
        if self.state_used:
            fileused = open(self.state_used, "w")
            json.dump(self.data, fileused, indent=4)
            

def parse_data_to_component(component, data):
    storage = {}
    for name, param in select_params_from_component(component):
        value = data.get(param.name or name, None)
        if value:
            storage[name] = param.parse(value)
    return storage

def select_params_from_component(component, param_class=StateParam):

    for name, value in inspect.getmembers(component):
        
        if name.startswith("__") or value is None:
            continue
        elif isinstance(value, param_class):
            yield (name, value)