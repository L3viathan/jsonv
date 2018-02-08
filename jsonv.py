#!/usr/bin/env python3
"""JSON validator

Usage:
    jsonv.py validate [-l] <schema> <file>

Options:
    -l --jsonl      Assume linewise JSON and test schema on each line

"""
import json
import docopt


class ValidationError(Exception):
    pass


typemap = {
    # oneof, noneof
    "string": (str, tuple),
    "int": (int, bool),
    "float": (float, tuple),
    "number": ((int, float), bool),
    "bool": (bool, tuple),
    "array": (list, tuple),
    "object": (dict, tuple),
}

references = {}


def schema_validate(obj, schema):
    # References
    if schema.get("$schema:ref"):
        return schema_validate(obj, references[schema["$schema:ref"]])
    if schema.get("$schema:id"):
        references[schema["$schema:id"]] = schema

    # General checks
    type_oneof, type_noneof = typemap[schema["$schema:type"]]
    if not isinstance(obj, type_oneof) or isinstance(obj, type_noneof):
        raise ValidationError("Invalid type: {} should be {}".format(type(obj), type_oneof))

    minlength = schema.get("$schema:minlength")
    if minlength and len(obj) < minlength:
        raise ValidationError("Not enough elements (at least {} required)".format(minlength))

    # Recursion
    if isinstance(obj, dict):
        for key in schema:
            if key.startswith("$schema:"):
                continue
            if key not in obj and schema[key].get("$schema:required", True):
                raise ValidationError("Missing key: {}".format(key))
        for key in obj:
            if key not in schema:
                raise ValidationError("Additional key: {}".format(key))
            schema_validate(obj[key], schema[key])
    elif isinstance(obj, list):
        for element in obj:
            schema_validate(element, schema["$schema:elements"])


def validate(jsonstr, schema):
    """Validate a string to be schema-valid JSON."""
    try:
        obj = json.loads(jsonstr)
    except json.decoder.JSONDecodeError as e:
        raise ValidationError("Invalid JSON") from None
    schema_validate(obj, schema)


if __name__ == '__main__':
    args = docopt.docopt(__doc__)
    with open(args['<schema>']) as f:
        schema = json.load(f)
    with open(args['<file>']) as f:
        if args["--jsonl"]:
            for line in f:
                validate(line, schema)
        else:
            validate(f.read(), schema)
