#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
from flask import Flask, render_template, request, send_from_directory, Response
from werkzeug import secure_filename
from werkzeug.datastructures import FileStorage
import hashlib

from flask_restful import Api
from restapi import DetectType3
from restapi.Uploader import Uploader
from restapi.FetchBaiduApi import FetchBaiduApi
from restapi.DatabaseApi import FetchRecordsApi, InsertRecordApi, InsertResultApi
import logging
import argparse
from datetime import datetime
from shutil import copyfile
from flask_cors import CORS

app = Flask(__name__)
cors = CORS(app, resources="/api/*", allow_headers='*', origins='*', expose_headers='Authorization')

# MySQL configurations
DB_HOST='localhost'
DB_USER='testuser'
DB_PASSWD='abcd1234'
DB_NAME='invoicedetector'

api = Api(app)

logging.basicConfig(level=logging.DEBUG, format="[%(asctime)s] %(levelname)-5s %(name)-8s - %(message)s")

DEBUG_FILE_NUM=10

@app.route('/health')
def heath_check():
    return 'OK'

@app.route('/')
def index():
      return app.send_static_file('index.html')

@app.after_request
def add_header(response):
    response.headers['Access-Control-Allow-Origin'] = '*'
    return response

api.add_resource(Uploader, '/api/upload')

api.add_resource(DetectType3.DetectType3Api, '/api/detect_in',
        resource_class_kwargs={'DB_HOST': DB_HOST, 'DB_USER': DB_USER, 'DB_PASSWD': DB_PASSWD, 'DB_NAME': DB_NAME})

api.add_resource(DetectType3.GetTaskImageApi, '/api/fetch/image',
        resource_class_kwargs={'DB_HOST': DB_HOST, 'DB_USER': DB_USER, 'DB_PASSWD': DB_PASSWD, 'DB_NAME': DB_NAME})

api.add_resource(FetchRecordsApi, '/api/fetch/records', 
        resource_class_kwargs={'DB_HOST': DB_HOST, 'DB_USER': DB_USER, 'DB_PASSWD': DB_PASSWD, 'DB_NAME': DB_NAME})

api.add_resource(InsertRecordApi, '/api/insert/record', 
        resource_class_kwargs={'DB_HOST': DB_HOST, 'DB_USER': DB_USER, 'DB_PASSWD': DB_PASSWD, 'DB_NAME': DB_NAME})

api.add_resource(InsertResultApi, '/api/insert/result', 
        resource_class_kwargs={'DB_HOST': DB_HOST, 'DB_USER': DB_USER, 'DB_PASSWD': DB_PASSWD, 'DB_NAME': DB_NAME})


# construct the argument parse and parse the arguments
ap = argparse.ArgumentParser()
ap.add_argument("-d", "--dir", required=True,
        help="path to the directory contains source images")
args = vars(ap.parse_args())

def getValidImgFileList():
    rootDir = args["dir"]
    lstValidImgFile = []
    bExitLoop = False
    for parent, dirnames, filenames in os.walk(rootDir):
        for filename in filenames:
            if filename.endswith(".jpg") or filename.endswith(".jpeg"):
                imgFile = os.path.join(parent,filename)
                lstValidImgFile.append(imgFile)
            else:
                if filename.endswith(".png") or filename.endswith(".bmp"):
                    imgFile = os.path.join(parent,filename)
                    lstValidImgFile.append(imgFile)
        if bExitLoop:
            break

    return lstValidImgFile;
    
def get_filePath_fileName(filename):  
    (filepath,tempfilename) = os.path.split(filename);  
    (shortname,extension) = os.path.splitext(tempfilename);  
    return shortname, extension

def main():
    lstVaildImgFiles = getValidImgFileList()

    obj = DetectType3.DetectType3Api()

    #obj.post()
    nIndex = 0
    for imgFile in lstVaildImgFiles:
        print(imgFile)

	# process images count not bigger than specific value
        if nIndex == DEBUG_FILE_NUM:
            break

        (strJobID, fext) = get_filePath_fileName(imgFile)

        strJobID_with_index = str(nIndex) + "_" + strJobID 
	
        print("strJobID =>", strJobID)
        strFilePath = imgFile
        obj.post2(strJobID_with_index, strFilePath)
        nIndex = nIndex + 1

def test():
    obj = DetectType3.DetectType3Api()
    strJobID="7251cc1147be4726f175a09612b05b90"

    print(strJobID)
    strFilePath = args['dir'] + "/" + strJobID +".jpg"
    obj.post2(strJobID, strFilePath)
    pass


if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True)
    #app.run(debug=True)
    #main()
    #test()
