class Error(Exception):
    pass

class ServiceUnavailable(Error):
    pass
    
class NotFound(Error):
    pass

class HttpError(Error):
    pass