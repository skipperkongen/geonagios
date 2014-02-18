# Public WMS Servers

This page lists a few public free WMS servers that can be used for testing.

## Public free WMS servers with Python example code

To load the class WebMapService used in the Python examples, use the following (requires OWSLib):

```python
from owslib.wms import WebMapService
```

### European Environmental Agency (EEA)

The EEA offers a huge collection of services. See links below for more information:

* About geospatial services at EEA: http://www.eea.europa.eu/code/gis
* Browse services: http://discomap.eea.europa.eu/arcgis/rest/services

GetCapabilities (one of many):

`http://discomap.eea.europa.eu/ArcGIS/services/Air/EPRTRDiffuseAir_Dyna_WGS84/MapServer/WMSServer?request=GetCapabilities&service=WMS&version=1.1.1`

Python example (one of many):

```python
wms = WebMapService('http://discomap.eea.europa.eu/ArcGIS/services/Air/EPRTRDiffuseAir_Dyna_WGS84/MapServer/WMSServer?request=GetCapabilities&service=WMS', version='1.1.1')
```

### Dansk Arealinfo

GetCapabilities:

`http://kort.arealinfo.dk/wms?servicename=landsdaekkende_wms&version=1.1.1&service=wms&REQUEST=GetCapabilities`

Python example:

```python
wms = WebMapService('http://kort.arealinfo.dk/wms?servicename=landsdaekkende_wms', version='1.1.1')
```

### Plansystem - lokalplaner for danmark

GetCapabilities:

`http://kort.plansystem.dk/wms?servicename=wms&request=getcapabilities&service=wms&version=1.1.0`

Python example

```python
wms = WebMapService('http://kort.plansystem.dk/wms?servicename=wms', version='1.1.0')
```

### Vienna City WMS (not part of GeoWatch project)

GetCapabilities:

`http://data.wien.gv.at/daten/wms?service=WMS&request=GetCapabilities&version=1.1.1`

Python example:

```python
wms = WebMapService('http://data.wien.gv.at/daten/wms', version='1.1.1')
```


