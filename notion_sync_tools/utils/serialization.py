__all__ = ['SecretYamlObject']

from copy import copy

import yaml


class SecretYamlObject(yaml.YAMLObject):
    hidden_fields = []

    @classmethod
    def to_yaml(cls, dumper, data):
        new_data = copy(data)
        for item in cls.hidden_fields:
            del new_data.__dict__[item]
        return dumper.represent_yaml_object(cls.yaml_tag, new_data, cls, flow_style=cls.yaml_flow_style)
