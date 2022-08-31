#! /usr/bin/env python

import os
import hjson

import pygdml
pygdml.set_package_loglevel(30)

from pygdml.gdml_solid import GdmlBox
from pygdml.gdml_physvol import GdmlPhysVol
from pygdml.gdml_file import GdmlFileMinimal
from pygdml.gdml_assembly import get_tsolids_from_subassembly

import logging
LOG = logging
try:
    import hepbasestack as hep
    LOG = hep.logger.get_logger(20)
except ImportError:
    pass

try:
    os.remove('sandbox-test.gdml')
except Exception as e:
    print(e)

def multiplex_solids(assembly_solids, n=1):
    """
    If the same assembly appears multiple times,
    make the solid list accordingly, and use multiple
    identifiers
    Args:
        assembly_solids:

    Returns:

    """
    n_rep = len(assembly_solids)
    #identifiers = [s.identifier for s in assembly_solids]
    #min_i,max_i = min(identifiers),max(identifiers)
    assembly_solids = sorted(assembly_solids,\
                             key= lambda x : x.identifier)
    multiplexed_solids = []
    for k in range(n):
        for s in assembly_solids:
            s._identifier = s.identifier * k*n_rep
            multiplexed_solids.append(s)
    return multiplexed_solids


# create a box solid similar as we do in
# geant4
box = GdmlBox('mybox',10,10,10)
# this is more like a mix of logical and physical volume
# since it has a material as well
box_pv = GdmlPhysVol('mybox', [1,2,3],\
                     solid=box,\
                     material='aluminum')

ORIGIN = (0,0,0)
SCALE  = 1 - 1e-5
SCALE  = 0.8

geofile = GdmlFileMinimal('sandbox-test.gdml')

# materials

# some materials are already predefined
geofile.add_antarctic_air_material()

# mixed materials with name, formula and density
geofile.add_material('PVT', 'C9H19', 1.032)
# elemental materials just require the
# correct chemical symbol
geofile.add_elemental_material('Al')
geofile.add_elemental_material('C')

# add elements to the file
# the parts counter does have nothing
# to do with the volume id
parts_counter = 0

#######################################
# TOF-CORTINA
########################################
GLOBAL_PARTS_COUNTER = 0

tof_03pp               = 'tof-panels/tof-03pp.fix.cmprX.gdml'
tof_03pp_solids        = get_tsolids_from_subassembly(tof_03pp,\
                                                      first_identifier=GLOBAL_PARTS_COUNTER)
# we need to do this 3 more times:
ltof_03pp_solids = len(tof_03pp_solids)
GLOBAL_PARTS_COUNTER += ltof_03pp_solids
for k in range(3):
    tof_03pp_solids += get_tsolids_from_subassembly(tof_03pp,\
                                                    first_identifier=GLOBAL_PARTS_COUNTER)
    GLOBAL_PARTS_COUNTER += ltof_03pp_solids

tof_03pp_meta          = hjson.load(open('tof-03pp.meta.json'))
tof_03pp_meta          = tof_03pp_meta['functional_parts']

# we have 4 times the 03pp panel
tof_03pp_translations = []
tof_03pp_translations.extend([(0,0,0)]*ltof_03pp_solids)
tof_03pp_translations.extend([(0,0,1000)]*ltof_03pp_solids)
tof_03pp_translations.extend([(0,0,2000)]*ltof_03pp_solids)
tof_03pp_translations.extend([(0,0,3000)]*ltof_03pp_solids)
#tof_03pp_solids = tof_03pp_solids*4
#tof_03pp_solids = multiplex_solids(tof_03pp_solids, n=4)

#GLOBAL_PARTS_COUNTER += len(tof_03pp_solids)

#######################################
# TOF-CUBE
########################################
npanels_cube_12pp       = 2

tof_12pp                = 'tof-panels/tof-12pp.fix.cmprX.gdml'
tof_12pp_solids         = get_tsolids_from_subassembly(tof_12pp,
                                                       first_identifier=GLOBAL_PARTS_COUNTER)
ltof_12pp_solids = len(tof_12pp_solids)
GLOBAL_PARTS_COUNTER += ltof_12pp_solids
for k in range(1):
    tof_12pp_solids = get_tsolids_from_subassembly(tof_12pp,
                                                   first_identifier=GLOBAL_PARTS_COUNTER)
    GLOBAL_PARTS_COUNTER += ltof_12pp_solids
tof_12pp_meta           = hjson.load(open('tof-12pp.meta.json'))
tof_12pp_meta           = tof_12pp_meta['functional_parts']

tof_12pp_translations   = []
for y in (-2000,2000):
    tof_12pp_translations.extend([(0,y,0)]*ltof_12pp_solids)

tof_12pp_rotations = []
tof_12pp_rotations.extend(['identity']*ltof_12pp_solids)
tof_12pp_rotations.extend(['identity']*ltof_12pp_solids)
#tof_12pp_solids         = tof_12pp_solids*npanels_cube_12pp
#tof_12pp_solids = multiplex_solids(tof_12pp_solids, n=2)
#GLOBAL_PARTS_COUNTER += len(tof_12pp_solids)

inner_cube              = 'cube-frame-600.fix.cmpr.gdml'
inner_cube_solids       = get_tsolids_from_subassembly(inner_cube,\
                                                       first_identifier=GLOBAL_PARTS_COUNTER)
GLOBAL_PARTS_COUNTER += len(inner_cube_solids)

inner_cube_meta         = hjson.load(open('cube-frame-600.meta.json'))
inner_cube_meta         = inner_cube_meta['functional-parts']

inner_cube_translations = []
inner_cube_translations.extend([(0,0,0)]*len(inner_cube_solids))

################################################3
# GAPS - ASSEMBLE!
#################################################

tof_solids = []
tof_translations = []
tof_solids.extend(tof_03pp_solids)
#tof_solids.extend(tof_12pp_solids)
#tof_solids.extend(inner_cube_solids)

tof_translations.extend(tof_03pp_translations)
#tof_translations.extend(tof_12pp_translations)
#tof_translations.extend(inner_cube_translations)

tof_meta = {}
tof_meta.update(tof_03pp_meta)
#tof_meta.update(tof_12pp_meta)
#tof_meta.update(inner_cube_meta)

print (len(tof_solids))

rotation_counter = dict()
material_counter = dict()
scale_counter    = dict()
no_meta_info     = []

for t, s in zip(tof_translations, tof_solids):
    print (t,s)
    print (s.name)

    if '__uid' in s.name:
        s.name = s.name.split('__uid')[0]
    #continue
    # set the default material to aluminum for now
    material = 'aluminum'
    s.translate_to_center_mass()
    #s.position = (0,0,0)

    global_part_name = None
    #print(s.name)

    for k in tof_meta:
        if s.name == k:
            global_part_name = k
            break
    if global_part_name is None:
        for k in tof_meta:
            if s.name.startswith(k):
                global_part_name = k
                break

    metadata = None
    print(f'GLOBAL PART {global_part_name}')

    rotation=None
    if global_part_name is not None:
        if not global_part_name in rotation_counter:
            rotation_counter[global_part_name] = 0
        if not global_part_name in material_counter:
            material_counter[global_part_name] = 0
        if not global_part_name in scale_counter:
            scale_counter[global_part_name] = 0

        metadata = tof_meta[global_part_name]
        metadata['generalized_name'] = global_part_name

        if 'tolerance' in metadata:
            tolerance = []
            for j in "xyz":
                 tolerance.append(1 - float(metadata['tolerance'][j]))

            s.scale(*tolerance)

        if 'scale' in metadata:
            if isinstance(metadata['scale'], list):
                tolerance = []
                for j in "xyz":
                    scx = float(metadata['scale'][scale_counter[global_part_name]])
                    tolerance.append(scx)

                #s.scale(*tolerance)
                s.scalefactors = tuple(tolerance)
                scale_counter[global_part_name] += 1

        if 'material' in metadata:
            if isinstance(metadata['material'], list):
                material = metadata['material'][material_counter[global_part_name]]
                material_counter[global_part_name] += 1
            else:
                material = metadata['material']

        if 'rotation' in metadata:
            rotation = metadata['rotation'][rotation_counter[global_part_name]]
            rotation_counter[global_part_name] += 1

    else:
        no_meta_info.append(s.name)
        continue

    if rotation == 'identity':
        rotation = None
    #s.position = (0,0,0)
    # general translation of the whole assembly
    s.position = (s.position[0] + t[0],\
                  s.position[1] + t[1],\
                  s.position[2] + t[2])

    if rotation is not None:
        s.rotation = rotation
    #print(f'Adding physvol {s.name} at position {s.position}, with metadata {metadata} and rotation {s.rotation} and material {material}')

    pv = GdmlPhysVol(s.name,\
                     s.position,\
                     solid=s,\
                     material=material,\
                     scale=s.scalefactors,\
                     metadata=metadata,
                     counter=parts_counter)
    if not rotation is None:
        for k in rotation:
            pass
            #pv.add_rotation(k,rotation[k])
    parts_counter += 1

    #pv = GdmlPhysVol(s.name, ORIGIN, solid=s, material=material)
    pv.register_myself(geofile)

# add elements to the file
#box_pv.register_myself(geofile)
#t_pv.register_myself(geofile)

geofile.add_world([10000,10000,10000])

geofile.write_to_file()
#print(geofile.bs.prettify())

print ("There is no meta info for the following parts:")
for k in no_meta_info:
    print(k)

overlap_check = False
if overlap_check:
    import Geant4.G4gdml as gd

    parse = gd.G4GDMLParser()
    parse.Read('sandbox-test.gdml')
    world = parse.GetWorldVolume()
    world.CheckOverlaps(1000, 3000, True)
    world.GetName()
    name = world.GetName()
    name.__str__()
    test = world.GetLogicalVolume()
    test.GetDaughter(0)
    dgtr = test.GetDaughter(0)
    dgtr.CheckOverlaps(1000, 0, True)
