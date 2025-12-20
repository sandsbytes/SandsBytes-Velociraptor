import sys
import json
import requests
import os
import shutil
import uuid
from pathlib import Path
import argparse
from sandsbytes_sdk.http_client import HTTPClient
import zipfile
import zlib


import logging

logging.getLogger("sandsbytes_sdk").disabled = True
# Also disable in all sub-packages
for name in list(logging.Logger.manager.loggerDict):
    if name.startswith("sandsbytes_sdk"):
        logging.getLogger(name).disabled = True

parsers_list = ["024d5499-5cd0-4897-8558-218d68639597"]

def zipdir(src_dir, zip_file_path, exclude_patterns=None):
    exclude_patterns = exclude_patterns or []

    with zipfile.ZipFile(zip_file_path, "w", zipfile.ZIP_DEFLATED) as z:
        for root, dirs, files in os.walk(src_dir):
            for file in files:
                file_path = os.path.join(root, file)

                # Skip excluded patterns
                if any(pattern in file_path for pattern in exclude_patterns):
                    continue

                # Add file with relative path
                z.write(file_path, os.path.relpath(file_path, src_dir))


def rezip(original_zip, output_zip):
    with zipfile.ZipFile(output_zip, "w", zipfile.ZIP_DEFLATED) as z:
        z.write(original_zip, arcname=original_zip.name)

def is_zlib(path):
    with open(path, "rb") as f:
        data = f.read(2)
    return data.startswith(b'\x78')

def compress_results(results_path: str, artifact_name: str, temporary_directory: str, hostname: str):

    temp_dir_id = str(uuid.uuid4())
    # Generate a unique temp folder name (UUID)
    temp_folder = Path(temporary_directory) / temp_dir_id
    results_folder = temp_folder / "results"

    # Create the temp and results folders
    results_folder.mkdir(parents=True, exist_ok=True)

    # Copy the results file into the results folder as "{artifact_name}.json"
    destination_file = results_folder / f"{artifact_name}.json"


    # check if the destination_file is compressed with zlib, then decompress it to a temporary folder
    if is_zlib(results_path):
        with open(results_path, "rb") as f:
            data = f.read()
        decompressed_data = zlib.decompress(data)
        with open(destination_file, "wb") as f:
            f.write(decompressed_data)
    else:
        shutil.copy(results_path, destination_file)



    # Zip the temp folder
    zip_filename = Path(temporary_directory) / temp_dir_id / f"velociraptor-{hostname}.zip"
    
    zipdir(temp_folder, zip_filename, exclude_patterns=[f"velociraptor-{hostname}.zip"])
    
    package_zip = Path(temporary_directory) / temp_dir_id / f"{temp_dir_id}.zip"
    rezip(zip_filename, package_zip)
    # Optionally, cleanup if needed
    # shutil.rmtree(temp_folder)
    return package_zip

def upload_results(zip_filename: str, sandsbytes_url: str, sandsbytes_username: str, sandsbytes_password: str, case_ids: list[str], auto_process: bool):
    # Initialize the SandsBytes client
    client = HTTPClient(
        base_url=sandsbytes_url,
        config_file=os.path.join(os.path.dirname(os.path.abspath(__file__)), "sandsbytes_sdk", "config.json"),
        ignore_ssl=True  # Set to False for production with valid SSL
    )

    to_be_processed = {}
    # Authenticate with your SandsBytes credentials
    if client.authenticate(sandsbytes_username, sandsbytes_password):
        
        for case_id in case_ids:
            if case_id not in to_be_processed:
                to_be_processed[case_id] = []


            case = client.cases.list(params={"query": json.dumps([{"field": "id", "op": "==", "value": case_id}])})
            if case['total'] > 0:
                package_id = None
                case = case['cases'][0]
                # check if triage exists, if not create it
                triage = client.packages.list(case_id=case_id, params={"query": json.dumps([{"field": "name", "op": "==", "value": hostname}])})

                if triage['total'] == 0:
                    package = client.packages.create(case_id=case_id, data={"name": hostname})
                    package_id = package['id']
                else:
                    package_id = triage['packages'][0]['id']

                # upload the results file to the package

                files = [
                    ("files", (zip_filename.name, open(zip_filename, 'rb'), "application/x-zip-compressed"))
                ]

                res = client.packages.upload_file(case_id=case_id, package_id=package_id, data={}, files=files)
                to_be_processed[case_id].append(package_id)



    # start processing the cases
    if auto_process:
        for case_id, package_ids in to_be_processed.items():
            if len(package_ids) > 0:
                res = client.cases.process(
                    case_id=case_id, 
                    data = {"packages_ids": package_ids, "parsers_ids": parsers_list}
                )
    
    
    

def main(
        artifact_name: str, 
        results_path: str, 
        temporary_directory: str,
        hostname: str,
        sandsbytes_url: str,
        sandsbytes_username: str,
        sandsbytes_password: str,
        case_ids: list[str],
        auto_process: bool
        ):

    zip_filename = compress_results(
        results_path=results_path, 
        artifact_name=artifact_name, 
        temporary_directory=temporary_directory, 
        hostname=hostname
    )
    upload_results(
        zip_filename=zip_filename, 
        sandsbytes_url=sandsbytes_url, 
        sandsbytes_username=sandsbytes_username, 
        sandsbytes_password=sandsbytes_password, 
        case_ids=case_ids,
        auto_process=auto_process
    )
    print("Successfully shipped results to SandsBytes")
    return True



if __name__ == "__main__":
    

    try:
        parser = argparse.ArgumentParser(description="Ship Velociraptor artifact results.")
        parser.add_argument('-a', '--artifact', required=True, help='Artifact name')
        parser.add_argument('-f', '--file', required=True, help='Input results file path')
        parser.add_argument('-c', '--client_hostname', required=True, help='Client hostname')
        parser.add_argument('-t', '--tempdir', required=False, default='/tmp', help='Temporary directory (optional)')
        parser.add_argument('-s', '--sandsbytes_url', required=True, help='SandsBytes URL')
        parser.add_argument('-u', '--sandsbytes_username', required=True, help='SandsBytes username')
        parser.add_argument('-p', '--sandsbytes_password', required=True, help='SandsBytes password')
        parser.add_argument('-l', '--labels', required=True, default='', help='Client labels')

        parser.add_argument(
            '-ap', '--auto_process',
            default='false',
            required=False,
            help='Automatically process the uploaded packages (include this flag to enable, omit for false).'
        )

        args = parser.parse_args()

        artifact_name = args.artifact
        results_file_path = args.file
        temporary_directory = args.tempdir
        hostname = args.client_hostname
        sandsbytes_url = args.sandsbytes_url
        sandsbytes_username = args.sandsbytes_username
        sandsbytes_password = args.sandsbytes_password
        labels = args.labels
        auto_process = args.auto_process == 'true'

        case_ids = [label.lstrip('case_') for label in labels.split(',') if label.startswith('case_')]

        main(
            artifact_name=artifact_name, 
            results_path=results_file_path, 
            temporary_directory=temporary_directory, 
            hostname=hostname, 
            sandsbytes_url=sandsbytes_url, 
            sandsbytes_username=sandsbytes_username, 
            sandsbytes_password=sandsbytes_password,
            case_ids=case_ids,
            auto_process=auto_process
        )

    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)