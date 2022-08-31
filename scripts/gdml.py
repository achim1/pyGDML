#! /usr/bin/env python

import bs4
import os
import os.path
import tqdm
import sys
import time
from copy import copy, deepcopy

from pygdml.gdml_parsers import extract_tessellated_solids
from pygdml.renormalize_names import normalize_name
from pygdml.gdml_file import GdmlFileMinimal
from pygdml.gdml_physvol import GdmlPhysVol

import logging
LOG = logging
try:
    import hepbasestack as hep
    from pygdml import __package_loglevel__
    LOG = hep.logger.get_logger(__package_loglevel__)
    del logging
except ImportError:
    pass

#######################################
# FIXME - triangle vertex check. 
# Geant4 currently has a limit where it
# is not processing triangles smaller 
# than a certain area 
# there is delta  = worldextent(in mm)*1e-11
# (it is called kCarTolerance)
# then there are 2 checks:
#   G4double leng1 = fE1.mag();
#   G4double leng2 = (fE2-fE1).mag();
#   G4double leng3 = fE2.mag();
#   if (leng1 <= delta || leng2 <= delta || leng3 <= delta)
#   {
#     fIsDefined = false;
#   }
# and 
#   // Check min height of triangle
#   //
#   if (fIsDefined)
#   {
#     if (2.*fArea/std::max(std::max(leng1,leng2),leng3) <= delta)



##################################


def reformat(name, extra_count, extra2):
    """
    Reformat vertex names. Add additional counters for identification

    Args:
        name:
        extra_count:
        extra2:

    Returns:
        str : new (reformatted) name
    """
    rname = 'v' + name + '_' + str(extra_count) + '_' + str(extra2)
    return rname

##################################

def g4_validator(infile):
    """
    Use the Geant4 GDML parser to validate the gdml file.
    This will only check, not fix anything

    args:
        infile (str) : path to the .gdml file in question
    """
    try:
        import Geant4.G4gdml as gd
    except ImportError as e:
        raise ImportError('This requires geant4 compiled with pybindings and in your PYTHONPATH, so that we can import Geant4.G4gdml')
    print ('Validating...')
    parser = gd.G4GDMLParser()
    parser.Read(infile, True) # the second
                                   # argument is 
                                   # validation
    world = parser.GetWorldVolume()
    checked_file = infile.replace('.gdml', 'whatg4sees.gdml')
    if os.path.exists(checked_file):
        os.remove(checked_file)
    parser.Write(checked_file, world)
    print ('Validation done. Inspect output...')

##################################
    
def fix_names(gdml):
    """
    In the case that the vertex names are just simple integers,
    fix them.

    Args:
        gdml (BeautifulSoup) : input gdml 
    """
    # first, we remove all invalid characters

    print (f'===> Removing invalid characters from xml-tree!')
 
    tess       = gdml.find_all("tessellated") #, limit=10) 
    sref       = gdml.find_all("solidref") #, limit=10) 
    vref       = gdml.find_all("volumeref")
    lvols      = gdml.find_all("volume")
    physvol    = gdml.find_all("physvol")
    poss       = gdml.find_all("position")
    possref    = gdml.find_all("positionref")   
    tris       = gdml.find_all("triangular")
 
    for k in tqdm.tqdm(vref, desc='cleaning volumerefs'):
        k.attrs['ref']  = normalize_name(k.attrs['ref'])
    for k in tqdm.tqdm(physvol, desc='cleaning physvols'):
        k.attrs['name'] = normalize_name(k.attrs['name'])
    for k in tqdm.tqdm(tess, desc='cleaning tesselated solids'):
        k.attrs['name'] = normalize_name(k.attrs['name'])
    for k in tqdm.tqdm(lvols, desc='cleaning volumes'):
        k.attrs['name'] = normalize_name(k.attrs['name'])
    for k in tqdm.tqdm(sref, desc='cleaning tessellateds'):
        k.attrs['ref']  = normalize_name(k.attrs['ref'])
    for k in tqdm.tqdm(poss, desc='cleaning posiitions'):
        k.attrs['name']  = normalize_name(k.attrs['name'])
    for k in tqdm.tqdm(possref, desc='cleaning positionref'):
        k.attrs['ref']  = normalize_name(k.attrs['ref'])
    for k in tqdm.tqdm(tris, desc='cleaning triangulars'):
        k.attrs['vertex1']  = normalize_name(k.attrs['vertex1'])
        k.attrs['vertex2']  = normalize_name(k.attrs['vertex2'])
        k.attrs['vertex3']  = normalize_name(k.attrs['vertex3'])

    print (f'===> DONE!')
    time.sleep(2)


    n_define = 0
    namestore = {}
    cc = 0 #continuous_counter
    defines = gdml.find_all('define')
    solids  = gdml.find_all('solids')
    if (len(defines) != len(solids)):
        raise ValueError(f'We have {len(solids)} solids for {len(defines)}')


    ndefines = len(defines)
    seed = gdml.gdml.find_next()
    while seed is not None:
        LOG.debug(f'Found seed with name {seed.name}')
        if seed.name == 'define':
            LOG.debug('found define')
            nkid = 0
            for kid in seed.findChildren():
                try:
                    int(kid.attrs['name'])
                except:
                    LOG.debug (f"Won't fix namestore {kid}")
                    continue
                #kid.name = clean(kid.name)
                old_name = kid.attrs['name']
                newname = reformat(old_name, nkid,cc)
                namestore[old_name] = newname
                kid.attrs['name'] = newname
                nkid += 1
                cc += 1
            n_define += 1
            seed = seed.findNextSibling()
            continue

        if seed.name == 'solids':
            kid_count = 0
            print ('found solids')
            print (len(namestore.keys()))
            for kid in seed.findChildren():
                #kid.name = clean(kid.name)
                if kid.name == 'triangular':
                    for v in 1,2,3:
                        oldname = kid.attrs[f'vertex{v}']
                        try:
                            kid.attrs[f'vertex{v}'] = namestore[oldname]
                        except KeyError:
                            print (kid, oldname)
                            #raise
                    #kid.ref  = namestore[kid.name]
            # reset the namestore for the next section
                    kid_count += 1 
            print (kid_count)
            seed = seed.findNextSibling()
            continue
        else:
            print ('reseting')
            # we are done with this section
            seed = seed.findNextSibling()
    # now we clean every name
    #seed = gdml.gdml.materials
    #while seed is not None:
    #    seed.name = clean(seed.name)
    #    for kid in seed.findChildren():
    #        kid.name = clean(kid.name)
    print ('part 1 done')
    return gdml



if __name__ == '__main__':
    
    import argparse
    import os
    
    parser = argparse.ArgumentParser(description='Work with .gdml files coming from the conversion from CAD files with MRADSim. The issue can be that there are invalid symbols, invalid triangles for the surfaces of the tesseleated solids and so on.')
    parser.add_argument('infile', metavar='infile', type=str,
                        help='Input .gdml file')
    parser.add_argument('--validation-check', dest='validation_check',
                        action='store_true',
                        help='Check if the file is valid gdml with the G4GDMLParser. Do not fix anything. Exit after validation check.')
    parser.add_argument('--fix-names',  dest='fix_names',
                        action='store_true',
                        help='Fix names with invalid symbols')

    args = parser.parse_args()

    if args.validation_check:
        g4_validator(args.infile)    
        sys.exit(0)

    if args.infile.endswith('.cmpr.gdml'):
        raise ValueError('File has been compressed already, nothing to do!')

    if args.fix_names: 
        bs = bs4.BeautifulSoup(open(args.infile),features="lxml-xml")
        fix_names(bs)
        print (f'Will work on {args.infile}')
        fixed_file = open(args.infile.replace('.gdml', '.fix.gdml'),'w')
        fixed_file.write(bs.prettify())
        print ('names fixed. Exiting!')
        sys.exit(0)
    else:
        bs = bs4.BeautifulSoup(open(args.infile),features="lxml-xml")


    outfileX = args.infile.replace('.gdml','.cmprX.gdml')
    if os.path.exists(outfileX):
        os.remove(outfileX)
    outfile = args.infile.replace('.gdml','.cmpr.gdml')
    compressed_file = GdmlFileMinimal(outfileX)
    try:
        compressed_file.copy_materials_from_file(args.infile)
    except IndexError as e:
        print (f'Exception, file most likely does not contain any materials! {e}')
    compressed_file.add_antarctic_air_material()
    print(f'Materials copied from {args.infile}')
    print (f'Will work on {args.infile} and save the result to {outfile}')
    
    # the organization of the gdml file is the
    # follows
    # gdml
    
    nkids = 0
    cursor = bs.gdml.materials
    # there might be no materials, in 
    # taat case we move on to the first
    # define 
    has_materials = True
    if cursor is None:
        cursor = bs.gdml.define
        has_materials = False
    ntess = 0 # how many tessellated solids
              # per section
    
    # write everything to a new file
    tags_to_write = []
    solid_tags_to_write = []
    
    cleaned_file = open(outfile, 'w')
    nkids = len(cursor.findAll())
    
    vertex_template     = None
    triangular_template = None

    all_tessell_solids = extract_tessellated_solids(cursor,\
                                                    solid_tags_to_write,\
                                                    tags_to_write)
    bs.gdml.clear()


    # the materials
    if has_materials:
        bs.gdml.append(tags_to_write[0])
        tags_to_write.remove(tags_to_write[0])

    #for k in solid_tags_to_write:
    empties = 0
    for ts in tqdm.tqdm(all_tessell_solids, desc='Processing triangles...'):
        if not ts.nvertices:
            empties += 1
            continue
        ts.remove_invalid_triangles()
    
        bs.gdml.append(ts.create_define_tag())
        bs.gdml.append(ts.create_solid_tag(no_name_change=True))
    
        #print (f'Saw {ts.ntriangles} triangles and {ts.ninvalidtri} invalid triangles')
        #print (f'There were {empties} empty vertices which were not processed!')
    
    # this is typically the worldbox
    for tag in solid_tags_to_write:
        print (f'Writing additional solid tags {tag}..')
        bs.gdml.append(tag)
    
    # these are setup and so on
    for tag in tags_to_write:
        print (f'Writing additional tags {tag}..')
        # FIXME - we fix volumeref, solidref and volume
        # name, for the tessellated solids
        bs.gdml.append(tag)
    
    cleaned_file.write(bs.prettify())
    cleaned_file.close()

    # now we write the file following the new scheme
    for ctr, tess in enumerate(all_tessell_solids):
        tess.translate_to_center_mass()
        tess.remove_invalid_triangles()
        #tess.position = (0,0,0)
        physvol = GdmlPhysVol(tess.name, tess.position, solid=tess,\
                              material="ALUMINUM", counter=ctr)
        physvol.register_myself(compressed_file)
    compressed_file.add_world([10000, 10000, 10000])
    compressed_file.write_to_file()

    print (all_tessell_solids)

    
