#!/usr/bin/env python2
# encoding: utf-8

import os
import sys
import json
import requests
import zipfile
import urllib

HEADERS = { "Content-Type": "application/json" }
MULTIPART = { "Content-Type": "multipart/form-data" }

import config as C

try:
    os.mkdir("tmp")
except OSError as e:
    pass

class Deposition:
    def __init__(self, doi, meta):
        data = json.dumps({ "metadata": { "doi": doi } })
        q = "?access_token=" + C.token + "&q=" + "doi:" + doi.replace("/", "\/")
        deps = requests.get(C.zenodo + "/deposit/depositions" + q).json()
        if len(deps) > 0:
            print("resource found...")
            self.id = deps[0]['id']
        else:
            meta['upload_type'] = "dataset"
            meta['doi'] = doi
            data = json.dumps({ "metadata": meta })
            q = "?access_token=" + C.token
            print("creating a new resource...")
            r = requests.post(C.zenodo + "/deposit/depositions" + q,
                              headers=HEADERS, data=data)
            self.id = r.json()['id']

    def url(self, path=""):
        query = "?access_token=" + C.token
        return C.zenodo + "/deposit/depositions/" + str(self.id) + path + query

    def upload(self, name, url):
        files = requests.get(self.url("/files")).json()
        for f in files:
            if f['filename'] == name:
                print("deleting " + f['filename'] + "...")
                requests.delete(self.url("/files/" + f['id']))
        urllib.urlretrieve(url, "tmp/dwca.zip")
        data = { 'filename': name }
        files = { 'file': open("tmp/dwca.zip", "rb") }
        print("uploading " + url)
        r = requests.post(self.url("/files"), data=data, files=files)

if len(sys.argv) < 2:
    sys.stderr.write("%s <gbif dataset uuid>\n" % sys.argv[0])
    sys.exit(0)

uuid = sys.argv[1]

gbifmeta = requests.get(C.gbif + "/dataset/" + uuid).json()

meta = {}
meta['creators'] = []
for contact in gbifmeta["contacts"]:
    if contact['type'] == "ORIGINATOR":
        if 'lastName' in contact and 'firstName' in contact:
            creator = {
                'name': "%s, %s" % (contact['lastName'], contact['firstName'])
            }
            meta['creators'].append(creator)

if len(meta['creators']) == 0: del meta['creators']
meta['title'] = gbifmeta['title']
meta['description'] = gbifmeta['description']
if gbifmeta["license"] == "http://creativecommons.org/licenses/by/4.0/legalcode":
    meta["license"] = "cc-by"
meta["keywords"] = [ "biodiversity", "gbif" ]

deposition = Deposition(gbifmeta['doi'], meta)

for endpoint in gbifmeta['endpoints']:
    if endpoint['type'] == "DWC_ARCHIVE":
        deposition.upload("dwca.zip", endpoint['url'])
        sys.exit(0)

