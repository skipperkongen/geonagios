#!/usr/bin/env python
from math import radians, cos, sin, asin, sqrt
import os, sys
import xml.etree.ElementTree as tree
import urllib2
from urllib import urlencode
import random
import time as t
from optparse import OptionParser
import datetime
import hashlib
import re
import math
import mimetypes as mime
from pyproj import Proj, Geod, transform

###############
# Setting up the options the user can set.
# -w is the max time the service have to respond before a warning is given
# -c is the max time the service have to respond before a critical warning is given
# -t is the max time the service have to respond.
# -n is the number of layers to test with
# --cached is a flag. If the flag is set, the script will only use getCap one time a day
###############

parser = OptionParser()

parser.add_option(  "-w", 
                    dest = "warning", 
                    default = 10000, 
                    type = "int",
                    help = "The maximum time, accepted for the service to run normally"
                    )
parser.add_option(  "-c", 
                    dest = "critical",
                    default = 30000,
                    type = "int",
                    help = "The threshold for the test, if the service doesn't respon by this time \
                            it's considered to be down"
                    )
parser.add_option(  "-t",
                    dest = "timeout",
                    default = None,
                    type = "int",
                    help = "set the timeout timer (default is 30 sec.)"
                    )
parser.add_option(  "-n",
                    dest = "layerCount",
                    default = None,
                    type = "int",
                    help = "The numbers of layers to be checked (defualt is all of them)"
                    )
parser.add_option(  "--cache", 
                    dest = "cached", 
                    action="store_true",
                    help = "")
parser.add_option(  "--image", 
                    dest = "image", 
                    action="store_true",
                    help = "Set this flag, if you want to save the pictures")
parser.add_option(  "-l", 
                    dest = "listLayer", 
                    action="store_true",
                    help = "Get list all the tested layers (This should not be used with nagios)")
parser.add_option(  "-g", 
                    dest = "getGeo", 
                    action="store_true",
                    help = "")
parser.add_option(  "-s", 
                    dest = "speLayer", 
                    type = "string", 
                    help = "specify layers to test (if multiple layers seperate with a ',')")
                    

                    
(options, args) = parser.parse_args()

class CheckWms():
    """docstring for CheckWms"""
    def __init__(self, options, args):
        self.options = options
        self.args = args
        
        if len(self.args) is 0:
            parser.print_help()
            sys.exit(2)
        
        self.setup()
        self.checkOptions()
        
    
    
    def checkOptions(self):
        """docstring for checkOptions"""
        opt = self.options
        try:
            if opt.listLayer is not None:
                if opt.layerCount is not None or \
                        opt.speLayer is not None:
                    raise WmsError("You can not use -s and/or -n with -l")
                if self.pLayers is not None or \
                        self.pBox is not None:
                    raise WmsError("You can not specify the param bbox and/or layers with -l")
            
            if opt.layerCount is not None:
                if opt.speLayer is not None:
                    raise WmsError("Please only specify -s or -n")
                    
                if self.pLayers is not None:
                    raise WmsError("You can not specify the param \"layers\" with -n")
                    
            elif opt.speLayer is not None:
                if opt.layerCount is not None:
                    raise WmsError("Please only specify -s or -n")
                if self.pLayers is not None and \
                        opt.speLayer is not self.argDict["LAYERS"]:
                    raise WmsError("You can not both specify a layer in the url and with -s")
                    
            if self.pBox is not None \
                    and self.pSrs is None:
                raise WmsError("You need to have both the \"bbox\" and the \"srs\" parameters in the url")
                    
        except WmsError, e:
            print e.value
            sys.exit(2)
    
    
    def setup(self):
        """docstring for setup"""
        url = urllib2.unquote(args[0])
        self.url, self.argDict = self.packUrl(url)
    
    
    def run(self):
        """docstring for run"""
        
        opt = self.options
        
        self.lCount = opt.layerCount
        
        if opt.timeout is not None:
            self.tout = (opt.timeout / 1000)
        else:
            self.tout = opt.timeout
            
        self.critTimer = opt.critical
        self.warnTimer = opt.warning
        
        listLayers = opt.listLayer
        self.getGeo = opt.getGeo
        
        flag = opt.cached
        
        self.fileHandler = FileHandler(self.url)
        
        self.imgFlag = opt.image
        
        try:
            self.wms = WebMapService(self.url, self.argDict, 
                                        flag, self.fileHandler, timeout = self.tout)
        except urllib2.HTTPError, e:
            print "HTTPerror code: %s, reason: %s" % (e.code, e.msg)
            sys.exit(2)
        except urllib2.URLError, e:
            print "Get Capability got a timeout"
            sys.exit(2)
            
        
        if listLayers is not None:
            self.listLayers()
            sys.exit(0)
            
        rData = self.wms.getRandomData(self.lCount)
        
        if self.pSrs:
            rData["SRS"] = self.checkSrs(self.pSrs)
        
        try:
            if opt.speLayer is not None:
                bbox = None
                if self.pBox is not None:
                    srs = self.pSrs
                    bbox = self.pBox
                elif self.pSrs is not None:
                    srs = self.pSrs
                    
                rData["Layers"] = self.checkLayers(opt.speLayer, rData["SRS"], bbox)
                
            elif self.pLayers:
                bbox = None
                if self.pBox is not None:
                    srs = self.pSrs
                    bbox = self.pBox
                elif self.pSrs is not None:
                    srs = self.pSrs
                    
                rData["Layers"] = self.checkLayers(self.pLayers, rData["SRS"], bbox)
                
            elif self.pBox is not None:
                for l in range(len(rData["Layers"])):
                    bbox = tuple(self.pBox.split(","))
                    if rData["Layers"][l][0].checkBbox(bbox, self.pSrs):
                        rData["Layers"][l] = (rData["Layers"][l][0], bbox)
            
            maximum, tData, tCap = self.checkWms(rData)
            
            pData = self.packData(tData, tCap, self.getGeo)
            
            if maximum is 2:
                endStr = "there is at least one layer, which is critical"
                print "%s|%s" % (endStr, pData)
                sys.exit(2)
            elif maximum is 1:
                endStr = "There is at least one layer, which is warrning"
                print "%s|%s" % (endStr, pData)
                sys.exit(1)
            else:
                endStr = "OK"
                print "%s|%s" % (endStr, pData)
                sys.exit(0)
            
        except WmsError, e:
            print e.value
            sys.exit(2)
        
    
    
    def checkWms(self, rData):
        timeDict = {}
        startTime = t.time()
        time = 0
        # Start to test the layers
        for layer in rData["Layers"]:
            try:
                t0 = t.time()
                pic = self.check_service(self.wms, layer[0], "default", rData["SRS"], layer[1], rData["Format"])
                t1 = t.time()
                size = sys.getsizeof(pic)
                if self.imgFlag is not None:
                    self.fileHandler.savePic(layer[0], rData["Format"], pic)
                time = t1 - t0
                time *= 1000
                # print "%s was %d before being done" % (layer[0], time)
                
                result = 0
                
                # Check what the result should be.
                
                if self.warnTimer <= time:
                    result = 1
                if self.critTimer <= time:
                    result = 2
            except urllib2.URLError, e:
                result = 2
                time = -1
                size = -1
                
            if result not in timeDict:
                timeDict[result] = []
                
            data = (layer[0], layer[1], time, size)
            timeDict[result].append(data)
            
        endTime = t.time()
        capTime = (endTime - startTime) * 1000
        
        keys = timeDict.keys()
        
        keys.sort()
        
        maximum = keys.pop()
        
        return (maximum, timeDict, capTime)
    
    
    def check_service(self, wms, layer, style, srs, bbox, format, size = (200,200)):
        """docstring for check_service"""
        img = wms.getMap( layer = layer.name,
                        style = style,
                        srs = srs,
                        bbox = bbox,
                        format = format,
                        size = size
                        )
        return img
    
    
    def checkLayers(self, speLayer, srs, bbox):
        if speLayer is not None:
            layers = speLayer.split(",")
            
        isLayer = False
        realLayer = []
        wmsLayer = self.wms.getLayersDict()
        if speLayer and srs and bbox:
            for l in layers:
                if l in wmsLayer:
                    isLayer = True
                    if wmsLayer[l].checkBbox(bbox, srs):
                        realLayer.append((wmsLayer[l], bbox))
                        
        elif speLayer and srs:            
            for l in layers:
                if l in wmsLayer:
                    isLayer = True
                    realLayer.append((wmsLayer[l], wmsLayer[l].getRandomBbox(srs)))
                else:
                    layers.remove(l)
                    
        elif speLayer:            
            for l in layers:
                if l in wmsLayer:
                    isLayer = True
                    realLayer.append((wmsLayer[l], wmsLayer[l].getRandomBbox(srs)))
                else:
                    layers.remove(l)
                    
        if not isLayer:
            raise WmsError("The layer(s) you have selected can not be found in this service")
            
        return realLayer
    
    
    def listLayers(self):
        """docstring for listLayers"""
        print "The layers for url %s are:" % self.url
        for layer in self.wms.getLayersDict():
            print layer
    
    
    def checkSrs(self, srs):
        if srs in self.wms.boundingbox.keys():
            return srs
        else:
            raise WmsError("The SRS you have specified is not supported by the service")
    
    def packUrl(self, urlStr):
        """docstring for packUrl"""
        url = urlStr.split('?')[0]
        
        argDict = {}
        self.pBox = None
        self.pLayers = None
        self.pSrs = None
        
        if len(urlStr.split('?')) > 1:
            arg = urlStr.split('?')[1]
            for argtup in arg.split('&'):
                key, value = argtup.split('=')
                argDict[key.upper()] = value
                
        if not "VERSION" in argDict:
            argDict["VERSION"] = "1.1.1"
            
        if not "SERVICE" in argDict:
            argDict["SERVICE"] = "WMS"
            
        if "LAYERS" in argDict:
            self.pLayers = argDict["LAYERS"]
            
        if "BBOX" in argDict:
            self.pBox = argDict["BBOX"]
            
        if "SRS" in argDict:
            self.pSrs = argDict["SRS"]
            
        return url, argDict
    
    
    def packData(self, values, capTime, getGeo):
        """docstring for packData"""
        timeList = []
        resStr = ""
        for key in values:
            for value in values[key]:
                name = value[0].name
                bbox = value[1]
                time = value[2]
                size = value[3]
                
                timeList.append(time)
                if key is 2:
                    nStr = "'t_%s'=%dms;%s" % (name, time, "crit")
                elif key is 1:
                    nStr = "'t_%s'=%dms;%s" % (name, time, "warn")
                else:
                    nStr = "'t_%s'=%dms" % (name, time)
                    
                nStr += ",'s_%s'=%dB" % (name, size)
                
                if getGeo is not None:
                    xStr = "'x_%s'=%d" % (name, (float(bbox[0]) + 50))
                    yStr = "'y_%s'=%d" % (name, (float(bbox[1]) + 50))
                    resStr += ",%s,%s,%s" % (nStr, xStr, yStr)
                else:
                    resStr += ",%s" % (nStr)
                    
        timeList.sort()
        
        minStr = ",'t_min'=%dms" % timeList[0]
        maxStr = ",'t_max'=%dms" % timeList.pop()
        oStr = "'t_get_capabilities'=%dms" % capTime
        
        return (oStr + maxStr + minStr + resStr)
    


class WebMapService():
    """docstring for WebMapService"""
    def __init__(self, url, urlArgs, flag, fileHandler, timeout = None):
        self.url = url
        self.urlArgs = urlArgs
        self.version = urlArgs['VERSION']
        self.flag = flag
        self.formats = []
        self.boundingbox = {}
        self.timeout = timeout
        self.layers = []
        self.operation = {}
        self.fh = fileHandler
        self._newXml()
        self.getCapability()
    
        
    def getCapability(self):
        try:
            etree = tree.parse(self.fName)
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
                bBox = self.boundingbox
                for b in tmpBBox:
                    box = ( b.attrib["minx"], b.attrib["miny"] ,
                            b.attrib["maxx"], b.attrib["maxy"])
                    bBox[b.attrib["SRS"]] = box
                l = Layer(name, title, bBox)
                self.layers.append(l)
        except tree.ParseError, e:
            print "Something is wrong with the xml from getcapabilities" \
                    + "\nPlease check you have entered a valid url"
            sys.exit(2)
        
        
    
    
    def _newXml(self):
        """
        newXml determines if there will be made a new cached xml file of the capabilitis
        
        @param  url: The url of the service.
        @param  flag: The flag set by the user, if this flag is said there won't be created a new xml file
        @param  timeout: user specific timeout.
        @param  verison: The version for the servcie.
        @return: The filename of the xml file whether or not a new file was created.
        """
        fName = self.fh.cache
        try:
            if self.flag:
                if fName is None or not self._checkDate(fName):
                    fName = self.fh.setCap(self.getCap())
                    
            else:
                fName = self.fh.setCap(self.getCap())
        except WmsError, e:
            print e.value
            sys.exit(2)
            
        
        self.fName = fName
    
    
    def _checkDate(self, fName):
        """
        checkData checkes if the data the xml file was created is the same
        as today
        
        @param  fName: The name of the file to check.
        @return: whether or not the file was created today
        """
        year = t.localtime(os.stat(fName).st_atime).tm_year
        mon = t.localtime(os.stat(fName).st_atime).tm_mon
        day = t.localtime(os.stat(fName).st_atime).tm_mday
        
        if datetime.date(year, mon, day) == datetime.date.today():
            return True
        else:
            return False
    
    
    def getCap(self):
        
        request = self.capRequest()
            
        data = urlencode(request)
        
        xmlCap = urllib2.urlopen((self.url + "?" + data), timeout = self.timeout)
        
        # del request["REQUEST"]
        
        if xmlCap.info()['Content-Type'] == 'application/xml charset=utf-8':
            se_xml = xmlCap.read()
            se_tree = tree.fromstring(se_xml)
            err_message = unicode(se_tree.find('ServiceException').text).strip()
            raise WmsError(err_message)
            
        return xmlCap
    
    
    def capRequest(self):
        """docstring for capRequest"""
        request = {}
        
        if not "REQUEST" in self.urlArgs:
            request["REQUEST"] = "GetCapabilities"
        elif not self.urlArgs["REQUEST"] == "GetCapabilities":
            request["REQUEST"] = "GetCapabilities"
        else:
            request["REQUEST"] = self.urlArgs["REQUEST"]
            
        request["VERSION"] = self.urlArgs["VERSION"]
        
        request["SERVICE"] = self.urlArgs["SERVICE"]
        
        if "SERVICENAME" in self.urlArgs:
            request["SERVICENAME"] = self.urlArgs["SERVICENAME"]
            
        if "PASSWORD" in self.urlArgs:
            request["PASSWORD"] = self.urlArgs["PASSWORD"]
            
        if "LOGIN" in self.urlArgs:
            request["LOGIN"] = self.urlArgs["LOGIN"]
            
        return request
    
    
    def getMap( self, layer, style, srs, 
                bbox, format, size,
                bgcolor='#FFFFFF',
                exceptions='application/vnd.ogc.se_xml',
                method='Get' ):
        
        urlBase = self.operation["get"]   
        
        request = self.urlArgs
        
        if not "VERSION" in request:
            request["VERSION"] = self.version
        
        if not "REQUEST" in request or not request["REQUEST"] == 'GetMap':
            request["REQUEST"] = 'GetMap'
        
        request['LAYERS'] = layer
        
        if not "STYLES" in request:
            request['STYLES'] = ""
        
        if not 'TRANSPARENT' in request:
            request['TRANSPARENT'] = "FALSE"
            
        if not 'WIDTH' in request:
            request['WIDTH'] = str(size[0])
            
        if not 'HEIGHT' in request:
            request['HEIGHT'] = str(size[1])
        
        request['SRS'] = str(srs)
        
        request['BBOX'] = ','.join([x for x in bbox])
        
        if not 'FORMAT' in request:
            request['FORMAT'] = str(format)
        
        if not 'BGCOLOR' in request:
            request['BGCOLOR'] = '0x' + bgcolor[1:7]
        
        if not 'EXCEPTIONS' in request:
            request['EXCEPTIONS'] = str(exceptions)
        
        data = urlencode(request)
        
        if not "?" in urlBase:
            urlBase += "?"
        
        u = urllib2.urlopen((urlBase + data), timeout = self.timeout)
        # check for service exceptions, and return
        
        if u.info()['Content-Type'] == 'application/vnd.ogc.se_xml':
            se_xml = u.read()
            se_tree = tree.fromstring(se_xml)
            err_message = unicode(se_tree.find('ServiceException').text).strip()
            raise WmsError(err_message)
        return u.read()
    
    
    def getRandomData(self, count):
        """docstring for getRandomLayers"""
        #Container
        resDict = {}
        
        srs = random.sample(self.boundingbox.keys(), 1)[0]
        
        if count is not None and count < len(self.layers):
            rLayers = random.sample(self.layers, count)
        else:
            rLayers = self.layers
            
        resDict["SRS"] = srs
        
        resDict["Layers"] = []
        
        for layer in rLayers:
            resDict["Layers"].append((layer, layer.getRandomBbox(srs)))
        
        resDict["Format"] = random.sample(self.formats, 1)[0]
        
        return resDict
    
    
    def getLayersDict(self):
        layerDict = {}
        for layer in self.layers:
            layerDict[layer.name] = layer
        return layerDict
    
    


class Layer():
    """
    The layer class keeps the information for each layer from the service
    """
    def __init__(self, name, title, srs):
        """
        @type   name: string
        @param  name: the name of the layer
        
        @type   title: string
        @param  title: The title of the layer
        
        @type   srs: dict
        @param  srs: A dictionary containing srs's and their bounding box
        
        @rtype: Layer object
        @return: A layer containing all relevant data
        """
        self.name = name
        self.title = title
        self.srs = srs
    
    
    def getRandomBbox(self, srs):
        """docstring for getRandomBbox
        The calculations in this methode is not 100% accurate
        """
        bBox = self.srs[srs]
        geod = Geod(ellps='sphere')
        dist = math.sqrt(20000)
        latLong = Proj(proj='latlong')
        
        if srs is "EPSG:900913":
            srs = "EPSG:3857"
            
        p = Proj(init=srs)
        minX, minY = transform(p, latLong, bBox[0], bBox[1])
        maxX, maxY = transform(p, latLong, bBox[2], bBox[3])
        
        maxX, maxY, trash = geod.fwd(maxX, maxY, 225, dist)
        
        rMinX = random.uniform(minX, maxX)
        rMinY = random.uniform(minY, maxY)
        
        rMaxX, rMaxY, trash = geod.fwd(rMinX, rMinY, 45, dist)
        
        
        res0, res1 = transform(latLong, p, rMinX, rMinY)
        res2, res3 = transform(latLong, p, rMaxX, rMaxY)
        
        randomBox = (str(res0), str(res1), str(res2), str(res3))
        
        return randomBox
    
    
    def calDist(self, lat, lon, lat2, lon2):
        """This is just for testing purpose"""
        lon1, lat1, lon2, lat2 = map(radians, [lon, lat, lon2, lat2])
        # haversine formula 
        dlon = lon2 - lon1 
        dlat = lat2 - lat1 
        a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
        c = 2 * asin(sqrt(a)) 
        km = 6367 * c
        print km
    
    
    def checkBbox(self, bbox, srs):
        
        layerBox = map(float, bbox)
        
        serviceBox = map(float, self.srs[srs])
        
        minX = serviceBox[0] <= layerBox[0] <= serviceBox[2]
        minY = serviceBox[1] <= layerBox[1] <= serviceBox[3]
        
        maxX = serviceBox[0] <= layerBox[2] <= serviceBox[2]
        maxY = serviceBox[1] <= layerBox[3] <= serviceBox[3]
        
        if minX and maxX \
                and minY and maxY:
            return True
        else:
            raise WmsError("The specified boundbox is not supported by the service")


class FileHandler():
    """docstring for FileHandler"""
    def __init__(self, url):
        homedir = os.path.expanduser('~')
        pattern = "http://(.[^/]+)"
        self.dirName = re.findall(pattern, url)[0].replace(".", "_")
        self.picDir =  homedir + "/check_wms_files/images/" + self.dirName
        self.capDir = homedir + "/check_wms_files/cache"
        self.initDir(homedir)
        
        m = hashlib.md5()
        m.update(self.dirName)
        fName = self.capDir + "/" + str(m.hexdigest()) + ".xml"
        
        if os.path.exists(fName):
            self.cache = fName
        else:
            self.cache = None
    
        
    def initDir(self, homedir):
        """docstring for initDir"""
        fDir = homedir + "/check_wms_files"
        if not os.path.exists(fDir):
            os.mkdir(fDir)
            
        cDir = fDir + "/cache"
        if not os.path.exists(cDir):
            os.mkdir(cDir)
        
        iDir = fDir + "/images"
        if not os.path.exists(iDir):
            os.mkdir(iDir)
            
        if not os.path.exists(self.picDir):
            os.mkdir(self.picDir)
    
            
    def savePic(self, lName, format, fd):
        """docstring for save"""
        exts = {"image/png8" : ".png", "image/png16" : ".png", "image/png32" : ".png",
                "image/jpg" : ".jpg"}
        ext = mime.guess_extension(format)
        if ext is None:
            ext = exts[format]
        fName = self.picDir + "/" + lName + ext
        f = open(fName, 'w')
        f.write(fd)
        f.close()
    
              
    def setCap(self, xml):
        """docstring for setCap"""
        
        m = hashlib.md5()
        m.update(self.dirName)
        
        self.cache = self.capDir + "/" + str(m.hexdigest()) + ".xml"
        
        fp = open(self.cache, 'w')
        
        fp.write(xml.read())
        
        fp.close()
        
        return self.cache
    
    
    def setCapXml(self):
        """docstring for setCapXml"""
        if self.cache is not None:
            fd = open(self.cache, 'r')
            xml = fd.read()
            fp.close()
            return xml
        return None
    


class WmsError(Exception):
    def __init__(self, value):
        self.value = value
    
    def __str__(self):
        return repr(self.value)
    


try:
    CheckWms(options, args).run()
except Exception, e:
    print e
    sys.exit(2)

    