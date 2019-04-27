import dns.update
import dns.tsigkeyring
import dns.resolver
import dns.rdatatype
import dns.query
import dns.zone
import dns.rdataclass
import dns.tsig
from dns.exception import DNSException


class DNSService(object):
    
    def __init__(self, zone, nameserver, keyring_name, keyring_value, timeout=10):
        self.zone = zone
        self.nameserver = nameserver
        self.keyring = dns.tsigkeyring.from_text(
            {keyring_name: keyring_value}
        )
        self.timeout = timeout
    
    @property
    def process_msg(self):
        try:
            result = self.process_result
        except AttributeError:
            result = None
        finally:
            return result

    def add_record(self, name, content, rtype, ttl=300):
        rtype = self.validate_rtype(rtype)
        data = dns.update.Update(self.zone, keyring=self.keyring)
        data.add(name, ttl, rtype, content)
        return self.handler(data)
    
    def update_record(self, name, content, rtype, ttl=300):
        rtype = self.validate_rtype(rtype)
        data = dns.update.Update(self.zone, keyring=self.keyring)
        data.replace(name, ttl, rtype, content)
        return self.handler(data)
        
    def remove_record(self, name, rtype=None):
        if rtype:
            rtype = self.validate_rtype(rtype)
        data = dns.update.Update(self.zone, keyring=self.keyring)
        data.delete(name, rtype)
        return self.handler(data)

    def import_records(self):
        answer = dns.resolver.query(self.zone, "NS")
        for rdata in answer:
            try:
                ns = str(rdata)
                dns_zone = dns.zone.from_xfr(dns.query.xfr(ns, self.zone))
            except DNSException as exc:
                exc = DNSException(f"{str(exc)} ({self.zone})")
                raise exc
            except Exception as exc:
                exc = RuntimeError(f"{str(exc)} ({self.zone})")
                raise exc
        
        records = list()
        for name, node in dns_zone.nodes.items():
            todict = {}
            for rdataset in node.rdatasets:
                for rdata in rdataset:
                    if rdataset.rdtype in (
                            dns.rdatatype.A, 
                            dns.rdatatype.CNAME, 
                            dns.rdatatype.MX,
                    ):
                        todict["zone"] = self.zone  
                        todict["name"] = str(name)
                        todict["content"] = rdata.to_text()                
                        todict["rtype"] = dns.rdatatype.to_text(rdataset.rdtype)
                        todict["ttl"] = rdataset.ttl                            
                        todict["representation"] = str(rdataset)
            
            if not todict: continue

            records.append(todict)
        return records
      

    def handler(self, data):
        err = True
        try:
            result = dns.query.tcp(data, self.nameserver, timeout=self.timeout)
            self.process_result = str(result)
            response = str(result).split("\n")[2].split(" ")[1]
            err = False
        except dns.tsig.PeerBadKey as e:
            response = "Looks like you have a wrong key to be used to communicate with DNS Server [BADKEY]"
        except dns.tsig.PeerBadTime as e:
            response = "Looks like you have unsynchronized datetime on DNS Server [BADTIME]"
        except dns.tsig.PeerBadSignature as e:
            response = "Looks like you have wrong signature to communite with DNS Server [BADSIGNATURE]"
        except dns.tsig.PeerError as e:
            response = str(e)
        finally:
            return response, err
    
    def validate_rtype(self, rtype):
        rtype = dns.rdatatype.from_text(rtype)
        if rtype in (
            dns.rdatatype.A,
            dns.rdatatype.CNAME,
            dns.rdatatype.PTR,
            dns.rdatatype.MX,
            dns.rdatatype.TXT,
            dns.rdatatype.SRV
        ):
            return rtype
        else:
            err = ValueError(f"DNS Service are not supported for this kind record type {rtype}")
            raise err