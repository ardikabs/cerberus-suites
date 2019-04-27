import os
import click
import time
import subprocess

class KnifeBootstrap(object):

    def __init__(self, debug=True, show_err=True):
        self.show_err = show_err
        self.debug = debug
    
    @classmethod
    def wait_to_live(cls, ipaddr):
        temp = 0
        MAX_THRESHOLD = 25
        while True:

            try:
                output = subprocess.run(
                    f"ping -c 1 {ipaddr} > /dev/null",
                    shell=True,
                    check=True
                ) 
            except subprocess.CalledProcessError as exc:
                pass
            else:
                if output.returncode != 0:
                    temp += 1
                    time.sleep(5)
                else:
                    break
            
            if temp > MAX_THRESHOLD:
                raise RuntimeError(f"Reached MAX TIMEOUT. Unable to reach {ipaddr}")

    def create(
        self, 
        ssh_user, 
        ssh_pwd, 
        ssh_port, 
        ipaddr, 
        fqdn, 
        databag_secret_path=None,
        chef_environment=None, 
        environment=None, 
        runlist=[]
        ):
        self.__class__.wait_to_live(ipaddr)

        command = f"knife bootstrap {ipaddr} --yes --sudo"
        command = f"{command} --node-name {fqdn}"
        command = f"{command} --ssh-user {ssh_user} --ssh-port {ssh_port} --ssh-password '{ssh_pwd}'"

        if chef_environment:
            command = f"{command} --environment {chef_environment}"

        if databag_secret_path:
            command = f"{command} --secret-file {databag_secret_path}"
        
        if runlist:
            runlist = ', '.join(runlist)
            command = f"{command} --run-list '{runlist}'"
               
        command = f"{command} && knife tag create --yes {fqdn} {environment}"

        out = subprocess.PIPE
        if self.debug:
            out = None

        try:
            output = subprocess.run(
                command,
                stdout=out,
                stderr=out,
                shell=True,
                check=True
            )
        except subprocess.CalledProcessError as err:
            if self.show_err:
                return err.output
            else:
                raise err
        else:
            return output
    
    def delete(self, fqdn):
        command = f"knife node delete --yes {fqdn} && knife client delete --yes {fqdn}"
        
        out = subprocess.PIPE
        if self.debug:
            out = None

        try:
            output = subprocess.run(
                command,
                stdout=out,
                stderr=out,
                shell=True,
                check=True
            )
        except subprocess.CalledProcessError as err:
            if self.show_err:
                return err.output
            else:
                raise err
        else:
            return output
