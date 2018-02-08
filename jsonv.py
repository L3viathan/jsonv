#!/usr/bin/env python3
"""JSON validator

Usage:
    jsonv.py validate [-l] <schema> <file>

Options:
    -l --jsonl      Assume linewise JSON and test schema on each line

"""
import re
import json
import docopt


class ValidationError(Exception):
    """Generic validation error"""
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


def validate_type(obj, schema):
    """Validate that the type matches."""
    if schema.get("$schema:type"):
        type_oneof, type_noneof = typemap[schema["$schema:type"]]
        if not isinstance(obj, type_oneof) or isinstance(obj, type_noneof):
            raise ValidationError(
                "Invalid type: {} should be {}".format(
                    type(obj),
                    type_oneof,
                )
            )


def validate_minlength(obj, schema):
    """Validate that the array has the right length."""
    minlength = schema.get("$schema:minlength")
    if minlength and len(obj) < minlength:
        raise ValidationError(
            "Not enough elements (at least {} required)".format(
                minlength,
            )
        )


def validate_name(schema, key=None):
    """Validate that the name matches the given regex."""
    if key is not None and schema.get("$schema:regex"):
        if not re.match(schema["$schema:regex"], key):
            raise ValidationError(
                "Key {} does not conform to regex /{}/".format(
                    key,
                    schema["$schema:regex"],
                )
            )


def validate_object(obj, schema):
    """Validate an object against the schema."""
    for skey in schema:
        okey = skey
        if skey.startswith("$schema:"):
            continue
        if skey.startswith("$$"):
            okey = skey[1:]
        if okey not in obj and schema[skey].get("$schema:required", True):
            raise ValidationError("Missing key: {}".format(okey))
    for okey in obj:
        skey = okey
        if okey.startswith("$"):
            skey = "$" + okey
        if skey not in schema:
            if not schema.get("$schema:any"):
                raise ValidationError("Additional key: {}".format(okey))
            else:
                schema_validate(obj[okey], schema["$schema:any"], okey)
        else:
            schema_validate(obj[okey], schema[skey])


def validate_array(obj, schema):
    """Validate an array against the schema."""
    for element in obj:
        schema_validate(element, schema["$schema:elements"])


def schema_validate(obj, schema, key=None):
    """Validate an arbitrary JSON value against the schema."""
    # References
    if schema.get("$schema:ref"):
        return schema_validate(obj, references[schema["$schema:ref"]])
    if schema.get("$schema:id"):
        references[schema["$schema:id"]] = schema

    # General checks
    validate_type(obj, schema)
    validate_minlength(obj, schema)
    validate_name(schema, key)

    # Recursion
    if isinstance(obj, dict):
        validate_object(obj, schema)
    elif isinstance(obj, list):
        validate_array(obj, schema)


def validate(jsonstr, schema):
    """Validate a string to be schema-valid JSON."""
    try:
        obj = json.loads(jsonstr)
    except json.decoder.JSONDecodeError:
        raise ValidationError("Invalid JSON") from None
    schema_validate(obj, schema)


if __name__ == '__main__':
    ARGS = docopt.docopt(__doc__)
    with open(ARGS['<schema>']) as f:
        SCHEMA = json.load(f)
    with open(ARGS['<file>']) as f:
        if ARGS["--jsonl"]:
            for line in f:
                validate(line, SCHEMA)
        else:
            validate(f.read(), SCHEMA)
