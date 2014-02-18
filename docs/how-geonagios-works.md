Below is a description, for each supported protocol, how GeoNagios tests a geospatial service.

## Testing a Web Map Service (WMS)

GeoNagios uses the <tt>check_wms.py</tt> script to test a WMS server. 

Given a WMS server, it proceeds in the following overall steps:

1. Get the GetCapabilities document, by making a WMS GetCapabilities request (or reading the document from disc, if it has been retrieved earlier)
2. Parse the GetCapabilities document, and store it on disc (filename = md5 hash of servername + xml extension) for reuse
3. Select subset of layers, either all layers, or _n_ random layers (using `-n`), or a list of specific layers (using `-s`)
4. Output performance and availability data for each layer tested

Given a layer, check_wms.py tests it in the following way (by extracting information from GetCapabilities):

0. Choose a random srs and image format
2. Compute a random bounding box, with dimensions of roughly 100m x 100m, inside the supported boundary of the layer
3. Issue a GetMap request for a 200x200 pixel image using these settings
4. Store performance data about the request

You can manually override specific GetMap parameters, e.g. to enforce using a specific image format, srs, bounding box, image size etc.