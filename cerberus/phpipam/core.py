
import requests
import base64

from . import (
    make_request,
    errors
)
from cerberus.utils import parser
import logging

logger = logging.getLogger(__name__)

class PHPIPAMService(object):

    def __init__(self, app_id, endpoint, user, pwd, retries=3):
        self.endpoint = endpoint[:-1] if endpoint.endswith("/") else endpoint
        self.app_id = app_id
        self.user = user
        self.pwd = pwd
        self.retries = retries
        self.token = self._set_token()
    
    @property
    def authorization(self):
        encoded = base64.b64encode(f"{self.user}:{self.pwd}".encode("utf-8"))
        return encoded.decode("utf-8")

    @property
    def base_url(self):
        return f"{self.endpoint}/api/{self.app_id}"

    def _set_token(self):
        url = f"{self.base_url}/user/"
        headers = {
            "Content-Type" : "application/json",
            "Authorization" : f"Basic {self.authorization}"
        }
        response = make_request("POST", url=url, headers=headers)
        return response["data"]["token"]
    
    def check_free_ipaddr(self, subnet_id=None, subnet_cidr=None):
        subnet_id = self.check_subnet(cidr=subnet_cidr, subnet_id=subnet_id)
        url = f"{self.base_url}/addresses/first_free/{subnet_id}/"

        response = make_request(
            "GET", 
            url=url, 
            headers=dict(token=self.token)
        )
        return parser.JSONParser("IPFreeResponse", response)


    def reserve_ipaddr(self, subnet_id=None, subnet_cidr=None):
        if subnet_cidr:
            subnet_id = self.find_subnet(subnet_cidr)
        elif not subnet_id:
            raise ValueError("Subnet ID or CIDR are needed!")

        url = f"{self.base_url}/addresses/first_free/{subnet_id}/"

        retry = 0
        while retry < self.retries:
            try:
                response = make_request(
                    "POST", 
                    url=url, 
                    headers=dict(token=self.token)
                )
            except:
                retry+=1
            else:
                break

        return parser.JSONParser("IPReserveResponse", response)
    
    def release_ipaddr(self, address, subnet_id=None, subnet_cidr=None):
        subnet_id = self.check_subnet(cidr=subnet_cidr, subnet_id=subnet_id)        

        url = f"{self.base_url}/addresses/{address}/{subnet_id}/"
        
        response = make_request(
            "DELETE", 
            url=url, 
            headers=dict(token=self.token)
        )
        return parser.JSONParser("IPReleaseResponse", response)

    def add_ipaddr(self, payload={}, subnet_id=None, subnet_cidr=None, show_result=False):
        subnet_id = self.check_subnet(cidr=subnet_cidr, subnet_id=subnet_id)
        payload["subnetId"] = subnet_id
        url = f"{self.base_url}/addresses/"
        response = make_request(
            "POST",
            url=url, 
            headers=dict(token=self.token),
            payload=payload
        )

        response = parser.JSONParser("IPNewResponse", response)

        if show_result:
            response = make_request(
                "GET",
                url=f"{url}{response.id}/",
                headers=dict(token=self.token)
            )
            response = parser.JSONParser("IPNewResponse", response)
            return response.data

        return response.id

    def update_ipaddr(self, address, payload={}, subnet_id=None, subnet_cidr=None, show_result=False):
        subnet_id = self.check_subnet(cidr=subnet_cidr, subnet_id=subnet_id)
        address = self.show_ipaddr(address=address, subnet_id=subnet_id)

        url = f"{self.base_url}/addresses/{address.id}/"
        response = make_request(
            "PATCH",
            url=url,
            headers=dict(token=self.token),
            payload=payload
        )

        if show_result:
            response = make_request(
                "GET",
                url=url,
                headers=dict(token=self.token)
            )
            response = parser.JSONParser("IPUpdateResponse", response) 
            return response.data
        
        return parser.JSONParser("IPUpdateResponse", response)

    
    def show_ipaddr(self, address=None, hostname=None, subnet_id=None, subnet_cidr=None):
        if subnet_cidr:
            subnet_id = self.find_subnet(cidr=subnet_cidr)

        if address:
            url = f"{self.base_url}/addresses/search/{address}/"
        elif hostname:
            url = f"{self.base_url}/addresses/search_hostname/{hostname}/"
        else:
            raise ValueError("Address or Hostname are needed!")
        
        response = make_request(
            "GET",
            url=url, 
            headers=dict(token=self.token)
        )

        if not response.get("data"):
            if address: msg = f"ipv4 ({address})"
            elif hostname: msg = f"hostname ({hostname})"
            msg = f"Address with {msg} not found"
            raise errors.NotFound(msg)

        response = parser.JSONParser("IPInfoResponse", response)

        if subnet_id:
            subnet = self.show_subnet(subnet_id=subnet_id)
            data = list(filter(lambda x: x.subnetId == subnet_id, response.data))
            if not data:
                if address: msg = f"ipv4 ({address})"
                elif hostname: msg = f"hostname ({hostname})"
                msg = f"Address with {msg} in the subnet ({subnet.subnet}/{subnet.mask}) not found!"
                raise errors.NotFound(msg)
            return data[0].export("IPInfoData")
        return response.data

    def check_subnet(self, cidr, subnet_id):
        if cidr:
            subnet_id = self.find_subnet(cidr)
        elif not subnet_id:
            raise ValueError("Subnet ID or Subnet CIDR are needed!")
        return subnet_id

    def find_subnet(self, cidr):
        url = f"{self.base_url}/subnets/cidr/{cidr}/"

        response = make_request(
            "GET", 
            url=url, 
            headers=dict(token=self.token)
        )

        if not response.get("data"):
            raise errors.NotFound(f"Subnet CIDR ({cidr}) not found")

        response = parser.JSONParser("SubnetInfoResponse", response)
        subnet_id = response.data[0].id
        return subnet_id

    def show_subnet(self, subnet_id=None, cidr=None):
        subnet_id = self.check_subnet(cidr=cidr, subnet_id=subnet_id)
        url = f"{self.base_url}/subnets/{subnet_id}/"
        response = make_request(
            "GET", 
            url=url, 
            headers=dict(token=self.token)
        )
        response = parser.JSONParser("SubnetInfoResponse", response)
        return response.data.export("SubnetInfoData")