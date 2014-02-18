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

parser.add_option(	"-w", "--warning",
					dest = "warning", 
					default = 10000, 
					type = "int",
					help = "Configure maximum latency for service response time, without raising warning. Argument is an integer (milliseconds)"
					)
parser.add_option(	"-c", "--critical",
					dest = "critical",
					default = 30000,
					type = "int",
					help = "Configure maximum latency for service response time, without raising a critical error. Argument is an integer (milliseconds)"
					)
parser.add_option(	"-t", "--timeout",
					dest = "timeout",
					default = None,
					type = "int",
					help = "Set the test timeout (default is 30 seconds). Argument is an integer (seconds)."
					)
parser.add_option(	"-n",
					dest = "layerCount",
					default = None,
					type = "int",
					help = "Test *n* random layers (default is to check all layers). Argument is an integer."
					)
parser.add_option(	"--cache-capabilities", 
					dest = "cached", 
					action="store_true",
					help = "Save a copy of getCapabilities on disk, and reuse on next run. No argument.")
parser.add_option(	"-l", "--list",
					dest = "listLayer", 
					action="store_true",
					help = "List the layers available from service. No argument.")
parser.add_option(	"-s", "--specific-layers",
					dest = "specificLayer", 
					type = "string", 
					help = "A list of layers (subset of layers from service) to test. Argument is a string like 'foo,bar,baz'.")
					
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
						opt.specificLayer is not None:
					raise WmsError("You can not use -s and/or -n with -l")
				if self.layersUrlParameter is not None or \
						self.bboxUrlParameter is not None:
					raise WmsError("You can not specify the param bbox and/or layers with -l")
			
			if opt.layerCount is not None:
				if opt.specificLayer is not None:
					raise WmsError("Please only specify -s or -n")
					
				if self.layersUrlParameter is not None:
					raise WmsError("You can not specify the param \"layers\" with -n")
					
			elif opt.specificLayer is not None:
				if opt.layerCount is not None:
					raise WmsError("Please only specify -s or -n")
				if self.layersUrlParameter is not None and \
						opt.specificLayer is not self.queryStringParameters["LAYERS"]:
					raise WmsError("You can not both specify a layer in the url and with -s")
					
			if self.bboxUrlParameter is not None \
					and self.srsUrlParameter is None:
				raise WmsError("You need to have both the \"bbox\" and the \"srs\" parameters in the url")
					
		except WmsError, e:
			print e.value
			sys.exit(2)
	
	
	def setup(self):
		"""docstring for setup"""
		url = urllib2.unquote(args[0])
		self.url, self.queryStringParameters = self.packUrl(url)
	
	
	def run(self):
		"""docstring for run"""
		
		opt = self.options
		
		self.layerCount = opt.layerCount
		
		if opt.timeout is not None:
			self.tout = (opt.timeout / 1000)
		else:
			self.tout = opt.timeout
			
		self.critTimer = opt.critical
		self.warnTimer = opt.warning
		
		flagListLayers = opt.listLayer
		
		flagCacheGetCapabilities = opt.cached
		
		self.fileHandler = FileHandler(self.url)
				
		try:
			startTime = t.time()
			self.wms = WebMapService(self.url, self.queryStringParameters, 
										flagCacheGetCapabilities, self.fileHandler, timeout = self.tout)
										
			getCapabilitiesLatency = (t.time() - startTime) * 1000
			 
		except urllib2.HTTPError, e:
			print "HTTPerror code: %s, reason: %s" % (e.code, e.msg)
			sys.exit(2)
		except urllib2.URLError, e:
			print "Get Capability got a timeout"
			sys.exit(2)
			
		
		if flagListLayers is not None:
			self.listLayers()
			sys.exit(0)
			
		randomTestData = self.wms.getRandomGetMapParameters(self.layerCount)
		
		if self.srsUrlParameter:
			randomTestData["SRS"] = self.checkSrs(self.srsUrlParameter)
		
		try:
			if opt.specificLayer is not None:
				bbox = None
				if self.bboxUrlParameter is not None:
					srs = self.srsUrlParameter
					bbox = self.bboxUrlParameter
				elif self.srsUrlParameter is not None:
					srs = self.srsUrlParameter
					
				randomTestData["Layers"] = self.checkLayers(opt.specificLayer, randomTestData["SRS"], bbox)
				
			elif self.layersUrlParameter:
				bbox = None
				if self.bboxUrlParameter is not None:
					srs = self.srsUrlParameter
					bbox = self.bboxUrlParameter
				elif self.srsUrlParameter is not None:
					srs = self.srsUrlParameter
					
				randomTestData["Layers"] = self.checkLayers(self.layersUrlParameter, randomTestData["SRS"], bbox)
				
			elif self.bboxUrlParameter is not None:
				for l in range(len(randomTestData["Layers"])):
					bbox = tuple(self.bboxUrlParameter.split(","))
					if randomTestData["Layers"][l][0].checkBbox(bbox, self.srsUrlParameter):
						randomTestData["Layers"][l] = (randomTestData["Layers"][l][0], bbox)
			
			worstStatus, layersWithErrorCount, getMapLatencies = self.checkWms(randomTestData)
			
			performanceData = self.packPerformanceData(getMapLatencies, getCapabilitiesLatency)
			
			if worstStatus is 2:
				humanReadableString = "Critical for: %d out of %d layer(s)" % (layersWithErrorCount, len(randomTestData["Layers"]))
				print "%s|%s" % (humanReadableString, performanceData)
				sys.exit(2)
			elif worstStatus is 1:
				humanReadableString = "Warning for: %d out of %d layer(s)" % (layersWithErrorCount, len(randomTestData["Layers"]))
				print "%s|%s" % (humanReadableString, performanceData)
				sys.exit(1)
			else:
				humanReadableString = "OK"
				print "%s|%s" % (humanReadableString, performanceData)
				sys.exit(0)
			
		except WmsError, e:
			print e.value
			sys.exit(2)
		
	
	
	def checkWms(self, randomTestData):
		testResultsByStatus = {}
		# Start to test the layers
		for layer in randomTestData["Layers"]:
			try:
				t0 = t.time()
				mapImage = self.check_service(self.wms, layer[0], "default", randomTestData["SRS"], layer[1], randomTestData["Format"])
				t1 = t.time()
				mapImageSize = sys.getsizeof(mapImage)
				latency = t1 - t0
				latency *= 1000
				# print "%s was %d before being done" % (layer[0], time)
				
				status = 0
				
				# Check what the result should be.
				
				if self.warnTimer <= latency:
					status = 1
				if self.critTimer <= latency:
					status = 2
			except urllib2.URLError, e:
				status = 2
				latency = -1
				size = -1
				
			if status not in testResultsByStatus:
				testResultsByStatus[status] = []
				
			testResults = (layer[0], layer[1], latency, mapImageSize)
			testResultsByStatus[status].append(testResults)
		
		statusKeys = testResultsByStatus.keys()
		
		statusKeys.sort()
		
		worstStatus = statusKeys.pop()
		
		return (worstStatus, len(testResultsByStatus[worstStatus]), testResultsByStatus)
	
	
	def check_service(self, wms, layer, style, srs, bbox, format, imageDimensions = (200,200)):
		"""docstring for check_service"""
		img = wms.getMap( layer = layer.name,
						style = style,
						srs = srs,
						bbox = bbox,
						format = format,
						imageDimensions = imageDimensions
						)
		return img
	
	
	def checkLayers(self, specificLayersString, srs, bbox):
		if specificLayersString is not None:
			specificLayers = specificLayersString.split(",")
			
		isValidLayer = False
		layersToTest = []
		layersInGetCapabilities = self.wms.getLayersDict()
		if specificLayersString and srs and bbox:
			for l in specificLayers:
				if l in layersInGetCapabilities:
					isValidLayer = True
					if layersInGetCapabilities[l].checkBbox(bbox, srs):
						layersToTest.append((layersInGetCapabilities[l], bbox))
						
		elif specificLayersString and srs:			  
			for l in specificLayers:
				if l in layersInGetCapabilities:
					isValidLayer = True
					layersToTest.append((layersInGetCapabilities[l], layersInGetCapabilities[l].getRandomBbox(srs)))
				else:
					specificLayers.remove(l)
					
		elif specificLayersString:			  
			for l in specificLayers:
				if l in layersInGetCapabilities:
					isValidLayer = True
					layersToTest.append((layersInGetCapabilities[l], layersInGetCapabilities[l].getRandomBbox(srs)))
				else:
					specificLayers.remove(l)
					
		if not isValidLayer:
			raise WmsError("The layer(s) you have selected can not be found in this service")
			
		return layersToTest
	
	
	def listLayers(self):
		"""docstring for listLayers"""
		#print "The layers for url %s are:" % self.url
		for layer in self.wms.getLayersDict():
			print layer
	
	
	def checkSrs(self, srsUrlParameter):
		if srsUrlParameter in self.wms.boundingbox.keys():
			return srsUrlParameter
		else:
			raise WmsError("The SRS you have specified is not supported by the service")
	
	def packUrl(self, urlStr):
		"""docstring for packUrl"""
		url = urlStr.split('?')[0]
		
		queryStringDict = {}
		self.bboxUrlParameter = None
		self.layersUrlParameter = None
		self.srsUrlParameter = None
		
		if len(urlStr.split('?')) > 1:
			arg = urlStr.split('?')[1]
			for argtup in arg.split('&'):
				key, value = argtup.split('=')
				queryStringDict[key.upper()] = value
				
		if not "VERSION" in queryStringDict:
			queryStringDict["VERSION"] = "1.1.1"
			
		if not "SERVICE" in queryStringDict:
			queryStringDict["SERVICE"] = "WMS"
			
		if "LAYERS" in queryStringDict:
			self.layersUrlParameter = queryStringDict["LAYERS"]
			
		if "BBOX" in queryStringDict:
			self.bboxUrlParameter = queryStringDict["BBOX"]
			
		if "SRS" in queryStringDict:
			self.srsUrlParameter = queryStringDict["SRS"]
			
		return url, queryStringDict
	
	
	def packPerformanceData(self, values, getCapabilitiesLatency):
		"""docstring for packPerformanceData"""
		latencies = []
		resStr = ""
		for key in values:
			for value in values[key]:
				layerName = value[0].name
				bbox = value[1]
				latency = value[2]
				size = value[3]
				
				latencies.append(latency)
				if key is 2:
					nStr = "'time_%s'=%dms;%s" % (layerName, latency, "crit")
				elif key is 1:
					nStr = "'time_%s'=%dms;%s" % (layerName, latency, "warn")
				else:
					nStr = "'time_%s'=%dms" % (layerName, latency)
					
				nStr += ",'size_%s'=%dB" % (layerName, size)
				
				resStr += ",%s" % (nStr)
					
		latencies.sort()
		
		minStr = ",'min_time'=%dms" % latencies[0]
		maxStr = ",'max_time'=%dms" % latencies.pop()
		oStr = "'time_get_capabilities'=%dms" % getCapabilitiesLatency
		
		return (oStr + maxStr + minStr + resStr)
	


class WebMapService():
	"""docstring for WebMapService"""
	def __init__(self, url, queryStringDict, flagCacheGetCapabilities, fileHandler, timeout = None):
		self.url = url
		self.queryStringDict = queryStringDict
		self.version = queryStringDict['VERSION']
		self.flagCacheGetCapabilities = flagCacheGetCapabilities
		self.formats = []
		self.boundingbox = {}
		self.timeout = timeout
		self.layers = []
		self.operation = {}
		self.fh = fileHandler
		self._newXml()
		self.parseGetCapabilities()
	
		
	def parseGetCapabilities(self):
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
		
		@param	url: The url of the service.
		@param	flagCacheGetCapabilities: The flagCacheGetCapabilities set by the user, if this flagCacheGetCapabilities is said there won't be created a new xml file
		@param	timeout: user specific timeout.
		@param	verison: The version for the servcie.
		@return: The filename of the xml file whether or not a new file was created.
		"""
		fName = self.fh.cache
		try:
			if self.flagCacheGetCapabilities:
				if fName is None or not self._checkDate(fName):
					fName = self.fh.setCap(self.getCapabilities())
					
			else:
				fName = self.fh.setCap(self.getCapabilities())
		except WmsError, e:
			print e.value
			sys.exit(2)
			
		
		self.fName = fName
	
	
	def _checkDate(self, fName):
		"""
		checkData checkes if the data the xml file was created is the same
		as today
		
		@param	fName: The name of the file to check.
		@return: whether or not the file was created today
		"""
		year = t.localtime(os.stat(fName).st_atime).tm_year
		mon = t.localtime(os.stat(fName).st_atime).tm_mon
		day = t.localtime(os.stat(fName).st_atime).tm_mday
		
		if datetime.date(year, mon, day) == datetime.date.today():
			return True
		else:
			return False
	
	
	def getCapabilities(self):
		
		request = self.normalizeGetCapabilitiesRequest()
			
		data = urlencode(request)
		
		xmlCap = urllib2.urlopen((self.url + "?" + data), timeout = self.timeout)
		
		# del request["REQUEST"]
		
		if xmlCap.info()['Content-Type'] == 'application/xml charset=utf-8':
			se_xml = xmlCap.read()
			se_tree = tree.fromstring(se_xml)
			err_message = unicode(se_tree.find('ServiceException').text).strip()
			raise WmsError(err_message)
			
		return xmlCap
	
	
	def normalizeGetCapabilitiesRequest(self):
		"""docstring for normalizeGetCapabilitiesRequest"""
		request = {}
		
		if not "REQUEST" in self.queryStringDict:
			request["REQUEST"] = "GetCapabilities"
		elif not self.queryStringDict["REQUEST"] == "GetCapabilities":
			request["REQUEST"] = "GetCapabilities"
		else:
			request["REQUEST"] = self.queryStringDict["REQUEST"]
			
		request["VERSION"] = self.queryStringDict["VERSION"]
		
		request["SERVICE"] = self.queryStringDict["SERVICE"]
		
		if "SERVICENAME" in self.queryStringDict:
			request["SERVICENAME"] = self.queryStringDict["SERVICENAME"]
			
		if "PASSWORD" in self.queryStringDict:
			request["PASSWORD"] = self.queryStringDict["PASSWORD"]
			
		if "LOGIN" in self.queryStringDict:
			request["LOGIN"] = self.queryStringDict["LOGIN"]
			
		return request
	
	
	def getMap( self, layer, style, srs, 
				bbox, format, imageDimensions,
				bgcolor='#FFFFFF',
				exceptions='application/vnd.ogc.se_xml',
				method='Get' ):
		
		urlBase = self.operation["get"]	  
		
		request = self.queryStringDict
		
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
			request['WIDTH'] = str(imageDimensions[0])
			
		if not 'HEIGHT' in request:
			request['HEIGHT'] = str(imageDimensions[1])
		
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
		
		response = urllib2.urlopen((urlBase + data), timeout = self.timeout)
		# check for service exceptions, and return
		
		if response.info()['Content-Type'] == 'application/vnd.ogc.se_xml':
			se_xml = response.read()
			se_tree = tree.fromstring(se_xml)
			err_message = unicode(se_tree.find('ServiceException').text).strip()
			raise WmsError(err_message)
			
		return response.read()
	
	
	def getRandomGetMapParameters(self, count):
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
	def __init__(self, name, title, srsToBoundingBox):
		"""
		@type	name: string
		@param	name: the name of the layer
		
		@type	title: string
		@param	title: The title of the layer
		
		@type	srs: dict
		@param	srs: A dictionary containing srs's and their bounding box
		
		@rtype: Layer object
		@return: A layer containing all relevant data
		"""
		self.name = name
		self.title = title
		self.srsToBoundingBox = srsToBoundingBox
	
	
	def getRandomBbox(self, srs):
		"""docstring for getRandomBbox
		The calculations in this methode is not 100% accurate
		"""
		bBox = self.srsToBoundingBox[srs]
		geod = Geod(ellps='sphere')
		
		distance = math.sqrt(20000)
		
		latLong = Proj(proj='latlong')
		
		if srs is "EPSG:900913":
			srs = "EPSG:3857"
			
		p = Proj(init=srs)
		minX, minY = transform(p, latLong, bBox[0], bBox[1])
		maxX, maxY = transform(p, latLong, bBox[2], bBox[3])
		
		maxX, maxY, trash = geod.fwd(maxX, maxY, 225, distance)
		
		rMinX = random.uniform(minX, maxX)
		rMinY = random.uniform(minY, maxY)
		
		rMaxX, rMaxY, trash = geod.fwd(rMinX, rMinY, 45, distance)
		
		# transform latlong back to original projection
		res0, res1 = transform(latLong, p, rMinX, rMinY)
		res2, res3 = transform(latLong, p, rMaxX, rMaxY)
		
		randomBox = (str(res0), str(res1), str(res2), str(res3))
		
		return randomBox
	
	
	def checkBbox(self, bbox, srs):
		
		layerBox = map(float, bbox)
		
		serviceBox = map(float, self.srsToBoundingBox[srs])
		
		minX = serviceBox[0] <= layerBox[0] <= serviceBox[2]
		minY = serviceBox[1] <= layerBox[1] <= serviceBox[3]
		
		maxX = serviceBox[0] <= layerBox[2] <= serviceBox[2]
		maxY = serviceBox[1] <= layerBox[3] <= serviceBox[3]
		
		if minX and maxX \
				and minY and maxY:
			return True
		else:
			raise WmsError("The specified bounding box is not supported by the service")


class FileHandler():
	"""docstring for FileHandler"""
	def __init__(self, url):
		homedir = os.path.expanduser('~')
		pattern = "http://(.[^/]+)"
		self.dirName = re.findall(pattern, url)[0].replace(".", "_")
		self.picDir =  homedir + "/check_wms_files/images/" + self.dirName
		self.capDir = homedir + "/check_wms_files/.cache"
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
			
		cDir = fDir + "/.cache"
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
	


CheckWms(options, args).run()

