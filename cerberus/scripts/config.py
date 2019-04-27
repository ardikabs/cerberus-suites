
import os
import click
import configparser
from click_configfile import (
    ConfigFileReader, 
    Param, 
    SectionSchema,
    matches_section,
    generate_configfile_names,
    select_params_from_section_schema,
    select_config_sections
)


class ConfigSectionSchema(object):
    """Describes all config sections of this configuration file."""

    @matches_section("DEFAULTS")
    class Defaults(SectionSchema):
        config_version = Param(type=str)

    @matches_section("vcenter")
    class Vcenter(SectionSchema):
        host = Param(type=str)
        port = Param(type=int)
        user = Param(type=str)
        pwd = Param(type=str)
        ssl = Param(type=bool)
        datacenter = Param(type=str)
        log = Param(type=click.Path())
        log_format = Param(type=str)
        zfill = Param(type=bool)
    
    @matches_section("vcenter.environments")
    class VCenterEnvironmentsAvailable(SectionSchema):
        available = Param(type=str, multiple=True)

    @matches_section("vcenter.networks.*")
    class VCenterNetworksComponent(SectionSchema):
        name = Param(type=str)
        dhcp = Param(type=bool)
        cidr = Param(type=str)
        domain = Param(type=str)
        dns = Param(type=str, multiple=True)

    @matches_section("vcenter.environments.*")
    class VCenterEnvironments(SectionSchema):
        type = Param(type=str)
        name = Param(type=str)
        prefix = Param(type=str)
        name_format = Param(type=str)
        hostname_format = Param(type=str)
        datastore = Param(type=str)
        datastore_cluster = Param(type=str)
        network = Param(type=str)
        compute = Param(type=str)
        template = Param(type=str)
        folder = Param(type=str)
        template = Param(type=str)
        template_path = Param(type=str)

    @matches_section("vcenter.categories.*")
    class VCenterCategory(SectionSchema):
        type = Param(type=str)
        name = Param(type=str)
        name_format = Param(type=str)
        hostname_format = Param(type=str)
        datastore = Param(type=str)
        datastore_cluster = Param(type=str)
        network = Param(type=str)
        compute = Param(type=str)
        template = Param(type=str)
        folder = Param(type=str)

    @matches_section("knife")
    class Knife(SectionSchema):
        ssh_user = Param(type=str)
        ssh_pwd = Param(type=str)
        ssh_port = Param(type=str)
        databag_secret_path = Param(type=click.Path())

    @matches_section("knife.environments.*")
    class KnifeEnvironments(SectionSchema):
        name = Param(type=str)
        chef_environment = Param(type=str)
        runlist = Param(type=str, multiple=True)


    @matches_section("knife.categories.*")
    class KnifeCategory(SectionSchema):
        name = Param(type=str)
        runlist = Param(type=str, multiple=True)

    @matches_section("phpipam")
    class PHPIPAM(SectionSchema):
        app_id = Param(type=str)
        endpoint = Param(type=str)
        user = Param(type=str)
        pwd = Param(type=str)

    @matches_section("dns")
    class DNS(SectionSchema):
        rtype = Param(type=str)
        ttl = Param(type=str)

    @matches_section("dns.zones")
    class DNSZoneAvailable(SectionSchema):
        available = Param(type=str, multiple=True)

    @matches_section("dns.zones.*")
    class DNSZoneItems(SectionSchema):
        name = Param(type=str)
        server = Param(type=str)
        keyring_name = Param(type=str)
        keyring_value = Param(type=str)

        
class ConfigFileProcessor(ConfigFileReader):
    config_files = ["cerberus.cfg", "cerberus.ini"]
    config_searchpath = [".", "/etc/cerberus"]
    config_section_schemas = [
        ConfigSectionSchema.Defaults,
        ConfigSectionSchema.Vcenter,
        ConfigSectionSchema.VCenterEnvironmentsAvailable,
        ConfigSectionSchema.VCenterNetworksComponent,
        ConfigSectionSchema.VCenterEnvironments,
        ConfigSectionSchema.VCenterCategory,
        ConfigSectionSchema.Knife,
        ConfigSectionSchema.KnifeEnvironments,
        ConfigSectionSchema.KnifeCategory,
        ConfigSectionSchema.PHPIPAM,
        ConfigSectionSchema.DNS,
        ConfigSectionSchema.DNSZoneAvailable,
        ConfigSectionSchema.DNSZoneItems,
    ]

    @property
    def config_path(self):
        import os
        cls = self.__class__
        config_param = Param(type=click.File('r'))
        configfile_names = list(generate_configfile_names(cls.config_files, cls.config_searchpath))

        if configfile_names:
            for name in configfile_names:
                config_file = config_param.parse(name)
                path = os.path.realpath(config_file.name)
        else:
            path = os.getcwd()
        return path

    @classmethod
    def read_config(cls):
        configfile_names = list(
            generate_configfile_names(cls.config_files, cls.config_searchpath))
        parser = configparser.ConfigParser(interpolation=None)
        parser.optionxform = str
        parser.read(configfile_names)

        if not cls.config_sections:
            # -- AUTO-DISCOVER (once): From cls.config_section_schemas
            cls.config_sections = cls.collect_config_sections_from_schemas()

        storage = {}
        for section_name in select_config_sections(parser.sections(),
                                                   cls.config_sections):
            # print("PROCESS-SECTION: %s" % section_name)
            config_section = parser[section_name]
            cls.process_config_section(parser, config_section, storage)
        return storage
        
    @classmethod
    def process_config_section(cls, parser_sections, config_section, storage):
        schema = cls.select_config_schema_for(config_section.name)
        if not schema:
            message = "No schema found for: section=%s"
            raise LookupError(message % config_section.name)

        # -- PARSE AND STORE CONFIG SECTION:
        section_storage = cls.select_storage_for(config_section.name, storage)
        section_data = parse_config_section(parser_sections, config_section, schema)
        section_storage.update(section_data)

def parse_config_section(parser, config_section, section_schema):

    storage = {}
    if config_section.get("inherit"):
        inherit_section = config_section.pop("inherit")
        inherit_schema = ConfigFileProcessor.select_config_schema_for(inherit_section)
        inherit_section_data = parse_config_section(
            parser, parser[inherit_section], inherit_schema)
        storage.update(inherit_section_data)

    for name, param in select_params_from_section_schema(section_schema):
        value = config_section.get(name, None)
        if value is None:
            if param.default is None:
                continue
            value = param.default
        else:
            value = param.parse(value)
        storage[name] = value
    return storage
