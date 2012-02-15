import os, sys
import xml.etree.ElementTree as tree
import urllib2
from urllib import urlencode
import random
import time as t
from optparse import OptionParser

parser = OptionParser()

parser.add_option(  "-w", 
                    dest = "warning", 
                    default = 10.0, 
                    type = "float",
                    help = "The maximum time, accepted for the service to run normally"
                    )
parser.add_option(  "-c", 
                    dest = "critical",
                    default = 30.0,
                    type = "float",
                    help = "The threshold for the test, if the service doesn't respon by this time \
                            it's considered to be down"
                    )
parser.add_option(  "-t",
                    dest = "timeout",
                    default = None,
                    type = "int",
                    help = "set the timeout timer (default is 40 sec.)"
                    )
parser.add_option(  "-n",
                    dest = "layerCount",
                    default = None,
                    type = "int",
                    help = "The numbers of layers to be checked (defualt is all of them)"
                    )
(options, args) = parser.parse_args()

def check_wms(options, urls):
    """docstring for check_wms"""
    
    url = urls[0]
    layerCount = options.layerCount
    timeout = options.timeout
    critTimer = options.critical
    warnTimer = options.warning
    try:
        wms = WebMapService(url, timeout = timeout, version='1.1.1')
    except urllib2.URLError:
        print "Get Capability got a timeout"
        return 2
    
    
    rOptions = wms.getRandomData(layerCount)
    
    print rOptions
    
    #Runtime container
    timeDict = {}
    startTime = t.time()
    for layer in rOptions["Layers"]:
        t0 = t.time()
        check_service(wms, layer[0], "default", rOptions["SRS"], layer[1], rOptions["Format"])
        t1 = t.time()
        time = t1 - t0
        
        result = 0
        
        if warnTimer <= time < critTimer:
            result = 1
        elif critTimer <= time < timeout:
            result = 2
            
        if result not in timeDict:
            timeDict[result] = []
        timeDict[result].append(layer)
        
    endTime = t.time()
    
    print "it took %d sec" % (endTime - startTime)
        
    keys = timeDict.keys()
    
    keys.sort()
    
    maximum = keys.pop()
    
    if maximum is 2:
        print "there is %d layers, which is critical" % len(timeDict[maximum])
        return 2
    elif maximum is 1:
        print "There is %d layers, which is warrning" % len(timeDict[maximum])
        return 1
    else:
        print "Everything is O.K"
        return 0


def check_service(wms, layer, style, srs, bbox, format, size = (200,200)):
    """docstring for check_service"""
    img = wms.getMap( layer = layer,
                    style = style,
                    srs = srs,
                    bbox = bbox,
                    size = size,
                    format = format
                    )

class WebMapService():
    """docstring for WebMapService"""
    def __init__(self, url, timeout = None, version="1.1.1"):
        self.url = url
        self.version = version
        self.formats = []
        self.boundingbox = {}
        self.timeout = timeout
        self.layers = []
        self.operation = {}
        self.getCapability()

    def getCapability(self):
        # Format url
        urlsplits = self.url.split('&')
        urlBase = urlsplits[0] + "&version=" + self.version \
              + "&service=wms&REQUEST=GetCapabilities"
        
        # Open the url
        f = urllib2.urlopen(urlBase, timeout = self.timeout)

        etree = etree = tree.parse(f)
        root = etree.getroot()

        capability = root.find("Capability")

        getmap = capability.find("Request").find("GetMap")

        for format in getmap.findall("Format"):
            self.formats.append(format.text)

        get1 = getmap.find("DCPType/HTTP/Get/OnlineResource")
        self.operation["get"] = get1.attrib['{http://www.w3.org/1999/xlink}href']

        layers = capability.find("Layer")

        for srs in layers.findall("SRS"):
            self.boundingbox[srs.text] = []

        bbox = layers.findall("BoundingBox")

        for b in bbox:
            box = ( b.attrib["minx"], b.attrib["miny"] ,
                    b.attrib["maxx"], b.attrib["maxy"])
            self.boundingbox[b.attrib["SRS"]] = box

        # Get all the layers!
        layer = layers.findall("Layer")
        for lay in layer:
            name = lay.find("Name").text
            title = lay.find("Title").text
            tmpBBox = lay.findall("BoundingBox")
            if len(tmpBBox) is 0:
                bBox = self.boundingbox
            else:
                bBox = {}
                for b in tmpBBox:
                    box = ( b.attrib["minx"], b.attrib["miny"] ,
                            b.attrib["maxx"], b.attrib["maxy"])
                    bBox[b.attrib["SRS"]] = box
            l = Layer(name, title, bBox)
            self.layers.append(l)

        print len(self.layers)
        print self.formats
        print self.boundingbox
    

    def getMap( self, layer, style, srs, 
                bbox, format, size,
                bgcolor='#FFFFFF',
                exceptions='application/vnd.ogc.se_xml',
                method='Get',):
                
        urlBase = self.operation["get"]        
        request = {'version': self.version, 'request': 'GetMap'}

        request['layers'] = layer
        
        request['styles'] = style
        
        request['transparent'] = "FALSE"

        request['width'] = str(size[0])
        request['height'] = str(size[1])

        request['srs'] = str(srs)
        request['bbox'] = ','.join([repr(x) for x in bbox])
        request['format'] = str(format)
        request['bgcolor'] = '0x' + bgcolor[1:7]
        request['exceptions'] = str(exceptions)

        data = urlencode(request)

        u = urllib2.urlopen((urlBase + data), timeout = self.timeout)

        # check for service exceptions, and return
        if u.info()['Content-Type'] == 'application/vnd.ogc.se_xml':
            se_xml = u.read()
            se_tree = tree.fromstring(se_xml)
            err_message = unicode(se_tree.find('ServiceException').text).strip()
            raise ServiceException(err_message, se_xml)
        return u



    def getRandomData(self, count):
        """docstring for getRandomLayers"""
        #Container
        resDict = {}

        srs = random.sample(self.boundingbox.keys(), 1)[0]
        print "count er "
        if count is not None and count < len(self.layers):
            print "I randomData laver en sample"
            rLayers = random.sample(self.layers, count)
        else:
            print "Der skal ikke laves en sample"
            rLayers = self.layers
            
        resDict["SRS"] = srs

        resDict["Layers"] = []

        for layer in rLayers:
            resDict["Layers"].append((layer.name, layer.getRandomBbox(srs)))

        resDict["Format"] = random.sample(self.formats, 1)[0]

        return resDict


class Layer():
    """docstring for Layer"""
    def __init__(self, name, title, srs):
        self.name = name
        self.title = title
        self.srs = srs

    def getRandomBbox(self, srs):
        """docstring for getRandomBbox"""
        bBox = self.srs[srs]
        maxX = float(bBox[2]) - 10.0
        maxY = float(bBox[3]) - 10.0

        randomX = random.randrange(float(bBox[0]), maxX, 1)
        randomY = random.randrange(float(bBox[1]), maxY, 1)

        return (str(randomX), str(randomY), str(randomX + 10.0), str(randomY + 10.0))

check_wms(options, args)
    