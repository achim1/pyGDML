"""
GDML - geometry description markup language is a descriptor 
language for any geometry used in construction/simulation.
The open format is especially leveraged by the physics 
community within the commonly used software packages 
ROOT and Geant4.
This software shell:
- manipulate geometries on the GDML level
- verify/clean GDML files
- compress GDML files, since they can get quite 
  large. The compression uses the possibility 
  to reuse solids and just change their position/rotation

"""


__version__ = '0.0.1'
