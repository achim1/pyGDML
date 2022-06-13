# pyGDML
GDML (Geometry Description Markup Language) allows to describe arbitrarily complex geometries and use them for open-source applications, e.g.  such written with the help of Geant4, a popular library among paticle physicists. 

## Focus on tessellated solids

A tessellated solid is an arbitrarily 
sahped solid, which surface is approximated 
by facets, typically triangles. 

## Fixing of issues for converted gdml files

A typical pipeline to generate gdml files might go 
through several conversions. The original engineering 
drawings might be in some proprietary CAD format, 
e.g. SOLIDWORKS and can then be exported as
STEP files. STEP is an open format. There is 
conversion software, e.g. MRADSim which acn then 
convert the STEP file into the gdml file. 

The conversion is non-trivial, and there might 
occur a number of issues:

* _invalid facets_ : The surfaces of the tessellated solids
migth contain factes, which are too small by some
metric or even degenerated.
* _invalid names_ : The names of the invalid solids might
contain invalid characters, e.g. "{"
* _duplicate tessellated solids_ : Instead of reusing the same solid, 
each part migth become its own tessellated solid, even if 
the same part has been used somewhere within the 
same construction before. This is only relevant 
in case the file contains an assembly with 
multiple solids. While technically not a problem,
but this increases the size of the file by a lot.

### Typical outline for a gdml file

A gdml file might contain the following sections, see also 
the gdml manual

```commandline
<gdml>
  <materials>
  <\materials>
  <define>
  <\define>
  <solids>
    <tessellated>
      <triangular\>
      ...
    <\tessellated>
  <\solids>
<\gdml>

```

There are some slight differences. From the official 
gdml standard, only a *single define* section is allowed.
However, sometimes during the conversion, there 
will be *multiple define* sections, one each 
per tessellated solid. 

The default naming of the vertices after the conversion 
might be ambiguous.
