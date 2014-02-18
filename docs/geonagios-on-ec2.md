# Installing GeoNagios on Amazon EC2

GeoNagios is a collection of Python scripts with a name of: 

* <tt>check_[name of protocol].py</tt>

GeoNagios depends on:

* gcc (for installing pyproj)
* Python
* Python development headers (for installing pyproj)
* pyproj

This document describes how to install the collection of scripts, with their dependencies. First an instruction is shown for EC2: 

## EC2 installation instructions

Instance AMI: Amazon Linux AMI 64 bit

### EC2: Installing Dependencies

Install gcc:

```
gcc --version
# If command not found: do the following
sudo yum install gcc
```

Install Python (actually Python 2.6 should already be installed):

```
# Python 2.6 should already be installed on the instance
python --version
# If command not found: do the following
sudo yum install python26.x86_64
```

Install Python development headers:

```
sudo yum install python26-devel.x86_64
```

Install pyproj using easy_install:

```
sudo easy_install pyproj
```

Or, if you prefer pip:

```
# sudo easy_install pip
sudo pip install pyproj
```

Test installation:

```
$ python
>>> import pyproj
>>>
```

If you didn't get an error, the dependencies have been installed.

## EC2: Installing GeoNagios/check_wms.py

```bash
# Download the script
curl -o check_wms.py https://raw.github.com/skipperkongen/GeoNagios/master/check_wms.py
# Change permissions
chmod u+x check_wms.py
chown nagios:nagios check_wms.py
# Move script to Nagios plugin folder
mv check_wms.py path-to-nagios-plugins-folder
```

This installation procedure has not been tested yet, so need to verify that it works.