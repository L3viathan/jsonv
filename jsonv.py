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


def schema_validate(obj, schema, key=None):
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

    if key is not None and schema.get("$schema:regex"):
        if not re.match(schema["$schema:regex"], key):
            raise ValidationError("Key {} does not conform to regex /{}/".format(key, schema["$schema:regex"]))

    # Recursion
    if isinstance(obj, dict):
        for skey in schema:
            okey = skey
            if skey.startswith("$schema:"):
                continue
            if skey.startswith("$$"):
                okey = skey[1:]
            if okey not in obj and schema[skey].get("$schema:required", True):
                raise ValidationError("Missing key: {}".format(skey))
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
