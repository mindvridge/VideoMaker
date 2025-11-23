"""
Mutmut configuration for mutation testing.
https://mutmut.readthedocs.io/
"""


def pre_mutation(context):
    """
    Called before each mutation is applied.
    Return False to skip this mutation.
    """
    # Skip mutations in certain files
    skip_files = [
        'tests/',
        'migrations/',
        '__pycache__',
    ]

    for skip_file in skip_files:
        if skip_file in context.filename:
            return False

    return True


def pre_mutation_test(context, line, mutant):
    """
    Called before running tests for a specific mutant.
    """
    pass


# Configuration dictionary
dict_synonyms = [
    'Struct',
    'Config',
]
