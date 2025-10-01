from flask import Flask, render_template, request, jsonify

app = Flask(__name__)

@app.route('/')
def home():
    return render_template('.html') 

@app.route('/analyze', methods=['POST'])
def analyze():
    symptoms = request.json.get('symptoms', [])
    observations =  []
    doctor_recommendation = []
    recommendations = []
    food_recommendations = []
    home_remedies = []

symptom_data={
        "Fever": {
            "observation": "You might have an infection or flu.",

            "recommendation": "Paracetamol for fever.",
            "food": {
                "English": "Stay hydrated with clear soups and water.",
                "Hindi": "सूप और पानी पीकर हाइड्रेट रहें।"
            },
            "remedies": [
                "Drink plenty of fluids, particularly water."
                "Avoid alcohol, tea, and coffee."
                "Sponge exposed skin with tepid water."
                "Stand in front of a fan to stay cool."
            ]
        },


        "cough":{
             "observation":""
        }
}

@app.route('/symptoms', methods=['GET'])
def symptoms():
    symptom_list = [
        "Fever", "Cough", "Sore Throat", "Sinus", "Headache", "Vomiting", "Loose Motion",
        "High Blood Pressure", "Low Blood Pressure", "Diabetes", "Chest Pain",
        "Shortness of Breath", "Fatigue", "Nausea", "Joint Pain", "Back Pain",
        "Dizziness", "Rash", "Malaria", "Dengue", "Typhoid", "Kidney Stone Pain", "Appendix"
    ]
    return jsonify(symptom_list)

if __name__ == "__main__":
    app.run(debug=True)
