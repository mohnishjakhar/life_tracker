from datetime import datetime, timezone, date
from app import db


class ExerciseTarget(db.Model):
    __tablename__ = "exercise_targets"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True)
    target_days_per_week = db.Column(db.Integer, nullable=False, default=4)
    target_minutes_per_week = db.Column(db.Integer, nullable=False, default=150)
    target_calories_per_week = db.Column(db.Integer, nullable=True, default=1500)
    notes = db.Column(db.String(255), nullable=True)
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    def __repr__(self):
        return f"<ExerciseTarget User {self.user_id}: {self.target_days_per_week} days/wk>"


class ExerciseLog(db.Model):
    __tablename__ = "exercise_logs"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    date = db.Column(db.Date, nullable=False, default=date.today, index=True)
    workout_type = db.Column(db.String(60), nullable=False)  # Running, Gym/Strength, Yoga, HIIT, Cycling, Swimming, Walking, Sports, Other
    duration_minutes = db.Column(db.Integer, nullable=False, default=30)
    calories_burned = db.Column(db.Integer, nullable=True, default=0)
    intensity = db.Column(db.String(20), nullable=False, default="Moderate")  # Low, Moderate, High, Extreme
    exercises_details = db.Column(db.Text, nullable=True)  # Detailed exercises, sets, reps, distance
    notes = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    def __repr__(self):
        return f"<ExerciseLog {self.workout_type} ({self.duration_minutes}m) on {self.date}>"


class BodyMeasurement(db.Model):
    __tablename__ = "body_measurements"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    date = db.Column(db.Date, nullable=False, default=date.today, index=True)
    weight_kg = db.Column(db.Float, nullable=True)
    height_cm = db.Column(db.Float, nullable=True)
    bmi = db.Column(db.Float, nullable=True)
    blood_pressure_systolic = db.Column(db.Integer, nullable=True)
    blood_pressure_diastolic = db.Column(db.Integer, nullable=True)
    resting_heart_rate = db.Column(db.Integer, nullable=True)  # bpm
    vision_right = db.Column(db.String(40), nullable=True)  # e.g., "-1.50" or "6/6"
    vision_left = db.Column(db.String(40), nullable=True)   # e.g., "-1.75" or "6/6"
    waist_cm = db.Column(db.Float, nullable=True)
    body_fat_pct = db.Column(db.Float, nullable=True)
    notes = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    def calculate_bmi(self):
        if self.weight_kg and self.height_cm and self.height_cm > 0:
            height_m = self.height_cm / 100.0
            self.bmi = round(self.weight_kg / (height_m * height_m), 1)
        return self.bmi

    @property
    def bmi_category(self):
        if not self.bmi:
            return {"label": "N/A", "badge": "secondary"}
        if self.bmi < 18.5:
            return {"label": "Underweight", "badge": "info"}
        elif self.bmi < 25.0:
            return {"label": "Normal weight", "badge": "success"}
        elif self.bmi < 30.0:
            return {"label": "Overweight", "badge": "warning"}
        else:
            return {"label": "Obese", "badge": "danger"}

    def __repr__(self):
        return f"<BodyMeasurement User {self.user_id} on {self.date}: {self.weight_kg}kg>"


class MedicalReport(db.Model):
    __tablename__ = "medical_reports"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    test_date = db.Column(db.Date, nullable=False, default=date.today, index=True)
    title = db.Column(db.String(150), nullable=False)
    lab_name = db.Column(db.String(120), nullable=True)
    doctor_name = db.Column(db.String(100), nullable=True)
    pdf_filename = db.Column(db.String(255), nullable=True)
    original_filename = db.Column(db.String(255), nullable=True)
    summary_notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    # --- Complete Blood Count (CBC) ---
    hemoglobin = db.Column(db.Float, nullable=True)       # g/dL (ref: 13.0 - 17.5 M, 12.0 - 15.5 F)
    wbc_count = db.Column(db.Float, nullable=True)        # /mcL (ref: 4000 - 11000)
    rbc_count = db.Column(db.Float, nullable=True)        # mil/mcL (ref: 4.5 - 5.9)
    platelet_count = db.Column(db.Float, nullable=True)   # thousand/mcL (ref: 150 - 450)
    hematocrit_pct = db.Column(db.Float, nullable=True)   # % (ref: 38.8 - 50.0)

    # --- Lipid Profile ---
    total_cholesterol = db.Column(db.Float, nullable=True)  # mg/dL (< 200)
    hdl_cholesterol = db.Column(db.Float, nullable=True)    # mg/dL (> 40)
    ldl_cholesterol = db.Column(db.Float, nullable=True)    # mg/dL (< 100)
    triglycerides = db.Column(db.Float, nullable=True)      # mg/dL (< 150)
    vldl = db.Column(db.Float, nullable=True)               # mg/dL (2 - 30)

    # --- Vitamins & Minerals ---
    vitamin_d = db.Column(db.Float, nullable=True)        # ng/mL (30 - 100)
    vitamin_b12 = db.Column(db.Float, nullable=True)      # pg/mL (200 - 900)
    iron_ferritin = db.Column(db.Float, nullable=True)    # ng/mL (20 - 250)
    calcium = db.Column(db.Float, nullable=True)          # mg/dL (8.5 - 10.2)

    # --- Basic Metabolic & Organs ---
    blood_sugar_fasting = db.Column(db.Float, nullable=True)  # mg/dL (70 - 99)
    hba1c = db.Column(db.Float, nullable=True)                # % (< 5.7)
    serum_creatinine = db.Column(db.Float, nullable=True)     # mg/dL (0.7 - 1.3)
    uric_acid = db.Column(db.Float, nullable=True)            # mg/dL (3.5 - 7.2)
    sgpt_alt = db.Column(db.Float, nullable=True)             # U/L (7 - 56)
    sgot_ast = db.Column(db.Float, nullable=True)             # U/L (10 - 40)
    tsh = db.Column(db.Float, nullable=True)                  # uIU/mL (0.4 - 4.0)

    other_findings = db.Column(db.Text, nullable=True)

    def get_parameter_analysis(self):
        """Returns structured lab metrics with standard reference ranges and evaluated status."""
        standards = [
            # Panel, Name, Value, Unit, Min, Max, Standard note
            ("CBC", "Hemoglobin", self.hemoglobin, "g/dL", 12.0, 17.5, "12.0 - 17.5 g/dL"),
            ("CBC", "WBC Count", self.wbc_count, "/mcL", 4000, 11000, "4,000 - 11,000 /mcL"),
            ("CBC", "RBC Count", self.rbc_count, "mil/mcL", 4.5, 5.9, "4.5 - 5.9 mil/mcL"),
            ("CBC", "Platelets", self.platelet_count, "k/mcL", 150, 450, "150 - 450 k/mcL"),
            ("CBC", "Hematocrit", self.hematocrit_pct, "%", 38.5, 50.0, "38.5 - 50.0 %"),

            ("Lipid Profile", "Total Cholesterol", self.total_cholesterol, "mg/dL", None, 200.0, "< 200 mg/dL"),
            ("Lipid Profile", "HDL (Good) Cholesterol", self.hdl_cholesterol, "mg/dL", 40.0, None, "> 40 mg/dL"),
            ("Lipid Profile", "LDL (Bad) Cholesterol", self.ldl_cholesterol, "mg/dL", None, 100.0, "< 100 mg/dL"),
            ("Lipid Profile", "Triglycerides", self.triglycerides, "mg/dL", None, 150.0, "< 150 mg/dL"),
            ("Lipid Profile", "VLDL", self.vldl, "mg/dL", 2.0, 30.0, "2 - 30 mg/dL"),

            ("Vitamins & Minerals", "Vitamin D3", self.vitamin_d, "ng/mL", 30.0, 100.0, "30 - 100 ng/mL"),
            ("Vitamins & Minerals", "Vitamin B12", self.vitamin_b12, "pg/mL", 200.0, 900.0, "200 - 900 pg/mL"),
            ("Vitamins & Minerals", "Iron / Ferritin", self.iron_ferritin, "ng/mL", 20.0, 250.0, "20 - 250 ng/mL"),
            ("Vitamins & Minerals", "Calcium", self.calcium, "mg/dL", 8.5, 10.2, "8.5 - 10.2 mg/dL"),

            ("Metabolic & Organs", "Fasting Blood Sugar", self.blood_sugar_fasting, "mg/dL", 70.0, 99.0, "70 - 99 mg/dL"),
            ("Metabolic & Organs", "HbA1c", self.hba1c, "%", None, 5.7, "< 5.7 %"),
            ("Metabolic & Organs", "Serum Creatinine", self.serum_creatinine, "mg/dL", 0.7, 1.3, "0.7 - 1.3 mg/dL"),
            ("Metabolic & Organs", "Uric Acid", self.uric_acid, "mg/dL", 3.5, 7.2, "3.5 - 7.2 mg/dL"),
            ("Metabolic & Organs", "SGPT (ALT)", self.sgpt_alt, "U/L", 7.0, 56.0, "7 - 56 U/L"),
            ("Metabolic & Organs", "SGOT (AST)", self.sgot_ast, "U/L", 10.0, 40.0, "10 - 40 U/L"),
            ("Metabolic & Organs", "TSH (Thyroid)", self.tsh, "uIU/mL", 0.4, 4.0, "0.4 - 4.0 uIU/mL"),
        ]

        panels = {"CBC": [], "Lipid Profile": [], "Vitamins & Minerals": [], "Metabolic & Organs": []}
        for panel, name, val, unit, min_val, max_val, ref_text in standards:
            if val is not None:
                status = "Normal"
                badge = "success"
                if min_val is not None and val < min_val:
                    status = "Low"
                    badge = "warning"
                elif max_val is not None and val > max_val:
                    status = "High"
                    badge = "danger"
                panels[panel].append({
                    "name": name,
                    "value": val,
                    "unit": unit,
                    "ref": ref_text,
                    "status": status,
                    "badge": badge
                })
        return panels

    def __repr__(self):
        return f"<MedicalReport {self.title} on {self.test_date}>"


class HealthIssue(db.Model):
    __tablename__ = "health_issues"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    title = db.Column(db.String(150), nullable=False)  # e.g., "Seasonal Viral Fever", "Lower Back Sprain"
    issue_type = db.Column(db.String(50), nullable=False, default="Fever / Infection")  # Fever / Infection, Injury / Pain, Dental, Digestive, Respiratory, ENT / Eye, Skin, Chronic, Other
    severity = db.Column(db.String(20), nullable=False, default="Moderate")  # Mild, Moderate, Severe
    status = db.Column(db.String(20), nullable=False, default="Active")  # Active, Recovering, Resolved, Chronic
    start_date = db.Column(db.Date, nullable=False, default=date.today)
    end_date = db.Column(db.Date, nullable=True)
    symptoms = db.Column(db.Text, nullable=True)
    doctor_visited = db.Column(db.Boolean, default=False, nullable=False)
    doctor_name = db.Column(db.String(100), nullable=True)
    clinic_hospital = db.Column(db.String(150), nullable=True)
    diagnosis = db.Column(db.Text, nullable=True)
    prescription = db.Column(db.Text, nullable=True)  # Medications & dosages
    follow_up_date = db.Column(db.Date, nullable=True)
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    def __repr__(self):
        return f"<HealthIssue {self.title} ({self.status})>"


class DietTarget(db.Model):
    __tablename__ = "diet_targets"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True)
    target_calories = db.Column(db.Integer, nullable=False, default=2000)
    target_protein_g = db.Column(db.Float, nullable=False, default=80.0)
    target_carbs_g = db.Column(db.Float, nullable=False, default=250.0)
    target_fats_g = db.Column(db.Float, nullable=False, default=65.0)
    target_fiber_g = db.Column(db.Float, nullable=False, default=30.0)
    target_water_ml = db.Column(db.Integer, nullable=False, default=2500)  # ~8-10 glasses
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    def __repr__(self):
        return f"<DietTarget User {self.user_id}: {self.target_calories} kcal>"


class DietLog(db.Model):
    __tablename__ = "diet_logs"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    date = db.Column(db.Date, nullable=False, default=date.today, index=True)
    meal_type = db.Column(db.String(30), nullable=False, default="Breakfast")  # Breakfast, Lunch, Dinner, Snack, Pre/Post-Workout
    food_items = db.Column(db.Text, nullable=False)  # Description of meals / foods
    food_tags = db.Column(db.String(255), nullable=True)  # e.g., "Vegetables, Cereals/Grains, Fruits, Bread/Rotis, Dairy"
    calories = db.Column(db.Float, nullable=False, default=0.0)
    protein_g = db.Column(db.Float, nullable=False, default=0.0)
    carbs_g = db.Column(db.Float, nullable=False, default=0.0)
    fats_g = db.Column(db.Float, nullable=False, default=0.0)
    fiber_g = db.Column(db.Float, nullable=False, default=0.0)
    notes = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    def tags_list(self):
        if not self.food_tags:
            return []
        return [t.strip() for t in self.food_tags.split(",") if t.strip()]

    def __repr__(self):
        return f"<DietLog {self.meal_type} on {self.date}: {self.calories} kcal>"


class DailyHealthLog(db.Model):
    """Daily holistic log for quick hydration, sleep, and overall wellness score."""
    __tablename__ = "daily_health_logs"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    date = db.Column(db.Date, nullable=False, default=date.today, index=True)
    water_ml = db.Column(db.Integer, nullable=False, default=0)
    sleep_hours = db.Column(db.Float, nullable=True, default=7.0)
    sleep_quality = db.Column(db.String(20), nullable=True, default="Good")  # Poor, Fair, Good, Excellent
    energy_level = db.Column(db.Integer, nullable=True, default=4)  # 1 to 5 scale
    notes = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    __table_args__ = (db.UniqueConstraint("user_id", "date", name="uq_user_daily_health"),)

    def __repr__(self):
        return f"<DailyHealthLog User {self.user_id} on {self.date}: {self.water_ml}ml water, {self.sleep_hours}h sleep>"
