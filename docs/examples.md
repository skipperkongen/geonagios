## Commandline examples

###List all layers in a WMS service:

```
$ python check_wms.py 'http://kort.plansystem.dk/wms?servicename=wms' -l
```
If you don't know which layers the WMS service has, you can use this command to get them listed.

Output:

```
The layers for url http://kort.plansystem.dk/wms are:
theme-pdk-specifikgeologiskbevaringsvaerdi_forslag
theme-pdk-virksomhedsaerligtbeliggenhedskrav_aflyst
theme-pdk-vaerdifuldtlandbrugsomraade_aflyst
...
theme-pdk-oekologiskforbindelse_vedtaget
```

###Test a service where the script generrates random bounding boxes and uses random layers:

```
$ python check_wms.py 'http://kort.plansystem.dk/wms?servicename=wms' -n 5
```
This command can be used to test random layers with a random bounding box.
The "-n" option lets you set how many layers you want to test.

Output:

```
OK|'t_get_capabilities'=2219ms,'t_max'=546ms,'t_min'=391ms,'t_theme-pdk- 
bevaringsvaerdigtlandskab_aflyst'=479ms,'s_theme-pdk-bevaringsvaerdigtlandskab_aflyst'=415B,'t_theme-pdk-     
lokalplandelomraade-aflyst'=393ms,'s_theme-pdk-lokalplandelomraade-aflyst'=415B,'t_theme-pdk-
planlagttrafikanlaeg_vedtaget'=391ms,'s_theme-pdk-planlagttrafikanlaeg_vedtaget'=415B,'t_theme-pdk-
oekologiskforbindelse_forslag'=546ms,'s_theme-pdk-oekologiskforbindelse_forslag'=415B,'t_theme-pdk-
bevaringsvaerdigtlandskab_forslag'=408ms,'s_theme-pdk-bevaringsvaerdigtlandskab_forslag'=415B
```

###Test a service with a specific layer:

```
$ python check_wms.py 'http://kort.plansystem.dk/wms?servicename=wms' -s theme-pdk-oekologiskforbindelse_vedtaget
```

Output:

```
OK|'t_get_capabilities'=676ms,'t_max'=676ms,'t_min'=676ms,'t_theme-pdk-
oekologiskforbindelse_vedtaget'=676ms,'s_theme-pdk-oekologiskforbindelse_vedtaget'=873B
```

###Test a service with the full query string:
```
python check_wms.py 'http://kort.plansystem.dk/wms?servicename=wms&BBOX=868659,6218505,868759,6218505&SRS=EPSG:25832' -n 1
```

Output:
```
OK|'t_get_capabilities'=435ms,'t_max'=435ms,'t_min'=435ms,'t_theme-pdk-oekologiskforbindelse_aflyst'=435ms,'s_theme-pdk-oekologiskforbindelse_aflyst'=415B
```
## Nagios config example
Remember there are multiple ways to configurate Nagios. This is just one way! 
###Define host
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

###Define command:
(I have defined $USER3$ to point to where check_wms.py is)
```
define command {
        command_name check_wms_py
        command_line    $USER3$/check_wms.py $HOSTADDRESS$$HOSTACTIONURL$ $ARG1$
}
```

###Define service:
```
define service {
        use             generic-service
        host_name       plansystem, eea_europa, arealinfo, vienna, kortforsyningen
        service_description check_wms_services
        check_command   check_wms_py ! -n 5 --cache
}
```
