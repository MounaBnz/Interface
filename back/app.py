from flask import Flask, request, jsonify
from werkzeug.utils import secure_filename
from flask_cors import CORS
import tensorflow as tf
import numpy as np
import cv2
import os
import io
from keras.models import load_model
from keras.layers import BatchNormalization

app = Flask(__name__)
CORS(app, resources={r"/analyse-embryon": {"origins": "http://localhost:4200"}})

# Use verified model path
model_path = r'C:\Users\mouna\interface_PFA_backend\Images_checkpoint.h5'
model = None

def load_model_function():
    global model 
    try:
        print(f"Checking if model path exists: {model_path}")
        if os.path.exists(model_path):
            print(f"Model path exists: {model_path}")
            custom_objects = {'BatchNormalization': BatchNormalization}
            model = load_model(model_path, custom_objects=custom_objects)
            print("Model loaded successfully")
            if model:
                print("Model structure: ")
                model.summary()  # This will print the model structure if successfully loaded
        else:
            print(f"Model path does not exist: {model_path}")
    except Exception as e:
        print(f"Error loading model: {e}")

# Load the model when the server starts
print("Starting the model loading process...")
load_model_function()
print("Model loading process ended.")

# Define allowed file extensions
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/analyse-embryon', methods=['POST'])
def analyze():
    if model is None:
        print("Model not loaded")
        return jsonify({'error': 'Model not loaded'})

    if 'file' not in request.files:
        print("No file part in the request")
        return jsonify({'error': 'No file part'})
    file = request.files['file']
    if file.filename == '':
        print("No selected file")
        return jsonify({'error': 'No selected file'})
    if file and allowed_file(file.filename):
        try:
            print("Processing file: ", file.filename)
            # Read the image file into memory
            in_memory_file = io.BytesIO()
            file.save(in_memory_file)
            in_memory_file.seek(0)

            # Convert the image to a numpy array
            file_bytes = np.frombuffer(in_memory_file.read(), np.uint8)
            image = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)

            if image is None:
                print("Error reading image")
                return jsonify({'error': 'Error reading image'})

            # Apply CLAHE using OpenCV
            print("Applying CLAHE...")
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
            lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
            lab_planes = list(cv2.split(lab))
            lab_planes[0] = clahe.apply(lab_planes[0])
            lab = cv2.merge(lab_planes)
            enhanced_image = cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)

            # Resize and normalize the image
            print("Resizing and normalizing the image...")
            resized_image = cv2.resize(enhanced_image, (299, 299))
            normalized_image = resized_image.astype(np.float32) / 255.0
            normalized_image = np.expand_dims(normalized_image, axis=0)  # Add batch dimension

            print("Image preprocessed successfully")

            # Make predictions
            print("Making predictions...")
            predictions = model.predict(normalized_image)
            predicted_class = np.argmax(predictions, axis=1)[0]
            score = float(np.max(predictions))

            print(f"Predictions: {predictions}")
            print(f"Predicted class: {predicted_class}")
            print(f"Score: {score}")

            # Map predicted class to class name
            class_mapping = {1: 'GOOD', 2: 'AVERAGE', 3: 'BAD'}
            class_name = class_mapping.get(predicted_class, 'UNKNOWN')

            response = {
                'class': class_name,
                'score': score
            }
            return jsonify(response)
        except Exception as e:
            print(f"Error during analysis: {e}")
            return jsonify({'error': str(e)})
    else:
        print("File not allowed")
        return jsonify({'error': 'File not allowed'})

if __name__ == '__main__':
    print("Starting Flask app...")
    app.run(debug=True)
    print("Flask app ended.")
