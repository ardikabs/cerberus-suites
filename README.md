Cerberus Suites is a bundle application built on Command Line (CLI) application. This bundle application consist of `cerberus dns`, `cerberus ipam`, and `cerberus vm`. All the application are a manager for the specific purposes like managing DNS, phpIPAM, and VMWare vSphere.

## Requirement
* Python 3.6+
* phpIPAM Server (Not allowed to configure same subnet in phpIPAM Server)
* DNS Server (Please allowing query and update using keyring on selected zone)
* VMWare vSphere 5.5

## Installation
* Clone this repo.
* Go to repo directory and running installation command with `pip install .` or `python setup.py install`
* Then, `cerberus` is ready to use, but before you can use the functionality, you need to configure the configuration file.
* The accepted configuration file is already served in `cerberus.cfg.example`.
* Cerberus will automatically load the configuration with the name `cerberus.cfg`, if the configuration file is exist on the current directory.
* Unless, you are setup the configuration file with this following command `cerberus --config-file=<cerberus_configuration_file>`

## Usage
After installation process, to use the `cerberus`, simply you can use the help option to know the available command/sub-command/option with `--help` option.

### DNS Command
The following available command are supplied by this command:

#### The `cerberus dns` Command
The `cerberus dns` command used for managing DNS Server (BIND9), with the help of querying to the server, with this command you can possible to add/update/delete the record of the available zone on the DNS server.

Example adding a new record:
```
    cerberus dns make --content=172.18.0.1 --zone=dev.local gateway
```

Example deleting an exist record:
```
    cerberus dns remove --zone=dev.local gateway
```
Example deleting an exist record with FQDN:
```
    cerberus dns remove gateway.dev.local
```
Example updating an exist record:
```
    cerberus dns update --content=172.18.0.254 --zone=dev.local gateway
```

###### Option Reference
* `content` - Content are the value of the record like the ip address. 
* `rtype` - Record type, currently Cerberus only accept one of the following type A, CNAME, PTR, MX, TXT, SRV. Default is A
* `ttl` - Time to live. Default is 300.
* `zone` - DNS zone of the record to be added.

### IPAM Command
The following available command are supplied by this command:

#### The `cerberus ipam` Command
The `cerberus ipam` command used for managing phpIPAM server, cerberus will comunicate to the phpIPAM server endpoint, so you need to ensure that endpoint are reachable. Cerberus only interact with phpIPAM to add/update/delete IP address that managed by phpIPAM server (only addresses).

Example check free ip address available:
```
    cerberus ipam check 172.18.0.0/16
```
Example find ip address (exist):
```
    cerberus ipam find 172.18.0.1
```
Example find ip address with hostname (exist):
```
    cerberus ipam find --hostname gateway
```
Example add ip address (new):
```
    cerberus ipam make --hostname=gateway --cidr=172.18.0.0/16 172.18.0.1
```
Example update ip address information (exist):
```
    cerberus ipam update --hostname=gateway-dev --description="Managed by Cerberus" --cidr=172.18.0.0/16 172.18.0.1
```
Example remove ip address:
```
    cerberus ipam remove --cidr=172.18.0.0/16 172.18.0.1
```

###### Option Reference
* `cidr` - Address CIDR. 
* `hostname` - Address hostname.
* `description` - Address description.
* `note` - Address note.

### VM Command
The following available command are supplied by this command:
#### The `cerberus vm` Command
The `cerberus vm` command used for managing virtual machine that served by VMWare vSphere, but for some sub-command are depend on others (DNS & phpIPAM) like making and destroying virtual machine. Other than that, `cerberus vm` can handle by itself.

Example find virtual machine exist:
```
    cerberus vm find virtual-machine-name
```
Example making virtual machine:
```
    cerberus vm make --environment=dev --category=webserver --cpus=1 --memory=1024 --replicas=3 phpwebserver
```
Example removing virtual machine:
```
    cerberus vm remove phpwebserver
```
Example removing virtual machine with FQDN:
```
    cerberus vm remove --fqdn phpipamwebserver.dev.local
```
Example removing virtual machine with IP address:
```
    cerberus vm remove --ipaddr 172.18.0.25
```

###### Option Reference
* `environment` - Virtual machine environment (set on configuration file). 
* `category` - Virtual machine category (set on configuration file).
* `cpus` - Virtual machine number of CPUs. Default is 1 Core.
* `memory` - Virtual machine size of memory (MegaByte). Default is 1024 MB.
* `folder` - Virtual machine destination folder.
* `replicas` - Number of virtual machine replicas to be created.
* `paralel` - Number of paralel job that possible to used. Default is 3.
* `ipaddr` - Virtual machine IP address.
* `fqdn` - Virtual machine FQDN.
* `uuid` - Virtual machine instance UUID.
* `bootstrap` - Bootstrap flag (set on configuration file).
* `debug` - Debugging flag for bootstrap purpose.

### Configuration File
The configuration file are follow INI file format (using section), so to be used `cerberus`, need to understanding what we need to set on the configuration file. The following available section accepted to be used in `cerberus`:

#### The `vcenter` Section
This section are used by `cerberus vm` command.
##### Variable reference
* `host` - vSphere host address could be ip address or FQDN
* `port` - vSphere port number
* `user` - vSphere user credential
* `pwd` - vSphere user password credential
* `ssl` - vSphere SSL
* `datacenter` - vSphere datacenter name
* `log` - Path on log produced by `cerberus vm make` and `cerberus vm remove`
* `log_format` - Format log to be used, you can set with any format, but available variable only `timestamp`, `action`, `user`, `datacenter`, `vm_name` and `address`
* `zfill` - The numbering format, if zfill is `true` the numbering format will be `01` else will be `1`.
  
#### The `vcenter.environments` Section
This section are used by `cerberus vm make` command.
##### Variable reference
* `available` - This available use for prevent available environment that could work on `cerberus vm make` command.
  
#### The `vcenter.networks.<network_identifier>` Section
This section are used by `cerberus vm make` command. You need to fill all the variable, cerberus using this section to interact with the IPAM, so whenever on virtual machine creation, cerberus receive ip address from IPAM by using CIDR to the IPAM server.
##### Variable reference
* `name` - vSphere network component name
* `dhcp` - Network DHCP (boolean value)
* `cidr` - Network CIDR
* `domain` - Network domain. Used for virtual machine FQDN, and the search suffix on DNS resolve process. Example `dev.local`
* `dns` - List of DNS server
  
#### The `vcenter.environments.<environment_identifier>` Section
This section are used by `cerberus vm make` command.
##### Variable reference
* `type`__*__ - Type of section
* `name`__*__ - Environment name
* `prefix`__*__ - Environment prefix name. Used for virtual machine name.
* `name_format`__*__ - Virtual machine name format. Available variable only `prefix`, `service`, and `category`.
* `hostname_format`__*__ - Virtual machine hostname format. Available variable only `prefix`, `service`, and `category`. 
* `network`__*__ - Selected network from `vcenter.networks.<network_identifier>` section. Used with network identifier.
* `folder`__*__ - vSphere destination folder. Example `WEB-SERVER`.
* `datastore`__**__ - vSphere datastore name. Example `DC-DS-RESOURCE-01`
* `datastore_cluster`__**__ - vSphere datastore cluster name (SDRS). Example `DC-SDRS-RESOURCE-01`
* `compute`__*__ - vSphere Resource Pool. If the computes are Cluster Compute Resource, use `/` as the separator, for example `ClusterComputeName/ResourcePoolA/SubResourcePoolA`
* `template`__*__ - Virtual machine template name. Example `Template-Web-Server`
* `template_path`__*__ - Virtual machine templates path name. Example `Templates`

######IMPORTANT!! 
* __*__ This variable are **required**, which mean virtual machine creation would be used all the variable from environment as **default** variable of the virtual machine component.
* __**__ Avoid define this 2 kind variable of `datastore` and `datastore_cluster` in the same section, because this would be bother on virtual machine creation process.

#### The `vcenter.categories.<environment_identifier>.<category_identifier>` Section
This section are used by `cerberus vm make` command. This section are setup for specific category to be used on specific resource, which mean if there is no value on the list of variable, virtual machine would be used from `vcenter.environments.*` from selected `environment_identifier` as the component.
##### Variable reference
* `type`__*__ - Type of section
* `name`__*__ - Category name
* `name_format` - Same like `vcenter.environments.*` section. But only for selected category.
* `hostname_format` - Same like `vcenter.environments.*` section. But only for selected category.
* `network` - Same like `vcenter.environments.*` section. But only for selected category.
* `folder` - Same like `vcenter.environments.*` section. But only for selected category.
* `datastore`__**__ - vSphere datastore name. Example `DC-DS-RESOURCE-01`
* `datastore_cluster` - Same like `vcenter.environments.*` section. But only for selected category.
* `compute` - Same like `vcenter.environments.*` section. But only for selected category.
* `template` -
* `template_path` - Same like `vcenter.environments.*` section. But only for selected category.
######IMPORTANT!! 
* __*__ This variable are **required**, which mean virtual machine creation would be used all the variable from category as **default** variable of the virtual machine component with the selected category.
* __**__ Avoid define this 2 kind variable of `datastore` and `datastore_cluster` in the same section, because this would be bother on virtual machine creation process.

#### The `knife` Section
This section are used by `cerberus vm make` command with using `--bootstrap` option. This is only works if the infrastructure use Chef [Knife](https://docs.chef.io/knife.html) as the bootstrapper on virtual machine.
##### Variable reference
* `ssh_user` - Chef SSH username credential.
* `ssh_pwd` - Chef SSH password credential.
* `ssh_port` - Chef SSH port to be used.
* `databag_secret_path` - Chef databag secret path.

#### The `knife.environments.<environment_identifier>` Section
This section are used by `cerberus vm make` command with using `--bootstrap` option. This section have similar structure from `vcenter.environments.*`.
##### Variable reference
* `name`__*__ - Environment name.
* `chef_environment`__*__ - Chef environment name.
* `runlist`__*__ - Selected runlist to be used on bootstrap process.
  
#### The `knife.categories.<environment_identifier>.<category_identifier>` Section
This section are used by `cerberus vm make` command with using `--bootstrap` option. This section have similar structure from `vcenter.categories.*`.
##### Variable reference
* `name`__*__ - Environment name.
* `runlist`__*__ - Selected runlist to be used on bootstrap process.

#### The `phpipam` Section
This section are used by `cerberus ipam` command.

##### Variable reference
* `app_id` - phpIPAM App Identifier. You can get this information from API page.
* `endpoint` - phpIPAM endpoint.
* `user` - phpIPAM user credential.
* `pwd` - phpIPAM user password credential.

#### The `dns` Section
This section are used by `cerberus dns` command.

##### Variable reference
* `rtype` - Record type (A|CNAME|PTR|MX|SRV).
* `ttl` - Time to live in second.

#### The `dns.zones` Section
This section are used by `cerberus dns` command.
##### Variable reference
* `available` - This available use for prevent available zones that could work on `cerberus dns make` command.

#### The `dns.zones.<zone_identifier>` Section
This section are used by `cerberus dns` command. This is a must section to be fill, you can not work with all zones available in `dns.zones` if there is no information about the zone in this section.
##### Variable reference
* `name` - DNS zone name.
* `server` - DNS server from selected zone.
* `keyring_name` - DNS zone keyring name.
* `keyring_value` - DNS zone keyring value.

#### Additional Information (Configuration File)
##### Using `inherit` variable
To prevent duplication data and stay on DRY principle, you can use `inherit` variable on every section. In some case, maybe you want to set component on specific category in `vcenter.categories.*` section used multiple times, so instead duplicate variable on each category you can use an __*abstract-like*__ section to be used multiple times on others category section. For example:
```
[vcenter.categories.production.db]
type = category
name = Database
datastore_cluster = DC-SDRS-PROD-DB-01
template = database-vm-template
template_path = Templates/Databases

[vcenter.categories.production.postgres]
type = category
name = PG
template = postgres-vm-template

[vcenter.categories.production.mongo]
type = category
name = MONGO
compute = ClusterCompute/Database/Mongo
template = mongo-vm-template
```