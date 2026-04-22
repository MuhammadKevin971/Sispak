from flask import Flask, render_template, request, jsonify
import numpy as np

app = Flask(__name__)

# ============================================================
# 1. FUNGSI KEANGGOTAAN (Membership Functions)
# ============================================================
def trimf(x, a, b, c):
    if x <= a or x >= c: return 0.0
    elif a < x <= b: return (x - a) / (b - a)
    else: return (c - x) / (c - b)

def trapmf(x, a, b, c, d):
    if x <= a or x > d: return 0.0  # FIXED: Changed x >= d to x > d
    elif a < x <= b: return (x - a) / (b - a)
    elif b < x <= c: return 1.0
    else: return (d - x) / (d - c)

# ============================================================
# 2. FUZZIFIKASI INPUT
# ============================================================
def fuzzify_kerusakan_daun(nilai):
    rendah = trapmf(nilai, 0, 0, 25, 50)
    sedang = trimf(nilai, 25, 50, 75)
    tinggi = trapmf(nilai, 50, 75, 100, 101)  # FIXED: Changed boundaries for better coverage
    return {"rendah": rendah, "sedang": sedang, "tinggi": tinggi}

def fuzzify_pola_kerusakan(nilai):
    merata = trapmf(nilai, 0, 0, 25, 50)
    campuran = trimf(nilai, 25, 50, 75)
    spot = trapmf(nilai, 50, 75, 100, 101)  # FIXED: Improved boundaries for better coverage
    return {"merata": merata, "campuran": campuran, "spot": spot}

def fuzzify_kerusakan_batang(nilai):
    layu = trapmf(nilai, 0, 0, 25, 50)
    lubang = trimf(nilai, 25, 50, 75)
    potong = trapmf(nilai, 50, 75, 100, 101)  # FIXED: Improved boundaries for better coverage
    return {"layu": layu, "lubang": lubang, "potong": potong}

def fuzzify_waktu_serangan(nilai):
    siang = trapmf(nilai, 0, 0, 25, 50)
    campuran = trimf(nilai, 25, 50, 75)
    malam = trapmf(nilai, 50, 75, 100, 101)  # FIXED: Improved boundaries for better coverage
    return {"siang": siang, "campuran": campuran, "malam": malam}

# ============================================================
# 3. RULE BASE
# ============================================================
def apply_rules(daun, pola, batang, waktu):
    rules = []
    
    # WERENG RULES
    rules.append(("wereng", "tinggi", min(daun["tinggi"], pola["merata"], batang["layu"], waktu["siang"])))
    rules.append(("wereng", "tinggi", min(daun["tinggi"], pola["merata"], batang["layu"], waktu["campuran"])))
    rules.append(("wereng", "tinggi", min(daun["tinggi"], pola["merata"], batang["layu"])))
    
    # More responsive rules for wereng
    rules.append(("wereng", "tinggi", min(daun["tinggi"], pola["merata"])))
    rules.append(("wereng", "tinggi", min(daun["tinggi"], batang["layu"])))
    
    rules.append(("wereng", "sedang", min(daun["sedang"], pola["merata"], batang["layu"])))
    rules.append(("wereng", "sedang", min(daun["tinggi"], pola["campuran"], batang["layu"])))
    rules.append(("wereng", "sedang", min(pola["merata"], batang["layu"], waktu["siang"])))
    rules.append(("wereng", "sedang", min(daun["sedang"], waktu["siang"], pola["merata"])))
    rules.append(("wereng", "sedang", min(daun["sedang"], pola["campuran"], waktu["siang"])))
    
    # More responsive rules for wereng (general)
    rules.append(("wereng", "sedang", min(daun["sedang"], pola["merata"])))
    rules.append(("wereng", "sedang", min(daun["sedang"], batang["layu"])))
    rules.append(("wereng", "sedang", min(pola["merata"], batang["layu"])))
    
    rules.append(("wereng", "rendah", min(daun["rendah"], pola["merata"], batang["layu"])))
    rules.append(("wereng", "rendah", min(daun["rendah"], pola["merata"])))
    rules.append(("wereng", "rendah", min(daun["rendah"], batang["layu"])))
    
    # TIKUS RULES
    rules.append(("tikus", "tinggi", min(batang["potong"], pola["spot"], waktu["malam"])))
    rules.append(("tikus", "tinggi", min(batang["potong"], pola["spot"])))
    rules.append(("tikus", "tinggi", min(daun["rendah"], batang["potong"], waktu["malam"])))
    rules.append(("tikus", "tinggi", min(daun["rendah"], batang["potong"], pola["spot"])))
    
    # More responsive rules for tikus
    rules.append(("tikus", "tinggi", min(batang["potong"], pola["spot"])))
    rules.append(("tikus", "tinggi", min(batang["potong"], waktu["malam"])))
    
    rules.append(("tikus", "sedang", min(batang["lubang"], pola["spot"], waktu["malam"])))
    rules.append(("tikus", "sedang", min(daun["rendah"], pola["spot"], batang["potong"])))
    rules.append(("tikus", "sedang", min(batang["lubang"], pola["spot"])))
    rules.append(("tikus", "sedang", min(pola["spot"], waktu["malam"], daun["sedang"])))
    rules.append(("tikus", "sedang", min(batang["lubang"], waktu["campuran"], pola["spot"])))
    rules.append(("tikus", "sedang", min(daun["sedang"], pola["spot"], waktu["malam"])))
    
    # More responsive rules for tikus (general)
    rules.append(("tikus", "sedang", min(batang["lubang"], pola["spot"])))
    rules.append(("tikus", "sedang", min(pola["spot"], waktu["malam"])))
    rules.append(("tikus", "sedang", min(batang["lubang"], waktu["campuran"])))
    
    rules.append(("tikus", "rendah", min(batang["lubang"], waktu["campuran"])))
    rules.append(("tikus", "rendah", min(daun["rendah"], pola["campuran"], waktu["malam"])))
    rules.append(("tikus", "rendah", min(batang["lubang"], daun["rendah"])))
    
    return rules

# ============================================================
# 4. DEFUZZIFIKASI
# ============================================================
def defuzzify(rules, hama):
    x = np.linspace(0, 100, 1000)
    aggregated = np.zeros_like(x)
    for (target_hama, level, alpha) in rules:
        if target_hama != hama or alpha == 0:
            continue
        if level == "rendah":
            mf = np.array([trapmf(xi, 0, 0, 20, 40) for xi in x])
        elif level == "sedang":
            mf = np.array([trimf(xi, 20, 50, 80) for xi in x])
        else:
            mf = np.array([trapmf(xi, 60, 80, 100, 100) for xi in x])
        clipped = np.minimum(alpha, mf)
        aggregated = np.maximum(aggregated, clipped)
    if np.sum(aggregated) == 0:
        return 0.0
    return round(np.sum(x * aggregated) / np.sum(aggregated), 2)

# ============================================================
# 5. DIAGNOSIS FUNCTION
# ============================================================
def diagnosa(kerusakan_daun, pola_kerusakan, kerusakan_batang, waktu_serangan):
    daun = fuzzify_kerusakan_daun(kerusakan_daun)
    pola = fuzzify_pola_kerusakan(pola_kerusakan)
    batang = fuzzify_kerusakan_batang(kerusakan_batang)
    waktu = fuzzify_waktu_serangan(waktu_serangan)
    rules = apply_rules(daun, pola, batang, waktu)
    skor_wereng = defuzzify(rules, "wereng")
    skor_tikus = defuzzify(rules, "tikus")
    total = skor_wereng + skor_tikus
    
    # Handle case ketika kedua skor 0 (tidak ada diagnosis yang jelas)
    if total == 0:
        pct_wereng = 0.0
        pct_tikus = 0.0
        diagnosis = "Tidak dapat ditentukan"
        confidence = 0.0
        penanganan = [
            "Lakukan pengamatan lebih lanjut pada tanaman",
            "Periksa kondisi tanaman secara menyeluruh",
            "Konsultasikan dengan ahli pertanian jika gejala berlanjut"
        ]
    else:
        pct_wereng = round((skor_wereng / total) * 100, 1)
        pct_tikus = round((skor_tikus / total) * 100, 1)
        if pct_wereng >= pct_tikus:
            diagnosis = "Wereng (Planthopper)"
            confidence = pct_wereng
            penanganan = [
                "Semprotkan insektisida (malathion, imidakloprid)",
                "Gunakan perangkap kuning untuk monitoring",
                "Tanam varietas tahan wereng"
            ]
        else:
            diagnosis = "Tikus (Rat)"
            confidence = pct_tikus
            penanganan = [
                "Semprotkan rodentisida (phosphine, coumatetralyl)",
                "Pasang perangkap tikus",
                "Kontrol gulma dan sisa panen",
                "Karantina area yang terjangkit"
            ]
    return {
        "diagnosis": diagnosis, "confidence": confidence,
        "skor_wereng": skor_wereng, "skor_tikus": skor_tikus,
        "pct_wereng": pct_wereng, "pct_tikus": pct_tikus,
        "penanganan": penanganan,
        "input": {"kerusakan_daun": kerusakan_daun, "pola_kerusakan": pola_kerusakan, 
                  "kerusakan_batang": kerusakan_batang, "waktu_serangan": waktu_serangan}
    }

# ============================================================
# FLASK ROUTES
# ============================================================

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/diagnose', methods=['POST'])
def api_diagnose():
    try:
        data = request.json
        
        # Validasi input
        if not all(k in data for k in ['kerusakan_daun', 'pola_kerusakan', 'kerusakan_batang', 'waktu_serangan']):
            return jsonify({"error": "Missing input data"}), 400
        
        kerusakan_daun = float(data['kerusakan_daun'])
        pola_kerusakan = float(data['pola_kerusakan'])
        kerusakan_batang = float(data['kerusakan_batang'])
        waktu_serangan = float(data['waktu_serangan'])
        
        # Validasi range (0-100)
        for val in [kerusakan_daun, pola_kerusakan, kerusakan_batang, waktu_serangan]:
            if not 0 <= val <= 100:
                return jsonify({"error": "Input value must be between 0-100"}), 400
        
        hasil = diagnosa(kerusakan_daun, pola_kerusakan, kerusakan_batang, waktu_serangan)
        return jsonify(hasil)
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/test-cases', methods=['GET'])
def test_cases():
    """Endpoint untuk test cases predefinisi"""
    test_data = [
        {
            "name": "Wereng Kuat",
            "description": "Ciri kuat wereng: daun rusak, pola merata, layu, siang",
            "data": {"kerusakan_daun": 80, "pola_kerusakan": 10, "kerusakan_batang": 15, "waktu_serangan": 10}
        },
        {
            "name": "Tikus Kuat",
            "description": "Ciri kuat tikus: daun sedikit, pola spot, terpotong, malam",
            "data": {"kerusakan_daun": 15, "pola_kerusakan": 90, "kerusakan_batang": 90, "waktu_serangan": 90}
        },
        {
            "name": "Ambigus",
            "description": "Gejala tidak jelas, semua nilai sedang",
            "data": {"kerusakan_daun": 50, "pola_kerusakan": 50, "kerusakan_batang": 50, "waktu_serangan": 50}
        },
        {
            "name": "Lubang + Malam",
            "description": "Batang lubang + malam (condong tikus)",
            "data": {"kerusakan_daun": 30, "pola_kerusakan": 90, "kerusakan_batang": 55, "waktu_serangan": 90}
        }
    ]
    
    results = []
    for test in test_data:
        result = diagnosa(**test['data'])
        result['test_name'] = test['name']
        result['test_description'] = test['description']
        results.append(result)
    
    return jsonify(results)

if __name__ == '__main__':
    app.run(debug=True, port=5000)
