class Error(Exception):
    pass

class ServiceUnavailable(Error):
    pass
    
class SessionError(Error):
    pass

class CredentialError(Error):
    pass

class UnrecognizedResourceError(Error):
    pass

class DatacenterAttributeError(Error):
    pass

class DatastoreAttributeError(Error):
    pass

class TaskError(Error):
    pass