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

# Download the map file unless we already have it.
# Lambda functions are often cached and so it's
# possible that the map file will be available between
# Lambda executions.
def download_map():
    if os.path.exists(mapfilepath):
        pass
    else:
        s3 = boto3.resource('s3')
        s3_client = boto3.client('s3')
        bkt = s3.Bucket('mast-labs-s3')
        bkt.download_file(mapfilename, mapfilepath)

def download_dvt(event):
    dvt_file_key = event['fits_s3_key']
    dvt_file_bucket = event['fits_s3_bucket']

    root = dvt_file_key.split('/')[-1].split('_')[0]
    s3 = boto3.resource('s3')
    s3_client = boto3.client('s3')
    bkt = s3.Bucket(dvt_file_bucket)
    bkt.download_file(dvt_file_key, '/tmp/{0}'.format(root), ExtraArgs={"RequestPayer": "requester"})

def cleanup_dvt(event):
    dvt_file_key = event['fits_s3_key']
    root = dvt_file_key.split('/')[-1].split('_')[0]

    if os.path.exists('/tmp/{0}'.format(root)):
        os.remove('/tmp/{0}'.format(root))

def write_results(tceDict, s3_output_bucket):
    # Write the file locally then upload to S3
    tic_id = tceDict['id']
    sector = tceDict['sector']
    planet = tceDict['planetNum']

    outputfilename = f"{tic_id}_{planet}_{sector}.txt"
    outputfilepath = f"/tmp/{outputfilename}"

    output = open(outputfilepath,'w')

    output.write("# TCE Table with Normalized LPP Transit Metric.\n")
    output.write("# Date: %s\n" % str( date.today() ))

    # Write the header
    for c in columns:
        output.write("%s  " % c)
    output.write("\n")

    # Write the values
    for c in columns:
        output.write("%s " % str(tceDict[c]))
    output.write("\n")

    output.close()

    # Write out to S3
    s3 = boto3.resource('s3')
    s3.meta.client.upload_file(outputfilepath, s3_output_bucket, '{0}/{1}'.format(tic_id, outputfilename))

    # Finally, clean up the output file
    os.remove(outputfilepath)

def compute_transit_metric(event):
    planet_number = event['planet_number']
    ticid = event['ticid']
    sector = event['sector']

    mapInfo = MapInfo(mapfilepath)

    dvt_file = event['fits_s3_key']
    root = dvt_file.split('/')[-1].split('_')[0]

    data, header = fits.getdata('/tmp/{0}'.format(root), ext=planet_number, header=True)
    tce=TCE(ticid, planet_number)
    tce.populateFromDvExt(data, header)
    tce.sector = sector

    normTLpp, rawTLpp, transformedTr=lppt.computeLPPTransitMetric(tce, mapInfo)
    tce.normTLpp=normTLpp
    tce.rawTLpp = rawTLpp
    tce.transformedLppTr = transformedTr
    tceDict=tce.__dict__

    write_results(tceDict, event['s3_output_bucket'])

def handler(event, context):
    download_map()
    download_dvt(event)
    compute_transit_metric(event)
    cleanup_dvt(event)

if __name__ == "__main__":
    handler('', '')
