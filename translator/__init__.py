"""OC -> SONiC configuration JSON translator.

The translator is driven entirely by the supplier mapping table
(``yang2sonic_maptable``).  Each CSV row is a template: a pattern over the
flattened OC tree, a value selector DSL, one or more SONiC key templates and a
value DSL aligned with them.

Modules
-------
``rules``    load and parse the mapping table
``ocdoc``    flatten the OC document and look paths up
``values``   value DSL evaluation (selectors, templates, transforms)
``engine``   match rules to OC leaves and emit the SONiC configuration
``cli``      command line entry point
"""

__version__ = "1.0.0"
