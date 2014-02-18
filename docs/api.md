# GeoNagios API

One way to see the options a GeoNagios <tt>check_[protocol].py</tt> accepts, is to run it with `-h` option.

## check_wms

Get usage for `check_wms.py`:

```
./check_wms.py -h
```

Prints the following usage message:

```
Usage: check_wms.py [options]

Options:
  -h, --help     show this help message and exit
  -w WARNING     The maximum time, accepted for the service to run normally
  -c CRITICAL    The threshold for the test, if the service doesn't respon by
                 this time                             it's considered to be
                 down
  -t TIMEOUT     set the timeout timer (default is 30 sec.)
  -n LAYER-COUNT  The numbers of layers to be checked (default is all of them)
  --cache        Attempt to read GetCapabilities document from disc
  --image        Set this flag, if you want to save the pictures on disc
  -l             Get list of all layers published by service, without testing them
  -g             Return a geographical point inside each bounding box used for testing
  -s LAYER       Specify specific layers to test (if multiple layers seperate with a comma)
```