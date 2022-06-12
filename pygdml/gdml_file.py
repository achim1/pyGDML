"""
Provides an interface to a gdml file
"""

import os
import os.path
import bs4
import periodictable as pt
import tqdm

from collections import defaultdict

from copy import copy

from .gdml_tags import VolumeTag, RotationTag

import dataclasses

@dataclasses.dataclass
class RegisteredVolume:
    name     : str
    material : str
import dataclasses


class GdmlFileMinimal(object):
    """
    A representation of a gdml file. Sort entries by classifications and
    then finally write it to disk
    """
    GDML_SCHEMA = { \
        'gdml': bs4.element.Tag(name='gdml', \
                                attrs={'xmlns:xsi': "http://www.w3.org/2001/XMLSchema-instance", \
                                       'xsi:noNamespaceSchemaLocation': "http://service-spi.web.cern.ch/service-spi/app/releases/GDML/schema/gdml.xsd"}),

        'define': bs4.element.Tag(name='define'),
        'materials': bs4.element.Tag(name='materials'),
        'solids': bs4.element.Tag(name='solids'),
        'structure': bs4.element.Tag(name='structure'),
        'setup': bs4.element.Tag(name='setup', \
                                 attrs={'name': 'Default', \
                                        'version': '1.0'})
    }

    def __init__(self, filename):
        self.filename = filename
        # this holds the actual tree
        # in case we read from a file
        self.bs = None
        # a lock, so we don't overwrite anything
        self.is_locked = False
        if os.path.exists(filename):
            print(f'Will parse {filename}')
            self.bs = bs4.BeautifulSoup(open(filename), features="lxml-xml")
            self.is_locked = True
        else:
            self.bs = bs4.BeautifulSoup('<?xml version="1.0" encoding="UTF-8" standalone="no" ?>', features='lxml-xml')
            # the current position inside the gdml tree
        self.cursor = None
        self.gdml = None
        # this holds the tree split up by
        # the sections as defined in schema
        # in case we are creating a new file
        self.schema = copy(GdmlFile.GDML_SCHEMA)
        # the extent of the world (if known)
        self.worldextent = (0, 0, 0)

        # since volumes can share the same solid
        # we keep track of "generalized names"
        # to identify which solid goes with which
        self.generalized_part_names   = []
        self.generalized_volume_names = []
        self.generalizcd_define_names = []

        # MATERIALS
        # keep track of every added [chemical] element
        self.element_registry = []
        # keep track of every added material
        self.material_registry = []
        # keep track of every added volume
        self.volume_registry = []
        # keep track of every added solid
        self.solid_registry  = []
        # and the physical volumes, these can be more than 1 per volume!
        self.physvol_registry = defaultdict(lambda: 0)
        # split up the materials in isotopes, elements and

        # materials
        self.isotope_tags = []
        self.element_tags = []
        self.material_tags = []

        # geometry
        self.structure_tags = []
        self.volume_tags = []
        self.solid_tags = []
        self.define_tags = []
        self.physvol_tags = []

    def copy_materials_from_file(self, filename):
        """
        Copy the whole material section from another file
        Args:
            filename:

        Returns:
            None
        """
        gdml = bs4.BeautifulSoup(open(filename), features="lxml-xml")
        materials = gdml.find_all('materials')[0]
        self.schema['materials'] = copy(materials)

    def add_define_tag(self, tag, generalized_part_name=None):
        if generalized_part_name in self.generalized_part_names:
            #print (f'WARN: <define name={tag.attrs["name"]} already registered!')
            return
        self.define_tags.append(tag)
        if generalized_part_name is not None:
            self.generalizcd_define_names.append(generalized_part_name)

    def add_solid_tag(self, tag, generalized_part_name=None):
        """

        Args:
            tag:
            unique_part_name:

        Returns:

        """
        if generalized_part_name in self.generalized_part_names:
            print (f'WARN: Solid {tag.attrs["name"]} already registered!')
            return
        if generalized_part_name is not None:
            self.generalized_part_names.append(generalized_part_name)
        self.solid_tags.append(tag)

    def add_volume_tag(self, tag, generalized_part_name=None):
        if generalized_part_name in self.generalized_volume_names:
            print (f'WARN: Solid {tag.attrs["name"]} already registered under {generalized_part_name}!')
            return
        if generalized_part_name is not None:
            tag.attrs['name'] = generalized_part_name + '_v'

        #if tag.attrs['name'] in self.volume_registry:
        #    # FIXME - this should not be a ValueError, just a warning
        #   raise ValueError(f'The name {tag.attrs["name"]} already exists in the volume registry')

        self.structure_tags.append(tag)
        if generalized_part_name is not None:
            self.generalized_volume_names.append(generalized_part_name)

    def add_physvol_tag(self, tag):
        self.physvol_tags.append(tag)

    def add_world(self, extent, center=(0, 0, 0)):
        """
        This means adding a world solid and a world volume
        to the gdml file.
        - This adds the "center' position to the define tag
        - A box called "worldbox" to the solids
        - Makes the setup using this "World"
        """
        attrs_w = {'name': 'center',\
                   'unit': 'mm',\
                   'x': str(center[0]),\
                   'y': str(center[1]),\
                   'z': str(center[2])}
        world_position = bs4.element.Tag(name='position',\
                                         is_xml=True,\
                                         can_be_empty_element=True,\
                                         attrs=attrs_w)
        self.schema['define'].append(copy(world_position))

        attrs_wb = {'name': 'worldbox',\
                    'x': str(extent[0]),\
                    'y': str(extent[1]),\
                    'z': str(extent[2])}

        world_box = bs4.element.Tag(name='box',\
                                    is_xml=True,\
                                    can_be_empty_element=True,\
                                    attrs=attrs_wb)
        self.schema['solids'].append(copy(world_box))
        world_volume = VolumeTag.create('World', 'ANTARCTICAIR', 'worldbox')
        for k in self.physvol_tags:
            world_volume.append(k)
        self.structure_tags.append(copy(world_volume))
        #self.world = copy(world_volume)

    def _create_gdml_tree(self):
        """
        Assemble the gdml tree
        """
        if self.is_locked:
            print(
                'Tree is locked. Propably you read in a gdml file. If you really want to overwrite the file, please release the lock with GdmlFile.release_lock()')
            return
        # self.bs.append(     copy(self.schema['gdml']))
        # self.bs.gdml.append(copy(self.schema['define']))
        # self.bs.gdml.append(copy(self.schema['materials']))
        # self.bs.gdml.append(copy(self.schema['solids']))
        # self.bs.gdml.append(copy(self.schema['structure']))
        # self.bs.gdml.append(copy(self.schema['setup']))
        self.bs.append(self.schema['gdml'])
        self.bs.gdml.append(self.schema['define'])
        self.bs.gdml.append(self.schema['materials'])
        self.bs.gdml.append(self.schema['solids'])
        self.bs.gdml.append(self.schema['structure'])
        self.bs.gdml.append(self.schema['setup'])
        # print (self.bs.prettify())

    def add_element(self, symbol):
        """
        Add an element to the materials list, look up by symbol
        """

        if isinstance(symbol, str):
            element = pt.__dict__[symbol]
        elif isinstance(symbol, pt.core.Element):
            element = symbol
        else:
            raise ValueError(f'Do not understand {symbol}. Has to be of type either str or periodictable.core.Element')
        if element.symbol in self.element_registry:
            print(f'Element {element.name} already added! Not doing anything')
            return

        isotopes = element.isotopes
        # add isotopes until we have 99.999% or larger
        threshold = 0.99999999
        total = 0
        use_isotopes = []
        fraction_tags = []
        fixed_fraction = (len(isotopes) == 1)
        for iso in isotopes:
            if element[iso].abundance == 0:
                continue
            total += element[iso].abundance
            use_isotopes.append(iso)
            attrs = dict()
            if fixed_fraction:
                abundance = 1
            else:
                abundance = str(element[iso].abundance)
            attrs = {'n': str(float(abundance) / 100.0),
                     'ref': element.symbol + str(iso)}
            fraction = bs4.element.Tag(name='fraction',\
                                       can_be_empty_element=True,\
                                       is_xml=True,\
                                       attrs=attrs)
            fraction_tags.append(copy(fraction))
            if total >= threshold:
                break

        isotope_tags = []
        for iso in use_isotopes:
            attrs = {'unit': 'g/mole',\
                     'value': element[iso].mass}

            atom = bs4.element.Tag(name='atom',
                                   can_be_empty_element=True,\
                                   is_xml=True,\
                                   attrs=attrs)
            attrs_i = {'N': iso,\
                       'Z': element[iso].number,\
                       'name': element.symbol + str(iso)}
            isotope_t = bs4.element.Tag(name='isotope',\
                                        is_xml=True,
                                        attrs=attrs_i)
            isotope_t.append(atom)
            self.isotope_tags.append(copy(isotope_t))
        element_tag = bs4.element.Tag(name='element',\
                                      is_xml=True,
                                      attrs={'name': element.symbol})
        for f in fraction_tags:
            element_tag.append(copy(f))
        self.element_tags.append(element_tag)
        self.element_registry.append(element.symbol)

    def add_elemental_material(self, symbol,
                               density=None,
                               temperature=293.15,
                               state=None):
        """
        Add a material which is just a single element (yes, we need this, since g4 can only
        use 'materials' for the logical volumes, not elements.

        Args:
            symbol (periodictable.core.Element)

        Keyword Args:
            density
            temperature
            state
        """
        if isinstance(symbol, str):
            element = pt.__dict__[symbol]
        elif isinstance(symbol, pt.core.Element):
            element = symbol
        else:
            raise ValueError(f'Do not understand {symbol}. Has to be of type either str or periodictable.core.Element')
        if element.name in self.material_registry:
            return

        if density is None:
            density = element.density
        attrs = {'name': element.name}
        if state is not None:
            atttrs['state'] = state
        material_t = bs4.element.Tag(name='material',\
                                     is_xml=True,\
                                     attrs=attrs)
        attrs_t = {'unit': 'K', 'value': temperature}
        temperature_t = bs4.element.Tag(name='T',\
                                        is_xml=True,\
                                        can_be_empty_element=True,\
                                        attrs=attrs_t)
        material_t.append(temperature_t)
        attrs_d = {'value': density, 'unit': 'g/cm3'}
        density_t = bs4.element.Tag(name='D',\
                                    is_xml=True,\
                                    can_be_empty_element=True,
                                    attrs=attrs_d)
        material_t.append(density_t)
        self.add_element(element.symbol)
        comp_tag = bs4.element.Tag(name='composite',\
                                   is_xml=True,
                                   can_be_empty_element=True,
                                   attrs={'n': '1',\
                                          'ref': element.symbol})
        material_t.append(comp_tag)
        self.material_tags.append(material_t)
        self.material_registry.append(element.name)

    def add_material(self, name, formula, density, state='solid', temperature='293.15'):
        """
        Add material with a chemical formula

        Args:
            density (float)     : Density in g/cm3

        Keyword Args:
            temperature (float) : Temperature in Celsius. The default is the Geant4 default.

        """
        if name in self.material_registry:
            return

        try:
            formula = pt.formula(formula)
        except ValueError as e:
            print(e)
            print(f'Most likely, {formula} is non-sensical or not formatted properly, try e.g. "C6H6" ..')
        attrs = {'name': name, 'state': state}
        material_t = bs4.element.Tag(name='material', \
                                     is_xml=True, \
                                     attrs=attrs)
        attrs_t = {'unit': 'K', 'value': temperature}
        temperature_t = bs4.element.Tag(name='T', \
                                        is_xml=True, \
                                        can_be_empty_element=True, \
                                        attrs=attrs_t)
        material_t.append(temperature_t)
        attrs_d = {'value': density, 'unit': 'g/cm3'}
        density_t = bs4.element.Tag(name='D', \
                                    is_xml=True, \
                                    can_be_empty_element=True,
                                    attrs=attrs_d)
        material_t.append(density_t)
        for el in formula.atoms:
            self.add_element(el.symbol)
            comp_tag = bs4.element.Tag(name='composite', \
                                       is_xml=True,
                                       can_be_empty_element=True,
                                       attrs={'n': formula.atoms[el], \
                                              'ref': el.symbol})
            material_t.append(comp_tag)
        self.material_tags.append(material_t)
        self.material_registry.append(name)

    def add_antarctic_air_material(self):
        """
        This adds a vacuum material, which is basically very thin
        air
        """
        # make sure the necessary elements are added
        for el in ['O','N','Ar','He','H']:
            self.add_element(el)

        attrs_v = {'name'  : 'ANTARCTICAIR',
                   'state' : 'gas'}

        antarcticair = bs4.element.Tag(name='material',\
                                       is_xml=True,\
                                       attrs=attrs_v)

        #MyAverageAntarcticAir = new G4Material("AverageAntarcticAir", 5.6023e-2*g/cm3, 5);
        #MyAverageAntarcticAir->AddElement(N, 59.7417986*perCent);
        #MyAverageAntarcticAir->AddElement(O, 39.9032668*perCent);
        #MyAverageAntarcticAir->AddElement(Ar, 0.31098995*perCent);
        #MyAverageAntarcticAir->AddElement(He, 0.04317824*perCent);
        #MyAverageAntarcticAir->AddElement(H, 0.00076565*perCent);

        # the 250 is approx and comes from a table
        # from the us weather service somewhere
        # it is probably more realistic than 293.15
        attrs_t = {'unit'  : 'K',\
                   'value' : 250}
        T       = bs4.element.Tag(name='T',\
                                  can_be_empty_element=True,\
                                  is_xml=True,\
                                  attrs=attrs_t)
        attrs_d = {'unit'  : 'g/cm3',\
                   'value' : '5.6023e-2'}
        D       = bs4.element.Tag(name='D',\
                                  can_be_empty_element=True,\
                                  is_xml=True,\
                                  attrs=attrs_d)
        fractions = {\
            'Oxygen'   : bs4.element.Tag(name='fraction',is_xml=True, can_be_empty_element=True,\
                                         attrs={'ref' : 'O'   , 'n' : '0.399032668'} ),
            'Nitrogen' : bs4.element.Tag(name='fraction',is_xml=True, can_be_empty_element=True,\
                                         attrs={'ref' : 'N' , 'n' : '0.597417986'} ),
            'Argon'    : bs4.element.Tag(name='fraction',is_xml=True, can_be_empty_element=True,\
                                         attrs={'ref' : 'Ar'    , 'n' : '0.0031098995'} ),
            'Helium'   : bs4.element.Tag(name='fraction',is_xml=True, can_be_empty_element=True,\
                                         attrs={'ref' : 'He'   , 'n' : '0.0004317824' } ),
            'Hydrogen'   : bs4.element.Tag(name='fraction',is_xml=True, can_be_empty_element=True,\
                                         attrs={'ref' : 'H'   , 'n' : '0.0000076565' } )
        }
        antarcticair.append(copy(T))
        antarcticair.append(copy(D))
        for k in fractions:
            antarcticair.append(copy(fractions[k]))
        self.material_tags.append(copy(antarcticair))

    def _write_materials(self):
        """
        Add all isotope/element/material tags to
        the <materials> tag and write it out
        """
        for k in self.isotope_tags:
            self.schema['materials'].append(copy(k))
        for k in self.element_tags:
            self.schema['materials'].append(copy(k))
        for k in self.material_tags:
            self.schema['materials'].append(copy(k))

    def _write_structure(self):
        for k in self.structure_tags:
            self.schema['structure'].append(k)

    def _write_solids(self):
        for k in tqdm.tqdm(self.solid_tags, desc='writing solids..'):
            self.schema['solids'].append(k)

    def _write_physvols(self):
        for k in tqdm.tqdm(self.physvol_tags, desc='writing physvols..'):
            self.schema['solids'].append(k)


    def _write_defines(self):
        for k in tqdm.tqdm(self.define_tags, desc='writing defines..'):
            self.schema['define'].append(k)

    def _write_setup(self, worldref='World'):
        """
        Adds the setup tag

        Keywords:
            worldref (str)   :  The name of the world volume
        """
        # FIXME - check if tag exists
        world_setup = bs4.element.Tag(name='world',\
                                      is_xml=True,\
                                      can_be_empty_element=True,\
                                      attrs={'ref' : worldref})
        self.schema['setup'].append(copy(world_setup))

    def write_to_file(self):
        """
        Write the gdml tree to the provided filename
        """
        if self.is_locked:
            print ('Tree is locked. Propably you read in a gdml file. If you really want to overwrite the file, please release the lock with GdmlFile.release_lock()')
            return
        self._write_tags()
        self._create_gdml_tree()
        f = open(self.filename, 'w')
        f.write(self.bs.prettify())
        f.close()


    def _write_tags(self):
        self._write_materials()
        self._write_defines()
        self._write_solids()
        self._write_structure()
        self._write_setup()








class GdmlFile(object):
    """
    A representation of a gdml file. Sort entries by classifications and
    then finally write it to disk
    """ 
    GDML_SCHEMA = {\
        'gdml'      : bs4.element.Tag(name='gdml',\
                        attrs={'xmlns:xsi' : "http://www.w3.org/2001/XMLSchema-instance",\
                               'xsi:noNamespaceSchemaLocation' : "http://service-spi.web.cern.ch/service-spi/app/releases/GDML/schema/gdml.xsd"}),

        'define'    : bs4.element.Tag(name='define'),
        'materials' : bs4.element.Tag(name='materials'),
        'solids'    : bs4.element.Tag(name='solids'),
        'structure' : bs4.element.Tag(name='structure'),
        'setup'     : bs4.element.Tag(name='setup',\
                          attrs={'name' : 'Default',\
                                 'version' : '1.0'})
    }


    def __init__(self, filename):
        self.filename    = filename
        # this holds the actual tree
        # in case we read from a file
        self.bs = None
        # a lock, so we don't overwrite anything
        self.is_locked = False
        if os.path.exists(filename):
            print (f'Will parse {filename}')
            self.bs = bs4.BeautifulSoup(open(filename), features="lxml-xml")
            self.is_locked = True
        else:
            self.bs = bs4.BeautifulSoup('<?xml version="1.0" encoding="UTF-8" standalone="no" ?>', features='lxml-xml') 
        # the current position inside the gdml tree
        self.cursor      = None
        self.gdml        = None
        # this holds the tree split up by 
        # the sections as defined in schema
        # in case we are creating a new file
        self.schema      = copy(GdmlFile.GDML_SCHEMA)
        # the extent of the world (if known)
        self.worldextent = (0,0,0)
        # keep track of every added element
        self.element_registry  = []
        # keep track of every added material
        self.material_registry = []
        # keep track of every added volume
        self.volume_registry = []
        # and the physical volumes, these can be more than 1 per volume!
        self.physvol_registry = defaultdict(lambda :0)
        # split up the materials in isotopes, elements and 
        
        # materials
        self.isotope_tags   = []
        self.element_tags   = []
        self.material_tags  = []

        # geometry
        self.structure_tags = []
        self.solid_tags     = []
        self.define_tags    = []
        self.physvol_tags   = []

    def add_physvol(self, name, posref=None, scale=None):
        physvol_name = name + '_p'
        
        if physvol_name in self.physvol_registry.keys():
            physvol_name += '_' + str( self.physvol_registry[physvol_name])
            self.physvol_registry[physvol_name]  += 1
        else:
            self.physvol_registry[physvol_name] = 1
        if posref is None:
            posref = physvol_name + '_pos'

        physvol_t = bs4.element.Tag(name = 'physvol',\
                                    is_xml = True,\
                                    attrs = {'name' : physvol_name})
        vol_ref   = bs4.element.Tag(name = 'volumeref',\
                                    is_xml = True,\
                                    can_be_empty_element=True,\
                                    attrs = {'ref' : name + '_v'})
        pos_ref   = bs4.element.Tag(name = 'positionref',\
                                    is_xml = True,\
                                    can_be_empty_element=True,\
                                    attrs = {'ref' : posref})
        if scale is not None:
            scale_tag = bs4.element.Tag(name='scale',\
                                        is_xml=true,\
                                        can_be_empty_element=True,\
                                        attrs={'name' : physvol_name + '_sc',
                                               'x' : scale[0],
                                               'y' : scale[1],
                                               'z' : scale[2]})
                                                             
        physvol_t.append(vol_ref)
        physvol_t.append(pos_ref)
        if scale is not None:
            physvol_t.append(scale_tag)
        self.physvol_tags.append(physvol_t)
        return physvol_name

    def add_tessel_solid(self, tsolid):
        """
        Add a tessellated solid in some form
        #TODO
        
        Args:
            tsolid (GdmlTessellatedSolid) : solid to add

        """
        # we have to add a new volume
        vname = tsolid.name + '_v'
        # in case it is in the registry, 
        # we also have it in the structure tags
        reg_vol = RegisteredVolume(vname, tsolid.material)
        if not (vname in self.volume_registry):
            volume_t  = self.volume_tag(tsolid.name, tsolid.material, tsolid.name + '_s')
            self.volume_registry.append(vname)
            self.structure_tags.append(copy(volume_t))
            define_t  = tsolid.create_define_tag()
            solid_t   = tsolid.create_solid_tag()
            # remove the <solids> preamble
            solid_t   = solid_t.tessellated
            solid_t.attrs['name'] += '_s'
            #define_t  = define_t.define 
            self.solid_tags.append(solid_t)
            for k in define_t.findChildren():
                self.define_tags.append(k)

        # if it has a position create an extra 
        # position tag
        if tsolid.position is not None:
            pname = self.add_physvol(tsolid.name)
            attrs = {'name' : pname + '_pos',\
                     'x'    : tsolid.position[0],\
                     'y'    : tsolid.position[1],\
                     'z'    : tsolid.position[2],\
                     'unit' : tsolid.unit}
            pos_tag = bs4.element.Tag(name='position',\
                                      is_xml=True,\
                                      can_be_empty_element=True,\
                                      attrs=attrs)
            
            self.define_tags.append(pos_tag)
            self.add_physvol(tsolid.name ,posref=pname + '_pos')
        else:
            self.add_physvol(tsolid.name ,posref= 'center')



    def release_lock(self):
        """
        Remove the lock to be able to overwrite 
        the currently loaded gdml tree
        """
        self.is_locked = False

    def create_gdml_tree(self):
        """
        Assemble the gdml tree
        """
        if self.is_locked:
            print ('Tree is locked. Propably you read in a gdml file. If you really want to overwrite the file, please release the lock with GdmlFile.release_lock()')
            return
        #self.bs.append(     copy(self.schema['gdml']))
        #self.bs.gdml.append(copy(self.schema['define'])) 
        #self.bs.gdml.append(copy(self.schema['materials'])) 
        #self.bs.gdml.append(copy(self.schema['solids'])) 
        #self.bs.gdml.append(copy(self.schema['structure'])) 
        #self.bs.gdml.append(copy(self.schema['setup'])) 
        self.bs.append(     self.schema['gdml'])
        self.bs.gdml.append(self.schema['define']) 
        self.bs.gdml.append(self.schema['materials']) 
        self.bs.gdml.append(self.schema['solids']) 
        self.bs.gdml.append(self.schema['structure']) 
        self.bs.gdml.append(self.schema['setup']) 
        #print (self.bs.prettify())

    def add_element(self, symbol):
        """
        Add an element to the materials list, look up by symbol
        """

        if isinstance(symbol, str):
            element = pt.__dict__[symbol]
        elif isinstance(symbol, pt.core.Element):
            element = symbol
        else:
            raise ValueError(f'Do not understand {symbol}. Has to be of type either str or periodictable.core.Element')
        if element.symbol in self.element_registry:
            print (f'Element {element.name} already added! Not doing anything')
            return

        isotopes = element.isotopes
        # add isotopes until we have 99.999% or larger    
        threshold = 0.99999999
        total     = 0
        use_isotopes = []
        fraction_tags = []
        fixed_fraction = (len(isotopes) == 1)
        for iso in isotopes:
            if element[iso].abundance == 0:
                continue
            total += element[iso].abundance
            use_isotopes.append(iso)
            attrs = dict()
            if fixed_fraction:
                abundance = 1
            else:
                abundance = str(element[iso].abundance)
            attrs = {'n'   : str(float(abundance)/100.0),
                     'ref' : element.symbol + str(iso)}
            fraction      = bs4.element.Tag(name='fraction',\
                                            can_be_empty_element=True,\
                                            is_xml=True,\
                                            attrs=attrs)
            fraction_tags.append(copy(fraction))
            if total >= threshold:
                break

        isotope_tags  = []
        for iso in use_isotopes:
            attrs = { 'unit' : 'g/mole',\
                      'value': element[iso].mass}
                     
            atom           = bs4.element.Tag(name='atom',
                                             can_be_empty_element=True,\
                                             is_xml=True,\
                                             attrs=attrs)
            attrs_i = {'N'    : iso,\
                       'Z'    : element[iso].number,\
                       'name' : element.symbol + str(iso)}
            isotope_t      = bs4.element.Tag(name='isotope',\
                                             is_xml=True,
                                             attrs=attrs_i)
            isotope_t.append(atom)
            self.isotope_tags.append(copy(isotope_t))
        element_tag = bs4.element.Tag(name='element',\
                                      is_xml=True,
                                      attrs={'name' : element.symbol})      
        for f in fraction_tags:
            element_tag.append(copy(f))
        self.element_tags.append(element_tag)
        self.element_registry.append(element.symbol)

    def add_elemental_material(self, symbol, density=None, temperature=293.15, state=None):
        """
        Add a material which is just a single element (yes, we need this, since g4 can only 
        use 'materials' for the logical volumes, not elements.

        Args:
            symbol (periodictable.core.Element)
        """
        if isinstance(symbol, str):
            element = pt.__dict__[symbol]
        elif isinstance(symbol, pt.core.Element):
            element = symbol
        else:
            raise ValueError(f'Do not understand {symbol}. Has to be of type either str or periodictable.core.Element')
        if element.name in self.material_registry:
            return 

        if density is None:
            density = element.density
        attrs={'name' : element.name}
        if state is not None:
            atttrs['state'] = state
        material_t  = bs4.element.Tag(name='material',\
                                     is_xml=True,\
                                     attrs=attrs)
        attrs_t = {'unit' : 'K', 'value' : temperature}
        temperature_t = bs4.element.Tag(name='T',\
                                       is_xml=True,\
                                       can_be_empty_element=True,\
                                       attrs = attrs_t)
        material_t.append(temperature_t)
        attrs_d = {'value' : density, 'unit' : 'g/cm3'}
        density_t   = bs4.element.Tag(name='D',\
                                     is_xml=True,\
                                     can_be_empty_element=True,
                                     attrs=attrs_d)
        material_t.append(density_t)
        self.add_element(element.symbol)
        comp_tag = bs4.element.Tag(name='composite',\
                                  is_xml=True,
                                  can_be_empty_element=True,
                                  attrs={'n'   : '1',\
                                         'ref' : element.symbol})
        material_t.append(comp_tag)
        self.material_tags.append(material_t)    
        self.material_registry.append(element.name)


    def add_material(self, name, formula, density, state='solid', temperature='293.15'):
        """
        Add material with a chemical formula

        Args:
            density (float)     : Density in g/cm3

        Keyword Args:
            temperature (float) : Temperature in Celsius. The default is the Geant4 default.

        """
        if name in self.material_registry:
            return

        try:
            formula = pt.formula(formula) 
        except ValueError as e:
            print (e)
            print (f'Most likely, {formula} is non-sensical or not formatted properly, try e.g. "C6H6" ..')
        attrs  = {'name': name, 'state' : state } 
        material_t  = bs4.element.Tag(name='material',\
                                     is_xml=True,\
                                     attrs=attrs)
        attrs_t = {'unit' : 'K', 'value' : temperature}
        temperature_t = bs4.element.Tag(name='T',\
                                       is_xml=True,\
                                       can_be_empty_element=True,\
                                       attrs = attrs_t)
        material_t.append(temperature_t)
        attrs_d = {'value' : density, 'unit' : 'g/cm3'}
        density_t   = bs4.element.Tag(name='D',\
                                     is_xml=True,\
                                     can_be_empty_element=True,
                                     attrs=attrs_d)
        material_t.append(density_t)
        for el in formula.atoms:
            self.add_element(el.symbol)
            comp_tag = bs4.element.Tag(name='composite',\
                                      is_xml=True,
                                      can_be_empty_element=True,
                                      attrs={'n'   : formula.atoms[el],\
                                             'ref' : el.symbol})
            material_t.append(comp_tag)
        self.material_tags.append(material_t)    
        self.material_registry.append(name)

    def write_materials(self):
        """
        Add all isotope/element/material tags to 
        the <materials> tag and write it out
        """
        for k in self.isotope_tags:
            self.schema['materials'].append(copy(k))
        for k in self.element_tags:
            self.schema['materials'].append(copy(k))
        for k in self.material_tags:
            self.schema['materials'].append(copy(k))

    def write_structure(self):
        for k in self.structure_tags:
            self.schema['structure'].append(k)

    def write_solids(self):
        for k in tqdm.tqdm(self.solid_tags, desc='writing solids..'):
            self.schema['solids'].append(k)
    
    def write_defines(self):
        for k in tqdm.tqdm(self.define_tags, desc='writing defines..'):
            self.schema['define'].append(k)

    def write_setup(self, worldref='World'):
        """
        Adds the setup tag

        Keywords:
            worldref (str)   :  The name of the world volume
        """
        # FIXME - check if tag exists
        world_setup = bs4.element.Tag(name='world',\
                                      is_xml=True,\
                                      can_be_empty_element=True,\
                                      attrs={'ref' : worldref})
        self.schema['setup'].append(copy(world_setup))

    def get_world_extent(self):
        pass

    def add_antarctic_air_material(self):
        """
        This adds a vacuum material, which is basically very thin
        air
        """ 
        # make sure the necessary elements are added
        for el in ['O','N','Ar','He','H']:
            self.add_element(el)

        attrs_v = {'name'  : 'ANTARCTICAIR',
                   'state' : 'gas'}

        antarcticair = bs4.element.Tag(name='material',\
                                       is_xml=True,\
                                       attrs=attrs_v)

        #MyAverageAntarcticAir = new G4Material("AverageAntarcticAir", 5.6023e-2*g/cm3, 5);
        #MyAverageAntarcticAir->AddElement(N, 59.7417986*perCent);
        #MyAverageAntarcticAir->AddElement(O, 39.9032668*perCent);
        #MyAverageAntarcticAir->AddElement(Ar, 0.31098995*perCent);
        #MyAverageAntarcticAir->AddElement(He, 0.04317824*perCent);
        #MyAverageAntarcticAir->AddElement(H, 0.00076565*perCent);

        # the 250 is approx and comes from a table
        # from the us weather service somewhere
        # it is probably more realistic than 293.15
        attrs_t = {'unit'  : 'K',\
                   'value' : 250} 
        T       = bs4.element.Tag(name='T',\
                                  can_be_empty_element=True,\
                                  is_xml=True,\
                                  attrs=attrs_t)
        attrs_d = {'unit'  : 'g/cm3',\
                   'value' : '5.6023e-2'}
        D       = bs4.element.Tag(name='D',\
                                  can_be_empty_element=True,\
                                  is_xml=True,\
                                  attrs=attrs_d)
        fractions = {\
            'Oxygen'   : bs4.element.Tag(name='fraction',is_xml=True, can_be_empty_element=True,\
                                         attrs={'ref' : 'O'   , 'n' : '0.399032668'} ), 
            'Nitrogen' : bs4.element.Tag(name='fraction',is_xml=True, can_be_empty_element=True,\
                                         attrs={'ref' : 'N' , 'n' : '0.597417986'} ),
            'Argon'    : bs4.element.Tag(name='fraction',is_xml=True, can_be_empty_element=True,\
                                         attrs={'ref' : 'Ar'    , 'n' : '0.0031098995'} ),
            'Helium'   : bs4.element.Tag(name='fraction',is_xml=True, can_be_empty_element=True,\
                                         attrs={'ref' : 'He'   , 'n' : '0.0004317824' } ), 
            'Hydrogen'   : bs4.element.Tag(name='fraction',is_xml=True, can_be_empty_element=True,\
                                         attrs={'ref' : 'H'   , 'n' : '0.0000076565' } ) 
        }
        antarcticair.append(copy(T))
        antarcticair.append(copy(D))
        for k in fractions:
            antarcticair.append(copy(fractions[k]))
        self.material_tags.append(copy(antarcticair))
 
    def volume_tag(self, name, materialref, solidref):
        """
        Emit a volume tag for inclusion in the tree
        """
        v_name = name
        if (name != 'World'):
            v_name += '_v'
        volume = bs4.element.Tag(name='volume',\
                                 is_xml=True,\
                                 attrs={'name' : v_name})
        mat    = bs4.element.Tag(name='materialref',\
                                 is_xml=True,\
                                 can_be_empty_element=True,\
                                 attrs={'ref' : materialref})
        sol    = bs4.element.Tag(name='solidref',\
                                 is_xml=True,\
                                 can_be_empty_element=True,
                                 attrs={'ref' : solidref})
        volume.append(copy(mat))
        volume.append(copy(sol))
        return copy(volume)

    def write_to_file(self):
        """
        Write the gdml tree to the provided filename
        """
        if self.is_locked:
            print ('Tree is locked. Propably you read in a gdml file. If you really want to overwrite the file, please release the lock with GdmlFile.release_lock()')
            return
        f = open(self.filename, 'w')
        f.write(self.bs.prettify())
        f.close()

    def add_world(self, extent, center=(0,0,0)):
        """
        This means adding a world solid and a world volume
        to the gdml file.
        - This adds the "center' position to the define tag
        - A box called "worldbox" to the solids
        - Makes the setup using this "World"
        """
        # attrs_w = {'name' : 'center',\
        #            'unit' : 'mm',\
        #            'x'    : str(center[0]),\
        #            'y'    : str(center[1]),\
        #            'z'    : str(center[2])}
        # world_position = bs4.element.Tag(name='position',\
        #                                  is_xml=True,\
        #                                  can_be_empty_element=True,\
        #                                  attrs=attrs_w)
        #self.schema['define'].append(copy(world_position))

        attrs_wb = {'name' : 'worldbox',\
                    'x' : str(extent[0]),\
                    'y' : str(extent[1]),\
                    'z' : str(extent[2])}
    
        world_box = bs4.element.Tag(name='box',\
                                    is_xml=True,\
                                    can_be_empty_element=True,\
                                    attrs=attrs_wb)
        self.schema['solids'].append(copy(world_box))
        world_volume = self.volume_tag('World', 'ANTARCTICAIR', 'worldbox')        
        for k in self.physvol_tags:
            world_volume.append(k)
        self.structure_tags.append(copy(world_volume))

