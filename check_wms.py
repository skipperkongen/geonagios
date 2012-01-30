import os, sys
import urllib2
import time as t
import random as r
from owslib.wms import WebMapService
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
                    default = 40.0,
                    type = "float",
                    help = "set the timeout timer (default is 40 sec.)"
                    )
parser.add_option(  "-n",
                    dest = "layerCount",
                    default = None,
                    help = "The numbers of layers to be checked (defualt is all of them)"
                    )
(options, args) = parser.parse_args()

print options.layerCount

def check_wms(options, urls):
    """docstring for check_wms"""
    
    url = urls[0]
    layerCount = options.layerCount
    timeout = options.timeout
    critTimer = options.critical
    warnTimer = options.warning
    
    wms = WebMapService(url, version='1.1.1')
    
    rOptions = getRandomData(wms, layerCount)
    
    #Runtime container
    timeDict = {}
    startTime = t.time()
    for layer in rOptions["layers"]:
        print layer
        t0 = t.time()
        check_service(wms, layer, "default", rOptions["bbox"], rOptions["format"])
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


def check_service(wms, layer, style, bbox, format, size = (300,250)):
    """docstring for check_service"""
    img = wms.getmap( layers = [layer],
                    styles = [style],
                    srs = 'EPSG:25832',
                    bbox = bbox,
                    size = size,
                    format = format,
                    transparent = False
                    )

def getRandomData(wms, layerCount):
    """docstring for getRandomData"""
    #Container
    resDict = {}
    
    #Get a random selection of layers if layerCount is set
    tmpLayers = wms.contents.keys()
    print len(tmpLayers)
    print layerCount
    if layerCount is not None and layerCount < len(tmpLayers):
        tLayers = r.sample(tmpLayers, layerCount)
        resDict["layers"] = tLayers
    else:
        resDict["layers"] = tmpLayers
        
    #TODO -
    #Make random bbox
    resDict["bbox"] = (669999.0, 6150602.0, 686669.0, 6163494.0)
    formats = wms.getOperationByName('GetMap').formatOptions
    
    #Get a random format supportet by the service
    resDict["format"] = r.sample(formats, 1)[0]
    
    return resDict

check_wms(options, args)
    