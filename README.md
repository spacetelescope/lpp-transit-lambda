# LPP transit metric code ported to Python from the DR25 Kepler Robovetter.

This repository builds a AWS Lambda function that can be used to calculate LPP transit metrics for TESS Candidate Events (TCEs).

Build the astropy, lpproj, numpy, scipy, and scikit-learn packages and strip them down to run in Lambda

This repository contains a `build.sh` script that's intended to be run in an Amazon Linux docker container (i.e. AWS Lambda), and builds astropy, lpproj, numpy, scipy, and scikit-learn to calculate the LPP transit metrics.

For more info about how the script works, and how to use it, see the blog post by `ryansb` [on deploying sklearn to Lambda](https://serverlesscode.com/post/scikitlearn-with-amazon-linux-container/). This repository is a fork of the excellent work by `ryanb` in https://github.com/ryansb/sklearn-build-lambda .

To build the zipfile, pull the Amazon Linux image and run the build script in it.

```
$ docker pull amazonlinux:2017.09
$ docker run -v $(pwd):/outputs -it amazonlinux:2017.09 /bin/bash /outputs/build.sh
```

That will make a file called `venv.zip` in the local directory that's around 65MB.

Once you run this, you'll have a zipfile containing astropy, lpproj, numpy, scipy, and scikit-learn and their dependencies. This repository also contains a file called `process.py` which imports these packages and verifies the TCEs.

```python
import os
import subprocess
import uuid

libdir = os.path.join(os.getcwd(), 'lib')

import warnings
from astropy.utils.data import CacheMissingWarning
warnings.simplefilter('ignore', CacheMissingWarning)

from astropy.io import fits
import boto3
from datetime import date
from lppDataClasses import TCE
from lppDataClasses import MapInfo
import lppTransform as lppt
import numpy as np

mapfilename = 'combMapDR25AugustMapDV_6574.mat'
mapfilepath = '/tmp/combMapDR25AugustMapDV_6574.mat'
columns = ['id','planetNum','sector','period','tzero','depth','dur','mes','normTLpp','rawTLpp']
...
...
...
```

## Extra Packages

To add extra packages to the build, add them to the `requirements.txt` file alongside the `build.sh` in this repo. All packages listed there will be installed in addition to those already described in [`build.sh`](https://github.com/spacetelescope/astropy-sep-lambda/blob/f3f34a6c1b8e6bd451de5c8ff6dc1f5e5cd193f8/build.sh#L18-L20)

## Testing locally

Testing Lambda locally is a pain, but thanks to the efforts of the Lambci folks in https://github.com/lambci/docker-lambda, we can test a function locally as follows:

First, build the Lambda function locally with the command from above:

```
$ docker run -v $(pwd):/outputs -it amazonlinux:2017.09 /bin/bash /outputs/build.sh
```

This should leave you with a `venv.zip` file. Unzip this with:

```
$ unzip venv.zip -d venv
```
Next enter the `venv` directory and try running the command, passing in your `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY` as environment variables:

```
$ cd venv
$ docker run --rm -e AWS_ACCESS_KEY_ID='XXXXXXXXXXXXX' -e AWS_SECRET_ACCESS_KEY='XXXXXXXXXXXXX' -v "$PWD":/var/task lambci/lambda:python3.6 process.handler '{"s3_output_bucket": "dsmo-lambda-test-outputs", "fits_s3_key":"tess/public/tid/s0001/0000/0001/1498/5772/tess2018206190142-s0001-s0001-0000000114985772-00106_dvt.fits", "fits_s3_bucket":"stpubdata", "planet_number": 1, "ticid": 114985772, "sector": 1}'
```
## Sizing and Future Work

In its current form, this set of packages weighs in at 50MB and could probably be reduced further by:

1. Pre-compiling all .pyc files and deleting their source
1. Removing test files
1. Removing documentation

According to [this article](https://docs.aws.amazon.com/lambda/latest/dg/limits.html) the size limit for a zipped Lambda package (the `venv.zip` file) is 50MB, however, reading around it seems like Lambda is tolerant of significantly larger packages when the zipped package is posted to S3.
