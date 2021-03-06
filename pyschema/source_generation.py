from pyschema import types
import pyschema

DEFAULT_INDENT = " " * 4


def to_python_source(classes, indent=DEFAULT_INDENT):
    """Convert a set of pyschemas to executable python source code

    Currently supports all built-in types for basic usage.

    Notably not supported:
    * Maintaining class hierarchy
    * Methods, properties and non-field attributes
    * SELF-references
    """
    return header_source() + "\n" + classes_source(classes, indent)


def classes_source(classes, indent=DEFAULT_INDENT):
    all_classes = set(classes)
    for c in classes:
        referenced_schemas = find_subrecords(c)
        all_classes |= set(referenced_schemas)

    ordered = sorted(all_classes, cmp=ref_comparator)
    return "\n\n".join([_class_source(c, indent) for c in ordered])


def header_source():
    """Get the required header for generated source"""
    return (
        "import pyschema\n"
        "from pyschema.types import *"
        "\n"
    )


def _class_source(schema, indent):
    """Generate Python source code for one specific class

    Doesn't include or take into account any dependencies between record types
    """

    def_pattern = (
        "class {class_name}(pyschema.Record):\n"
        "{indent}# WARNING: This class was generated by pyschema.to_python_source\n"
        "{indent}# there is a risk that any modification made to this class will be overwritten\n"
        "{optional_namespace_def}"
        "{field_defs}\n"
    )
    if hasattr(schema, '_namespace'):
        optional_namespace_def = "{indent}_namespace = {namespace!r}\n".format(
            namespace=schema._namespace, indent=indent)
    else:
        optional_namespace_def = ""

    field_defs = [
        "{indent}{field_name} = {field!r}".format(field_name=field_name, field=field, indent=indent)
        for field_name, field in schema._fields.iteritems()
    ]
    if not field_defs:
        field_defs = ["{indent}pass".format(indent=indent)]

    return def_pattern.format(
        class_name=schema._schema_name,
        optional_namespace_def=optional_namespace_def,
        field_defs="\n".join(field_defs),
        indent=indent
    )


def ref_comparator(a, b):
    """Comparator used to sort pyschema classes in referential order

    i.e. if schema A references schema B in a subrecord, it needs to be
    defined first of the two
    """

    if has_directed_link(a, b):
        # a refers to b, so it should come after b in the sort order
        return 1
    elif has_directed_link(b, a):
        return -1
    else:
        return 0


def find_subrecords(a, include_this=False):
    subs = set()
    if pyschema.ispyschema(a):
        if include_this:
            subs.add(a)
        for _, field in a._fields.iteritems():
            subs |= find_subrecords(field, True)
    elif isinstance(a, types.List):
        subs |= find_subrecords(a.field_type, True)
    elif isinstance(a, types.Map):
        subs |= find_subrecords(a.value_type, True)
    elif isinstance(a, types.SubRecord):
        subs |= find_subrecords(a._schema, True)
    return subs


def has_directed_link(a, b):
    # TODO: refactor to use find_subrecords instead
    #       to reduce duplication
    if pyschema.ispyschema(a):
        if a == b:
            return True
        for _, field in a._fields.iteritems():
            if has_directed_link(field, b):
                return True
    elif isinstance(a, types.List):
        if has_directed_link(a.field_type, b):
            return True
    elif isinstance(a, types.Map):
        if has_directed_link(a.value_type, b):
            return True
    elif isinstance(a, types.SubRecord):
        if has_directed_link(a._schema, b):
            return True
    return False
