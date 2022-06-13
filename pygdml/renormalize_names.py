
def remove_invalid(name):
    """
    Removes invalid characters from a name in a gdml file

    Args:
        name (str) : A name of an object in the gdml file
    """

    clean_name = name\
       .replace(',','')\
       .replace('-','')\
       .replace('#','')\
       .replace('?','')\
       .replace(' ','')\
       .replace('}','')\
       .replace('{','')\
       .replace('.','')\
       .replace('x','')
       # no x because it will look like a memory address
       # e.g. 0x333
    return clean_name

#############################################################3

def normalize_name(name):
    """
    In the gdml file, it seems that the name for the parts follows a
    pattern of <whatevername>-id
    We want to split of the id by two underscores and the
    clean the rest of the name
    """
    # never normalize anything world like
    if 'orld' in name:
        return name
    parts = name.split('-')
    id = parts[-1]
    parts = ''.join(parts[:-1])
    parts = remove_invalid(parts)
    return parts + f'__uid{id}'
