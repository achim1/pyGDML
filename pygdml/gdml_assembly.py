
import bs4
import logging
LOG = logging
try:
    import hepbasestack as hep
    from . import __package_loglevel__
    LOG = hep.logger.get_logger(__package_loglevel__)
except ImportError:
    pass

from .gdml_parsers import extract_tessellated_solids

def get_physvols_from_subassembly(filename):
    """
    Extract the physical volumes which belong to a single
    subassembly and name them as belonging together.

    Args:
        filename:

    Returns:

    """
    return

##############################################################

def get_tsolids_from_subassembly(filename, first_identifier=0):
    """
    Open a file and get the tessellated solids
    """
    LOG.info(f"Will check {filename} for subassembly!")
    gdml = bs4.BeautifulSoup(open(filename), features="lxml-xml")

    # assume we have materials
    cursor = gdml.gdml.find_next()
    #cursor = gdml.gdml.materials
    #if cursor is None:
    #    LOG.warn(f"No material definitions in {filename}")
   #     cursor = bs.gdml.define
    all_tessell_solids = extract_tessellated_solids(cursor,\
                                                    tessellsolid_identifier=first_identifier)
    del gdml
    return all_tessell_solids
