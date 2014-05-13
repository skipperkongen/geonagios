# About GeoNagios

GeoNagios is a plugin for the monitoring system [Nagios](http://nagios.org/). It tests the availability and performance of a geospatial web service, e.g. [Web Map Service](http://en.wikipedia.org/wiki/Web_Map_Service) (WMS). It measures latency and size of response in bytes. 

<table>
<tr><th>Protocol</th><th>Implemented by</th><th>Finished</th><th>Contributor</th></tr>
<tr><td>WMS</td><td>check_wms.py</td><td>✓</td><td>[Skipperkongen](https://github.com/skipperkongen), [Warlink](https://github.com/warlink), [JesperKihlberg](https://github.com/jesperkihlberg)</td></tr>
<tr><td>WMTS</td><td>check_wmts.py</td><td>✓</td><td>[JesperKihlberg](https://github.com/jesperkihlberg)</td></tr>
<tr><td>WFS</td><td>check_wfs.py</td><td></td><td></td></tr>
<tr><td>WCS</td><td>check_wcs.py</td><td></td><td></td></tr>
<tr><td>CSW</td><td>check_csw.py</td><td></td><td></td></tr>
<tr><td>TMS</td><td>check_tms.py</td><td></td><td></td></tr>
</table>

GeoNagios has been developed with support from the [Danish Geodata Agency](http://www.gst.dk) and the [University of Copenhagen, Department of Computer Science](http://di.ku.dk/).

## Dependencies

GeoNagios is written in [Python](http://www.python.org/) (tested with 2.6 and 2.7). Dependencies are Python 2.5+ and [pyproj](http://code.google.com/p/pyproj/). It currently only supports WMS, but additional protocols are planned.

```bash
# easy_install pyproj
pip install pyproj  # maybe need 'sudo' in front
```

## Getting started with GeoNagios

Get a copy of *check_wms.py*:

```bash
curl -o check_wms.py https://raw.github.com/skipperkongen/GeoNagios/master/check_wms.py
chmod u+x check_wms.py
```

Get help by calling *check_wms.py* with the *--help* option:

```bash
$./check_wms.py --help
```

List the layers available for a WMS service by calling *check_wms.py* with the *--list-layers* option:

```bash
$ ./check_wms.py --list-layers 'http://kortforsyningen.kms.dk/service?ticket=1940ecb511e4d1a92df01347a85aa30f&servicename=dagi' 
politikreds
sogn
kommune
region
retskreds
opstillingskreds
postdistrikt
```

Test all the layers by calling *check_wms.py* without options (only the URL argument):

```bash
$ ./check_wms.py 'http://kortforsyningen.kms.dk/service?ticket=1940ecb511e4d1a92df01347a85aa30f&servicename=dagi' | tr ',' '\n' | tr '|' '\n'
OK
'time_get_capabilities'=710ms
'max_time'=330ms
'min_time'=62ms
'time_region'=330ms
'size_region'=1340B
'time_kommune'=76ms
'size_kommune'=1340B
'time_politikreds'=67ms
'size_politikreds'=1340B
'time_retskreds'=67ms
'size_retskreds'=1340B
'time_opstillingskreds'=62ms
'size_opstillingskreds'=1340B
'time_sogn'=71ms
'size_sogn'=1340B
'time_postdistrikt'=140ms
'size_postdistrikt'=1340B
```

Test some of the layers by calling *check_wms.py* with the *--specific-layers* option:

```bash
$ ./check_wms.py --specific-layers 'COMMA-SEPARATED-LAYER-NAMES' [SERVICEURL]
``` 

Test *n* randomly picked layers by calling *check_wms.py* with the *--n-layers* option:

```bash
$ ./check_wms.py --n-layers INTEGER [SERVICEURL]
```

## Configure Nagios to use GeoNagios

Remember there are multiple ways to configurate Nagios. This is just one way! 

### Define host

Host template:

```
define host {
        name                            generic-wmshost ; The name of this host template
        hostgroups                      geospatial-servers
        notifications_enabled           0
        check_command                   check-wms
        check_interval                  1
        retry_interval                  1
        max_check_attempts              5
        check_period                    24x7
        event_handler_enabled           1               ; Host event handler is enabled
        flap_detection_enabled          1               ; Flap detection is enabled
        failure_prediction_enabled      1               ; Failure prediction is enabled
        process_perf_data               1               ; Process performance data
        retain_status_information       1               ; Retain status information across program restarts
        retain_nonstatus_information    1               ; Retain non-status information across program restarts
        register                        0               
}
```

Host:

```
define host {
        use             generic-wmshost
        host_name       plansystem
        alias           Plansystem - local plans for Denmark
        address         http://kort.plansystem.dk
	action_url	/wms?servicename=wms
}
```

### Define command:

(I have defined $USER3$ to point to where check_wms.py is)

```
define command {
        command_name check_wms_py
        command_line    $USER3$/check_wms.py $HOSTADDRESS$$HOSTACTIONURL$ $ARG1$
}
```

### Define service:
```
define service {
        use             generic-service
        host_name       plansystem, eea_europa, arealinfo, vienna, kortforsyningen
        service_description check_wms_services
        check_command   check_wms_py ! -n 5 --cache
}
```

## Additional documentation

* [How GeoNagios works](docs/how-geonagios-works.md) - Description of the method used to test services
* [Installing GeoNagios on EC2](geonagios-on-ec2.md) - These instruction are for Amazon Linux AMI 64 bit, but can easily be adopted for Windows, Mac OS X or another Linux flavour.
