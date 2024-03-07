import os
import json
import xml.etree.ElementTree as ET
import yaml
import unittest
from jinja2 import Environment, FileSystemLoader

class PKLError(Exception):
    """Base class for PKL-related errors with detailed context."""
    def __init__(self, message, path=None, additional_info=None):
        super().__init__(message)
        self.path = path
        self.additional_info = additional_info

    def __str__(self):
        base_message = super().__str__()
        if self.path:
            base_message += f" at '{self.path}'"
        if self.additional_info:
            base_message += f". {self.additional_info}"
        return base_message

class Parser:
    def parse(self, content):
        raise NotImplementedError

class JSONParser(Parser):
    def parse(self, content):
        try:
            return json.loads(content)
        except json.JSONDecodeError as e:
            raise PKLError("JSON parsing failed", additional_info=str(e))

class XMLParser(Parser):
    def parse(self, content):
        try:
            root = ET.fromstring(content)
            return self.parse_xml_recursive(root)
        except ET.ParseError as e:
            raise PKLError("XML parsing failed", additional_info=str(e))

    def parse_xml_recursive(self, element):
        result = {}
        for child in element:
            if child.tag in result:
                if isinstance(result[child.tag], list):
                    result[child.tag].append(self.parse_xml_recursive(child))
                else:
                    result[child.tag] = [result[child.tag], self.parse_xml_recursive(child)]
            else:
                result[child.tag] = self.parse_xml_recursive(child) if len(child) > 0 else child.text
        return result

class YAMLParser(Parser):
    def parse(self, content):
        try:
            return yaml.safe_load(content)
        except yaml.YAMLError as e:
            raise PKLError("YAML parsing failed", additional_info=str(e))

class PKLParser:
    def __init__(self, template_dir='templates'):
        self.env = Environment(loader=FileSystemLoader(template_dir))

    def parse(self, pkl_content, file_type):
        template = self.env.get_template('pkl_structure.j2')
        rendered_template = template.render(pkl_content=pkl_content)
        parser = {
            'json': JSONParser(),
            'xml': XMLParser(),
            'yaml': YAMLParser()
        }.get(file_type)
        if not parser:
            raise PKLError("Unsupported file type")
        return parser.parse(rendered_template)

class PKLConfig:
    def __init__(self, config_data):
        self.config = config_data

    def get(self, path, expected_type):
        value = self.config
        for key in path.split('.'):
            value = value[key]
        if not isinstance(value, expected_type):
            raise PKLError(f"Expected {expected_type} but got {type(value)} for path '{path}'")
        return value

    def validate_with_constraints(self, path, validator):
        value = self.get(path, object)
        if not validator(value):
            raise PKLError(f"Validation failed for {path}")

class PKLImportHandler:
    def __init__(self, base_path):
        self.base_path = base_path

    def import_file(self, file_name, file_type):
        file_path = os.path.join(self.base_path, file_name)
        with open(file_path, 'r') as file:
            content = file.read()
        return PKLParser().parse(content, file_type)

class PKLClassRegistry:
    def __init__(self):
        self.classes = {}

    def define_class(self, class_name, class_definition):
        self.classes[class_name] = class_definition

    def instantiate_class(self, class_name, **kwargs):
        class_definition = self.classes.get(class_name)
        if not class_definition:
            raise PKLError(f"Class {class_name} not defined.")
        return class_definition(**kwargs)

class PKLReferenceResolver:
    @staticmethod
    def resolve_references(config_data):
        for key, value in config_data.items():
            if isinstance(value, str) and value.startswith("$ref:"):
                ref_path = value[5:]
                config_data[key] = PKLReferenceResolver.get_value_by_path(config_data, ref_path.split('.'))
            elif isinstance(value, dict):
                PKLReferenceResolver.resolve_references(value)
    
    @staticmethod
    def get_value_by_path(data, path):
        for key in path:
            data = data.get(key)
            if data is None:
                break
        return data

def when(condition, true_branch, false_branch=None):
    return true_branch if condition else false_branch

def for_generator(iterable, transformation):
    return [transformation(item) for item in iterable]

class PKLConfigDynamic(PKLConfig):
    def get_dynamic(self, path):
        value = self.config
        for key in path.split('.'):
            value = value.get(key)
        return value

def is_valid_hostname(hostname):
    return isinstance(hostname, str) and len(hostname) > 0

class PKLCustomTypeSystem:
    type_registry = {}

    @staticmethod
    def register_type(type_name, validation_func):
        PKLCustomTypeSystem.type_registry[type_name] = validation_func

    @staticmethod
    def validate(data, type_name):
        validator = PKLCustomTypeSystem.type_registry.get(type_name)
        if not validator:
            raise PKLError(f"Type '{type_name}' is not registered.")
        if not validator(data):
            raise PKLError(f"Validation failed for type '{type_name}'.", additional_info=f"Data: {data}")

class TestPKLConfig(unittest.TestCase):
    def test_get_existing_value(self):
        config = PKLConfig({'server': {'host': 'localhost'}})
        host = config.get('server.host', str)
        self.assertEqual(host, 'localhost')

if __name__ == "__main__":
    unittest.main()
