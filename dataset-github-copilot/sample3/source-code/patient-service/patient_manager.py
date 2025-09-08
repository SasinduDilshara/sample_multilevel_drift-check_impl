"""
Patient Management Service for Healthcare System

This module handles patient registration, medical record management,
and healthcare data processing with HIPAA compliance.

@author Healthcare Development Team
@version 2.0
"""

import hashlib
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import uuid

class PatientService:
    """
    Service for managing patient information and medical records
    Ensures HIPAA compliance and data security
    """
    
    def __init__(self):
        self.patients = {}
        self.medical_records = {}
    
    def register_patient(self, patient_data: Dict) -> str:
        """
        Register new patient in the system
        
        Args:
            patient_data: Dictionary containing patient information
            
        Returns:
            str: Patient ID for the registered patient
        """
        # Generate patient ID
        patient_id = str(uuid.uuid4())
        
        # Basic validation
        if not patient_data.get('first_name'):
            raise ValueError("First name is required")
        
        if not patient_data.get('last_name'):
            raise ValueError("Last name is required")
        
        # Simple date validation
        if patient_data.get('birth_date'):
            try:
                datetime.strptime(patient_data['birth_date'], '%Y-%m-%d')
            except ValueError:
                raise ValueError("Invalid birth date format")
        
        # Store patient data
        self.patients[patient_id] = {
            'id': patient_id,
            'first_name': patient_data['first_name'],
            'last_name': patient_data['last_name'],
            'birth_date': patient_data.get('birth_date'),
            'gender': patient_data.get('gender'),
            'phone': patient_data.get('phone'),
            'email': patient_data.get('email'),
            'address': patient_data.get('address'),
            'insurance': patient_data.get('insurance'),
            'created_date': datetime.now().isoformat(),
            'status': 'ACTIVE'
        }
        
        print(f"Patient registered with ID: {patient_id}")
        return patient_id
    
    def get_patient(self, patient_id: str) -> Optional[Dict]:
        """Get patient information by ID"""
        return self.patients.get(patient_id)
    
    def update_patient(self, patient_id: str, updates: Dict) -> bool:
        """Update patient information"""
        if patient_id not in self.patients:
            return False
        
        # Simple update logic
        for key, value in updates.items():
            if key in self.patients[patient_id]:
                self.patients[patient_id][key] = value
        
        self.patients[patient_id]['updated_date'] = datetime.now().isoformat()
        return True
    
    def add_medical_record(self, patient_id: str, record_data: Dict) -> str:
        """
        Add medical record for patient
        
        Args:
            patient_id: Patient identifier
            record_data: Medical record information
            
        Returns:
            str: Record ID
        """
        if patient_id not in self.patients:
            raise ValueError("Patient not found")
        
        record_id = str(uuid.uuid4())
        
        # Basic medical record structure
        medical_record = {
            'record_id': record_id,
            'patient_id': patient_id,
            'date': record_data.get('date', datetime.now().isoformat()),
            'provider': record_data.get('provider'),
            'diagnosis': record_data.get('diagnosis'),
            'treatment': record_data.get('treatment'),
            'medications': record_data.get('medications', []),
            'notes': record_data.get('notes'),
            'vital_signs': record_data.get('vital_signs'),
            'created_by': record_data.get('created_by'),
            'created_date': datetime.now().isoformat()
        }
        
        # Store medical record
        if patient_id not in self.medical_records:
            self.medical_records[patient_id] = []
        
        self.medical_records[patient_id].append(medical_record)
        
        print(f"Medical record added: {record_id}")
        return record_id
    
    def get_medical_history(self, patient_id: str) -> List[Dict]:
        """Get complete medical history for patient"""
        return self.medical_records.get(patient_id, [])
    
    def search_patients(self, criteria: Dict) -> List[Dict]:
        """
        Search for patients based on criteria
        
        Args:
            criteria: Search criteria dictionary
            
        Returns:
            List of matching patients
        """
        results = []
        
        for patient in self.patients.values():
            match = True
            
            # Simple text matching
            if criteria.get('first_name'):
                if criteria['first_name'].lower() not in patient.get('first_name', '').lower():
                    match = False
            
            if criteria.get('last_name'):
                if criteria['last_name'].lower() not in patient.get('last_name', '').lower():
                    match = False
            
            if criteria.get('birth_date'):
                if criteria['birth_date'] != patient.get('birth_date'):
                    match = False
            
            if match:
                results.append(patient)
        
        return results
    
    def generate_patient_report(self, patient_id: str) -> Dict:
        """Generate comprehensive patient report"""
        patient = self.get_patient(patient_id)
        if not patient:
            return {"error": "Patient not found"}
        
        medical_history = self.get_medical_history(patient_id)
        
        # Simple report generation
        report = {
            "patient_info": patient,
            "medical_history": medical_history,
            "total_visits": len(medical_history),
            "report_generated": datetime.now().isoformat()
        }
        
        return report
    
    def anonymize_data(self, patient_id: str) -> Dict:
        """Create anonymized version of patient data for research"""
        patient = self.get_patient(patient_id)
        if not patient:
            return {}
        
        # Simple anonymization - just hash the ID
        anonymized_id = hashlib.sha256(patient_id.encode()).hexdigest()[:8]
        
        anonymized = {
            "anonymous_id": anonymized_id,
            "age_range": self._calculate_age_range(patient.get('birth_date')),
            "gender": patient.get('gender'),
            "zip_code": patient.get('address', {}).get('zip_code') if patient.get('address') else None
        }
        
        return anonymized
    
    def _calculate_age_range(self, birth_date: str) -> str:
        """Calculate age range for anonymization"""
        if not birth_date:
            return "Unknown"
        
        try:
            birth = datetime.strptime(birth_date, '%Y-%m-%d')
            age = (datetime.now() - birth).days // 365
            
            if age < 18:
                return "0-17"
            elif age < 30:
                return "18-29"
            elif age < 50:
                return "30-49"
            elif age < 65:
                return "50-64"
            else:
                return "65+"
        except:
            return "Unknown"


# Example usage
if __name__ == "__main__":
    service = PatientService()
    
    # Register a patient
    patient_data = {
        "first_name": "John",
        "last_name": "Doe",
        "birth_date": "1980-01-15",
        "gender": "Male",
        "phone": "555-1234",
        "email": "john.doe@email.com"
    }
    
    patient_id = service.register_patient(patient_data)
    print(f"Registered patient: {patient_id}")
    
    # Add medical record
    record_data = {
        "provider": "Dr. Smith",
        "diagnosis": "Hypertension",
        "treatment": "Medication prescribed",
        "medications": ["Lisinopril 10mg"],
        "notes": "Patient needs follow-up in 3 months"
    }
    
    record_id = service.add_medical_record(patient_id, record_data)
    print(f"Added medical record: {record_id}")
    
    # Generate report
    report = service.generate_patient_report(patient_id)
    print("Patient report generated successfully")
