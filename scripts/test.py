#! /usr/bin/env python

import pygdml
import pygdml.gdml_parsers as ps
import pygdml.gdml_file as gf
import pygdml.gdml_physvol

infile = gf.GdmlFileMinimal('tof-panels/tof-03pp.gdml')
solids = ps.extract_tessellated_solids(infile.bs.materials)
foo = solids[0]
foo.set_material('aluminum')
newfile = gf.GdmlFileMinimal('test.gdml')
newfile.add_elemental_material('Al')

gp = pygdml.gdml_physvol
foo_pv = gp.GdmlPhysVol(foo.name, [0,0,0], solid=foo, material=foo.material)
foo_pv.register_myself(newfile)
#foo.name = ps.normalize_name(foo.name)
foo.normalize_name()
newfile.add_world([10000]*3)
newfile.write_to_file()
newfile.add_antarctic_air_material()
newfile.write_to_file()
