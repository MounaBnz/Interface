from flask import Flask, Blueprint, request, jsonify,send_from_directory
from flask_cors import CORS, cross_origin

from model import predict
from tensorflow.keras.models import load_model
import pandas
from werkzeug.utils import secure_filename

import os
from dotenv import load_dotenv
#Blob
from azure.storage.blob import BlobServiceClient

#SQL
import pyodbc, struct
from azure import identity
from typing import Union
# from fastapi import FastAPI
from pydantic import BaseModel

#for connecting with service principal
import msal
import adal




#loading .env to environment
load_dotenv()

app = Flask(__name__)
cors = CORS(app)
UPLOAD_FOLDER = './input_images'
app.config['CORS_HEADERS'] = 'Content-Type'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER


#Connection strings to SQL DB and Blob Storage
sql_connection_string = os.environ["AZURE_SQL_CONNECTION_STRING"]
blob_connection_str = os.getenv('AZURE_STORAGE_CONNECTION_STRING')



class Embryo(BaseModel):

    # ImageUrl: Union[str, None] = None
    ImageName:str
    Result: str
    suggested_value:Union[str, None] = None
    note:Union[str, None] = None


@app.route('/')
def index():
    print("Hello, World!")
    return "Hello, World!"

@app.route('/upload', methods=['POST'])
def upload_image():
    try:
        if 'image' not in request.files:
            return jsonify({'error': 'No file part in the request'}), 400

        uploaded_file = request.files['image']
        if uploaded_file.filename == '':
            return jsonify({'error': 'No selected file'}), 400

        if uploaded_file and allowed_file(uploaded_file.filename):
            filename = secure_filename(uploaded_file.filename)
            destination_file = os.path.join(app.config['UPLOAD_FOLDER'], filename)

            #saving image locally
            uploaded_file.save(destination_file)

            #saving image in blob
            saveToBlob(uploaded_file,destination_file)

            #processing the image
            result = process_image(filename)

            #saving image in sql db
            embryo= Embryo(ImageName=filename,Result=result,suggested_value=None,note=None)
            saveToSQLDB(embryo)

            #Retrieve image and result
            # print(get_image_and_result(filename))

            # Embed the result with the image URL
            image_with_result = {'image':destination_file , 'result': result}
            # This are returns for just the upload
            #     return jsonify({'message': 'File uploaded successfully', 'file': filename}), 201
            # else:
            #     return jsonify({'error': 'Invalid file type, only JPEG images are allowed'}), 400

            return jsonify({'message': 'Image processed successfully', 'image_with_result': image_with_result}), 201
        else:
            return jsonify({'error': 'Invalid file type, only JPEG images are allowed'}), 400


    except Exception as e:
        return jsonify({'error': str(e)}), 500

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in {'jpg','png', 'jpeg','bmp'}

def process_image(image_name):

    predict()
    # Load the results CSV file
    labled_results_csv_file='./results/labled_results_csv.csv'
    results_df = pandas.read_csv(labled_results_csv_file)

    row = results_df.loc[results_df['image_name'] == image_name]
    result=row['classification'].to_string(index=False)
    print(image_name)
    print(result)
    return result


# Function to establish connection to blob storage
def get_blob_service_client():
    # retrieve the connection string from the environment variable
    return BlobServiceClient.from_connection_string(blob_connection_str)

# retrieve the container name (in which images will be store in the storage account)  from the environment variable
container_name = os.environ["CONTAINER_NAME"]
def saveToBlob(file,filepath):
    blob_service_client=get_blob_service_client()
    try:

        container_client = blob_service_client.get_container_client(container=container_name) # get container client to interact with the container in which images will be stored
        container_client.get_container_properties() # get properties of the container to force exception to be thrown if container does not exist
    except Exception as e:
        print(e)
        print("Creating container...")
        container_client = blob_service_client.create_container(container_name) # create a container in the storage account if it does not exist

    try:
        with open(file=filepath, mode="rb") as data:
            print("before blob")
            blob_client = container_client.upload_blob(name=file.filename, data=data, overwrite=True)
            print("after blob")
    except Exception as e:
        print(e)
        print("Ignoring duplicate filenames") # ignore duplicate filenames


def saveToSQLDB(item: Embryo):
    print("********* saving data to DB .... ********* ")
    #Environments variables to have access to Blob Storage
    sas_token=os.environ["SAS_TOKEN"]
    storage_account_url=os.environ["STORAGE_ACCOUNT_URL"]

    try:
        
        # conn = get_conn()
        conn=connect_oauth()
        cursor = conn.cursor()

        #Apparently this is why it doesn't recognize the storage account , the string being overwritten and null

        # Table should be created ahead of time in production app.
        cursor.execute("""

            CREATE TABLE EmbryoResults (
                Id INT NOT NULL PRIMARY KEY IDENTITY,
                ImageName NVARCHAR(MAX),
                Result NVARCHAR(MAX),
                SuggestedValue NVARCHAR(MAX) NULL,
                Note NVARCHAR(MAX) NULL
            );
        """)

        conn.commit()

        # This is two sql queries are for retrieving image url and storing it in DB

        # #creating external Azure Blob data source
        # cursor.execute("""
        #     CREATE DATABASE SCOPED CREDENTIAL sampleblobcred1
        #         WITH IDENTITY = 'SHARED ACCESS SIGNATURE',
        #         SECRET = ?;
        # """,(sas_token,))

        # conn.commit()


        # cursor.execute("""
        #     CREATE EXTERNAL DATA SOURCE blobstorage
        #     WITH (
        #         TYPE = BLOB_STORAGE,
        #         LOCATION = ?,
        #         CREDENTIAL = sampleblobcred1);
        #     """, (storage_account_url,))



        # conn.commit()
    except Exception as e:
        # Table may already exist
        print(e)

    print("******* Inserting new row ... *********")
    cursor.execute(f"INSERT INTO EmbryoResults (ImageName, Result,SuggestedValue,Note) VALUES (?,?,?,?)", item.ImageName, item.Result,item.suggested_value,item.note)

    # Insert image url into table from blob storage using parameterized query

    # bulk="pictures/{}".format(item.ImageName)
    # print("bulk",bulk)
    # cursor.execute(f"INSERT INTO EmbryoResults (ImageUrl, ImageName, Result) VALUES ((SELECT BulkColumn FROM OPENROWSET(BULK ?,DATA_SOURCE = 'bolobstorage', SINGLE_BLOB) AS ImageFile), ?,?)", bulk, item.ImageName , item.Result)
    # sql = """
    # INSERT INTO EmbryoResults (ImageUrl)
    # VALUES (
    #     (SELECT * FROM OPENROWSET(
    #         BULK 'pictures/personal.jpeg',
    #         DATA_SOURCE = 'blobstorage',
    #         SINGLE_BLOB
    #         ) AS ImageFile)

    # )
    # """
    # cursor.execute(sql)

    conn.commit()
    return item

### connected with sql db in default way
def get_conn():
    credential = identity.DefaultAzureCredential(exclude_interactive_browser_credential=False)
    token_bytes = credential.get_token("https://database.windows.net/.default").token.encode("UTF-16-LE")
    token_struct = struct.pack(f'<I{len(token_bytes)}s', len(token_bytes), token_bytes)
    SQL_COPT_SS_ACCESS_TOKEN = 1256  # This connection option is defined by microsoft in msodbcsql.h
    print("********* connecting to sql db .... ********* ")
    conn = pyodbc.connect(sql_connection_string, attrs_before={SQL_COPT_SS_ACCESS_TOKEN: token_struct})
    return conn

### connected with sql db using service principal 
def connect_oauth():
    tenant_id = os.environ.get('AZURE_TENANT_ID')
    clientId = os.environ.get('AZURE_CLIENT_ID')
    clientSecret = os.environ.get('AZURE_CLIENT_SECRET')
    server = os.environ.get('SQL_SERVER')
    database = os.environ.get('SQL_DATABASE')
    print(tenant_id,clientId,clientSecret,server,database)
    
    authorityHostUrl = "https://login.microsoftonline.com"
    authority_url = authorityHostUrl + "/" + tenant_id
    context = adal.AuthenticationContext(authority_url,   api_version=None)
    token = context.acquire_token_with_client_credentials("https://database.windows.net/", clientId, clientSecret)
    driver = "{ODBC Driver 18 for SQL Server}"
    #   conn_str = "DRIVER=" + driver + ";server=" + server + ";database="+ database
    conn_str=sql_connection_string
    print("connection string",conn_str)
    SQL_COPT_SS_ACCESS_TOKEN = 1256
    tokenb = bytes(token["accessToken"], "UTF-8")
    exptoken = b''
    for i in tokenb:
        exptoken += bytes({i})
        exptoken += bytes(1)
    tokenstruct = struct.pack("=i", len(exptoken)) + exptoken
    conn = pyodbc.connect(conn_str, attrs_before={SQL_COPT_SS_ACCESS_TOKEN: tokenstruct})
    return conn

# Function to retrieve all blobs (images) from Azure Blob Storage
def list_blobs_in_container():
    blob_service_client = get_blob_service_client()
    container_client = blob_service_client.get_container_client(container_name)
    blob_list = container_client.list_blobs()
    return [blob.name for blob in blob_list]

# Function to retrieve results from Azure SQL Database
def get_all_results():
    print("from get image from sql db")

    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT ImageName, Result, SuggestedValue, Note FROM EmbryoResults")
    rows = cursor.fetchall()
    print("rows",rows)
    conn.close()
    # return {row.ImageName: row.Result for row in results}
    results = {}

    for row in rows:
        results[row.ImageName] = {
            'result': row.Result,
            'suggested_value': row.SuggestedValue,
            'note': row.Note
        }
    print("results",results)

    return results
# API endpoint to list all images and their results
@app.route('/images', methods=['GET'])
def list_images_and_results():
    try:
        # Retrieve all blobs (images) from Azure Blob Storage
        images = list_blobs_in_container()

        # Retrieve all results from Azure SQL Database
        results = get_all_results()

        # Combine the data
        response = []
        # for image in images:
        #     # destination_file = os.path.join(app.config['UPLOAD_FOLDER'], image)

        #     response.append({
        #         "image_name":image,
        #         "image_path": f"http://localhost:5000/images/{image}",
        #         "result": results.get(image, "No result found")
        #     })
        print("results",results)
        for image in images:
            result_data = results.get(image, {
                'result': "No result found",
                'suggested_value': None,
                'note': None
                })
            response.append({
                "image_name": image,
                "image_path": f"http://localhost:5000/images/{image}",
                "result": result_data['result'],
                "suggested_value": result_data['suggested_value'],
                "note": result_data['note']
            })

        return jsonify(response), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/images/<path:filename>')
def get_image(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)

@app.route('/update', methods=['POST'])
def update_embryo():
    data = request.json
    print(data)
    image_name=data['image_name']
    suggested_value = data['suggested_value']
    result=data['result']
    note = data['note']
    try:
        conn = connect_oauth()
        cursor = conn.cursor()

        # Check if the embryo exists
        cursor.execute("SELECT * FROM EmbryoResults WHERE ImageName = ?", (image_name,))
        embryo = cursor.fetchone()

        if not embryo:
            return jsonify({'error': 'Embryo not found'}), 404

    # Update the embryo with new values
        cursor.execute("""
            UPDATE EmbryoResults
            SET Result = ?, SuggestedValue = ?, Note = ?
            WHERE ImageName = ?""", (result, suggested_value, note, image_name)
             
            )

        conn.commit()
        conn.close()

        return jsonify({'message': 'Embryo updated successfully'}), 200

    except Exception as e:
        if conn:
            conn.rollback()
            conn.close()
        return jsonify({'error': str(e)}), 500




    # # Retrieve the embryo from the database based on the image name
    # embryo = Embryo.query.filter_by(image_name=data['image_name']).first()
    # if not embryo:
    #     return jsonify({'error': 'Embryo not found'}), 404

    # Update the note and suggested value

    # # Save the changes to the database
    # db.session.commit()

    # update_embryo=Embryo(ImageName=image_name,Result=result,SuggestedValue=suggested_value,Note=note)
    # saveToSQLDB(update_embryo)

    # return jsonify({'message': 'Embryo updated successfully'}), 200    


###  THIS DOESN'T WORK !! :   API endpoint to retrieve image and result

# Function to retrieve image from Azure Blob Storage
def get_image_from_blob(image_name):
    print("from get image from blob")
    blob_client = get_blob_service_client().get_blob_client(container=container_name, blob=image_name)
    image_data = blob_client.download_blob().readall()
    return image_data

# Function to retrieve result from Azure SQL Database
def get_result_from_db(image_name):
    print("from get image from sql db")

    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT Result FROM EmbryoResults WHERE ImageName = ?", image_name)
    result = cursor.fetchone()[0]  # Assuming result is in the first column
    conn.close()
    return result

@app.route('/image/<image_name>', methods=['GET'])
def get_image_and_result(image_name):
    print("from get_image_and_result method ")
    print(image_name)
    try:
        # Retrieve image from Azure Blob Storage
        image_data = get_image_from_blob(image_name)

        # Retrieve result from Azure SQL Database
        result = get_result_from_db(image_name)

        # Return image and result as JSON response
        response = {
            "image_name": image_name,
            "image_data": image_data,
            "result": result
        }
        return jsonify({'message': 'Image retrieved successfully', 'response':response}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500



# This is are unused APIs

@app.route('/get', methods=['GET'])
def list():
    print("getting data from flask")
    data={'message':'getting data from flask'}
    return jsonify(data)

#for testing
@app.route('/data')
def get_data():
    data = {'message': 'This is data from the Flask API'}
    return jsonify(data)



if __name__ == '__main__':
    app.run(debug=True)
