from flask import Flask, request, jsonify, session, g, redirect, url_for, render_template
from flask_cors import CORS
import os
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timezone
from pymongo import MongoClient, errors as pymongo_errors
from dotenv import load_dotenv
load_dotenv()




app = Flask(__name__)

# Secret key for session
app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret-key')

# Enable CORS for local development
CORS(app, resources={r"/*": {"origins": [
    "http://127.0.0.1:5500",
    "http://localhost:5500",
    "http://127.0.0.1:5001",
    "http://localhost:5001"
]}}, supports_credentials=True)

app.config.update(SESSION_COOKIE_SAMESITE=None, SESSION_COOKIE_SECURE=False)

# MongoDB setup
MONGODB_URI = os.environ.get('MONGODB_URI', "mongodb://localhost:27017/")
MONGODB_DB = os.environ.get('MONGODB_DB', 'aih_db')
MONGODB_TLS_CA_FILE = os.environ.get('MONGODB_TLS_CA_FILE', None)  # Optional for Atlas SSL

def get_mongo_client():
    """Return a MongoClient stored in flask.g with optional SSL for Atlas."""
    if 'mongo' not in g:
        if MONGODB_TLS_CA_FILE:
            g.mongo = MongoClient(MONGODB_URI, tls=True, tlsCAFile=MONGODB_TLS_CA_FILE)
        else:
            g.mongo = MongoClient(MONGODB_URI)
    return g.mongo

@app.teardown_appcontext
def close_db(exception=None):
    """Close MongoDB connection after request"""
    client = g.pop('mongo', None)
    if client:
        try:
            client.close()
        except Exception:
            pass

def init_db():
    """Create unique indexes for users collection"""
    client = get_mongo_client()
    db = client[MONGODB_DB]
    users = db.users
    try:
        users.create_index('username', unique=True)
        users.create_index('email', unique=True)
    except pymongo_errors.OperationFailure:
        pass

# Initialize DB on startup
with app.app_context():
    init_db()

@app.route('/')
def home():
    try:
        return render_template('ruf.html')
    except Exception:
        return "AIH backend running"

# ----------- User Functions -----------
def create_user(username, email, password):
    """Create a new user in the DB"""
    client = get_mongo_client()
    users = client[MONGODB_DB].users
    pw_hash = generate_password_hash(password)
    doc = {
        'username': username or '',
        'email': email,
        'password_hash': pw_hash,
        'created_at': datetime.now(timezone.utc)
    }
    try:
        users.insert_one(doc)
        return True, None
    except pymongo_errors.DuplicateKeyError:
        return False, 'duplicate'
    except Exception as e:
        return False, str(e)

def authenticate_user(identifier, password):
    """Check username/email and password"""
    client = get_mongo_client()
    users = client[MONGODB_DB].users
    row = users.find_one({'username': identifier}) or users.find_one({'email': identifier})
    if not row:
        return False, 'user-not-found'
    if not check_password_hash(row.get('password_hash', ''), password):
        return False, 'invalid-password'
    return True, dict(id=str(row.get('_id')), username=row.get('username'), email=row.get('email'))

# ----------- Routes -----------
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'GET':
        try:
            return render_template('register.html')
        except Exception:
            return jsonify({'ok': True, 'msg': 'POST username,email,password to register'}), 200

    data = request.get_json(silent=True) or request.form
    username = (data.get('username') or '').strip()
    email = (data.get('email') or '').strip().lower()
    password = data.get('password') or ''

    if not email or not password:
        return jsonify({'ok': False, 'error': 'email and password are required'}), 400

    ok, err = create_user(username, email, password)
    if not ok:
        if err == 'duplicate':
            return redirect(url_for('login'))
        return jsonify({'ok': False, 'error': 'db_error', 'detail': err}), 500

    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        try:
            return render_template('login.html')
        except Exception:
            return jsonify({'ok': True, 'msg': 'POST identifier (username or email), password to login'}), 200

    data = request.get_json(silent=True) or request.form
    identifier = (data.get('username') or data.get('email') or data.get('identifier') or '').strip()
    password = data.get('password') or ''

    if not identifier or not password:
        return jsonify({'ok': False, 'error': 'identifier and password required'}), 400

    ok, payload_or_err = authenticate_user(identifier, password)
    if not ok:
        return jsonify({'ok': False, 'error': 'invalid_credentials', 'detail': payload_or_err}), 401

    payload = payload_or_err
    session.clear()
    session['user_id'] = payload['id']
    session['username'] = payload.get('username') or payload.get('email')

    return jsonify({'ok': True, 'username': session['username']}), 200

@app.route('/logout', methods=['POST'])
def logout():
    session.clear()
    return jsonify({'ok': True}), 200

# ----------- Symptom Analysis -----------

symptom_data = {
 "Fever": {
 "observation": "You might have an infection or flu.",
 "recommendation": "Paracetamol for fever.",
 "food": {
 "English": "Stay hydrated with clear soups and water.",
 "Hindi": "सूप और पानी पीकर हाइड्रेट रहें।"
 },
 "remedies": [
 "Drink plenty of fluids, particularly water.",
 "Avoid alcohol, tea, and coffee.",
 "Sponge exposed skin with tepid water.",
 "Stand in front of a fan to stay cool."
 ]
 },
 "Cough": {
 "observation": "You might have a respiratory issue.",
 "recommendation": "Cough syrups like Benadryl or lozenges for sore throat.",
 "food": {
 "English": "Warm teas with honey and ginger, soft foods like mashed potatoes.",
 "Hindi": "शहद और अदरक के साथ गर्म चाय, और नरम भोजन जैसे मसला हुआ आलू।"
 },
 },
 "Sore Throat": {
 "observation": "You might have a respiratory issue.",
 "recommendation": "Lozenges for sore throat relief.",
 "food": {
 "English": "Drink warm fluids like soup or herbal tea.",
 "Hindi": "गर्म तरल पदार्थ जैसे सूप या हर्बल चाय पीएं।"
 },
 "remedies": [
 "Gargle with warm salt water.",
 "Drink warm honey-lemon tea.",
 "Use a throat lozenge to soothe irritation.",
 "Avoid speaking loudly to rest your throat."
 ]
 },
 "Sinus": {
 "observation": "You might have sinusitis.",
 "recommendation": "Steam inhalation and nasal decongestants. Decongestants, Antihistamines, Nasal corticosteroids",
 "food": {
 "English": "Spicy foods (if tolerated) and warm broths.",
 "Hindi": "मसालेदार खाना (यदि सहन हो) और गर्म सूप।"
 },
 },
 "Headache": {
 "observation": "You might be experiencing stress, migraine, or dehydration.",
 "recommendation": "Pain relievers like ibuprofen or acetaminophen. Tension headaches, Migraines",
 "food": {
 "English": "Drink plenty of water, include magnesium-rich foods like spinach.",
 "Hindi": "ज्यादा पानी पिएं, और पालक जैसे मैग्नीशियम युक्त भोजन लें।"
 },
 },
 "Vomiting": {
 "observation": "You might have a stomach infection or food poisoning.",
 "recommendation": "ORS (Oral Rehydration Solution) and antiemetics like ondansetron.",
 "food": {
 "English": "Eat bland foods like rice and bananas.",
 "Hindi": "सादा भोजन जैसे चावल और केले खाएं।"
 },
 },
 "Loose Motion": {
 "observation": "You might have digestive issues or an infection.",
 "recommendation": "ORS and probiotics like Enterogermina.",
 "food": {
 "English": "Consume curd, bananas, and boiled potatoes.",
 "Hindi": "दही, केले, और उबले आलू खाएं।"
 },
 },
 "High Blood Pressure": {
 "observation": "You might have hypertension. Monitor regularly.",
 "recommendation": "Consult a doctor for antihypertensive medications.",
 "food": {
 "English": "Reduce salt intake, eat bananas and leafy greens.",
 "Hindi": "नमक का सेवन कम करें, केले और पत्तेदार सब्जियां खाएं।"
 },
 },
 "Low Blood Pressure": {
 "observation": "You might have hypotension. Stay hydrated and consult a doctor.",
 "recommendation": "Electrolyte drinks and proper rest.",
 "food": {
 "English": "Include salty snacks and foods rich in vitamin B12.",
 "Hindi": "नमकीन स्नैक्स और विटामिन बी12 युक्त खाना खाएं।"
 },
 },
 "Diabetes": {
 "observation": "You might need to manage your blood sugar levels.",
 "recommendation": "Consult a doctor for antidiabetic medications.",
 "food": {
 "English": "Focus on low-GI foods like oatmeal, nuts, and green vegetables.",
 "Hindi": "लो-जीआई भोजन जैसे ओट्स, मेवे, और हरी सब्जियां खाएं।"
 },
 },
 "Chest pain": {
 "observation": "Chest pain could indicate a heart issue. Seek immediate medical attention.",
 "recommendation": "Emergency care required. Avoid self-medication.",
 "food": {
 "English": "Avoid heavy meals and consume light, easily digestible foods.",
 "Hindi": "भारी भोजन से बचें और हल्का, आसानी से पचने वाला भोजन खाएं।"
 },
 },
 "Shortness of Breath": {
 "observation": "Shortness of breath might indicate respiratory or cardiac problems.",
 "recommendation": "Emergency care required. Avoid self-medication.",
 "food": {
 "English": "Avoid allergens and stay hydrated.",
 "Hindi": "एलर्जी से बचें और हाइड्रेट रहें।"
 },
 },
 "Fatigue": {
 "observation": "Fatigue could be due to anemia, stress, or an underlying condition.",
 "recommendation": "Iron supplements for anemia and balanced nutrition.",
 "food": {
 "English": "Iron-rich foods like spinach, lentils, and beetroot.",
 "Hindi": "आयरन युक्त खाना जैसे पालक, मसूर की दाल, और चुकंदर।"
 },
 },
 "Nausea": {
 "observation": "Nausea might indicate gastrointestinal or hormonal issues.",
 "recommendation": "Antiemetics like ondansetron.",
 "food": {
 "English": "Eat small portions of crackers, dry toast, or ginger tea.",
 "Hindi": "थोड़ा-थोड़ा बिस्किट, सूखी टोस्ट, या अदरक की चाय लें।"
 },
 },
 "Joint Pain": {
 "observation": "Joint pain could indicate arthritis or an autoimmune condition.",
 "recommendation": "Pain relievers like ibuprofen and anti-inflammatory gels.",
 "food": {
 "English": "Add turmeric, fish oil, and cherries to your diet.",
 "Hindi": "अपने आहार में हल्दी, मछली का तेल, और चेरी शामिल करें।"
 },
 },
 "Back Pain": {
 "observation": "Back pain might be due to posture, injury, or a spinal issue.",
 "recommendation": "Pain relievers and hot or cold compresses.",
 "food": {
 "English": "Consume foods rich in calcium and vitamin D like milk and almonds.",
 "Hindi": "दूध और बादाम जैसे कैल्शियम और विटामिन डी युक्त खाना खाएं।"
 },
 },
 "Dizziness": {
 "observation": "Dizziness might be due to low blood pressure, dehydration, or vertigo.",
 "recommendation": "Hydration and medications like betahistine for vertigo.",
 "food": {
 "English": "Drink plenty of fluids and include salty snacks.",
 "Hindi": "ज्यादा तरल पदार्थ पिएं और नमकीन स्नैक्स खाएं।"
 },
 },
 "Rash": {
 "observation": "A rash might indicate an allergic reaction or skin condition.",
 "recommendation": "Antihistamines like cetirizine and topical creams.",
 "food": {
 "English": "Consume foods rich in antioxidants like berries and green tea.",
 "Hindi": "एंटीऑक्सिडेंट से भरपूर भोजन जैसे बेरीज और ग्रीन टी पिएं।"
 },
 },
 "Malaria": {
 "observation": "You might have malaria, which is caused by a mosquito bite.",
 "recommendation": "Drink plenty of fluids and rest.",
 "food": {
 "English": "Consume coconut water, fresh fruits, and herbal teas.",
 "Hindi": "नारियल पानी, ताजे फल, और हर्बल चाय पिएं।"
 },
 },
 "Dengue": {
 "observation": "You might have dengue, which is transmitted by mosquitoes.",
 "recommendation": "Hydrate with ORS and stay in a cool environment.",
 "food": {
 "English": "Consume papaya leaves juice and pomegranate.",
 "Hindi": "पपीते के पत्तों का रस और अनार खाएं।"
 },
 },
 "Typhoid": {
 "observation": "You might have typhoid, an infection caused by bacteria.",
 "recommendation": "Stay hydrated and consume bland foods.",
 "food": {
 "English": "Eat boiled vegetables, rice, and bananas.",
 "Hindi": "उबली हुई सब्जियां, चावल, और केले खाएं।"
 },
 },
 "Kidney Stone Pain": {
 "observation": "You might be experiencing kidney stone pain.",
 "recommendation": "Drink plenty of water and try warm compresses.",
 "food": {
 "English": "Drink lemon juice and water, avoid high-oxalate foods.",
 "Hindi": "नींबू का रस और पानी पिएं, उच्च ऑक्सालेट वाले भोजन से बचें।"
 },
 },
 "Appendix": {
 "observation": "You might have appendicitis, which requires immediate medical attention.",
 "recommendation": "Seek emergency medical care.",
 "food": {
 "English": "Avoid solid foods until treated. Focus on liquids.",
 "Hindi": "इलाज होने तक ठोस भोजन से बचें। तरल पदार्थ लें।"
 },
 }
 }


@app.route('/analyze', methods=['POST'])
def analyze():
    data = request.get_json(silent=True) or {}
    symptoms = data.get('symptoms', []) or []
    observations, recommendations, food_recommendations = [], [], []

    for symptom in symptoms:
        if symptom in symptom_data:
            observations.append(symptom_data[symptom]["observation"])
            recommendations.append(symptom_data[symptom]["recommendation"])
            food_recommendations.append(symptom_data[symptom]["food"])

    return jsonify({
        "observations": observations,
        "recommendations": recommendations,
        "food_recommendations": food_recommendations,
    }), 200

@app.route('/symptoms', methods=['GET'])
def symptoms():
    return jsonify(list(symptom_data.keys()))

@app.route('/me', methods=['GET'])
def me():
    username = session.get('username')
    if username:
        return jsonify({'ok': True, 'username': username}), 200
    return jsonify({'ok': False, 'username': None}), 200

# ----------- Run App -----------
if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5001, debug=True)
