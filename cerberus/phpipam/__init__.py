
import requests
from . import errors

def make_request(method, url, headers={}, params={}, payload={}, timeout=30):
    method = str.upper(method)
    kwargs = {
        "url": url,
        "headers": headers,
        "params": params,
        "json": payload,
        "timeout": timeout
    }

    try:
        if method == "GET":
            response = requests.get(**kwargs)
        elif method == "POST":
            response = requests.post(**kwargs)
        elif method == "PATCH":
            response = requests.patch(**kwargs)
        elif method == "PUT":
            response = requests.put(**kwargs)
        elif method == "DELETE":
            response = requests.delete(**kwargs)
        response.raise_for_status()

    except (requests.ConnectionError, requests.Timeout) as e:
        err = errors.ServiceUnavailable(f"Timeout reached or may phpIPAM service had internal error: {str(e)}")
        raise err

    except requests.exceptions.HTTPError as e:

        if e.response.status_code != 500:
            raise errors.HttpError(str(e))

        err = errors.ServiceUnavailable(f"phpIPAM service had internal error: {str(e)}")
        raise err

    return response.json()