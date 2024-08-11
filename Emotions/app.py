from flask import Flask, request, jsonify, render_template
import boto3
import base64
import uuid
from PIL import Image
import io

app = Flask(__name__)

# Initialize Rekognition client
rekognition_client = boto3.client('rekognition')

# Emotion and gender counts
emotion_counts = {
    "happy": 0,
    "sad": 0,
    "angry": 0,
    "surprised": 0,
    "calm": 0,
    "confused": 0,
    "fearful": 0,
    "disgusted": 0
}

gender_counts = {
    "Male": 0,
    "Female": 0
}

# Load logo
logo_path = 'logo.png'  # Ensure this path is correct
logo = Image.open(logo_path).convert("RGBA")

def add_logo_to_image(image):
    img_width, img_height = image.size
    logo_width, logo_height = logo.size

    # Position the logo at the top-right corner
    position = (img_width - logo_width, 0)
    
    # Create a new image with RGBA mode for transparency
    img_with_logo = Image.new('RGBA', image.size)
    img_with_logo.paste(image, (0, 0))
    img_with_logo.paste(logo, position, logo)  # Use the logo as a mask for transparency

    return img_with_logo

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/capture', methods=['POST'])
def capture():
    global emotion_counts, gender_counts
    
    # Get the image from the request
    image_data = request.form.get('image')
    image_bytes = base64.b64decode(image_data.split(',')[1])
    
    # Convert to PIL Image
    img = Image.open(io.BytesIO(image_bytes)).convert("RGBA")
    
    # Call Rekognition
    response = rekognition_client.detect_faces(
        Image={'Bytes': image_bytes},
        Attributes=['ALL']
    )
    
    # Analyze the emotions and gender
    detected_emotions = {emotion: 0 for emotion in emotion_counts}
    detected_genders = {"Male": 0, "Female": 0}
    
    for faceDetail in response['FaceDetails']:
        emotions = faceDetail['Emotions']
        # Find the most confident emotion for this face
        max_emotion = max(emotions, key=lambda e: e['Confidence'])
        emotion_name = max_emotion['Type'].lower()
        if emotion_name in detected_emotions:
            detected_emotions[emotion_name] += 1
        
        # Detect gender
        gender = faceDetail['Gender']['Value']
        if gender in detected_genders:
            detected_genders[gender] += 1
    
    # Update global counts
    for emotion in detected_emotions:
        if detected_emotions[emotion] > 0:
            emotion_counts[emotion] += detected_emotions[emotion]
    
    for gender in detected_genders:
        if detected_genders[gender] > 0:
            gender_counts[gender] += detected_genders[gender]
    
    # Overlay the logo on the image
    img_with_logo = add_logo_to_image(img)
    
    # Save the captured image with a unique identifier and emotion label
    unique_id = uuid.uuid4().hex
    image_label = max(detected_emotions, key=detected_emotions.get)
    image_filename = f"captured_{unique_id}_{image_label}.png"
    img_with_logo.save(image_filename)
    
    # Return the updated counts
    return jsonify({
        "emotions": emotion_counts,
        "genders": gender_counts
    })

@app.route('/counts', methods=['GET'])
def get_counts():
    return jsonify({
        "emotions": emotion_counts,
        "genders": gender_counts
    })

if __name__ == '__main__':
    app.run(debug=True, port=6699)
