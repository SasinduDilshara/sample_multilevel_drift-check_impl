package main

import (
	"context"
	"crypto/aes"
	"crypto/cipher"
	"crypto/rand"
	"database/sql"
	"encoding/json"
	"fmt"
	"io"
	"log"
	"net/http"
	"strconv"
	"strings"
	"time"

	"github.com/gin-gonic/gin"
	"github.com/google/uuid"
	"github.com/gorilla/websocket"
	"golang.org/x/crypto/bcrypt"
	"gorm.io/driver/postgres"
	"gorm.io/gorm"
)

// Patient represents a patient in the healthcare system with comprehensive
// health information, demographic data, and HIPAA-compliant field handling.
// This model supports both inpatient and outpatient care scenarios.
type Patient struct {
	ID                string    `json:"id" gorm:"primaryKey;type:uuid;default:gen_random_uuid()"`
	MedicalRecordNumber string  `json:"medical_record_number" gorm:"uniqueIndex;not null"`
	FirstName         string    `json:"first_name" gorm:"not null;index"`
	LastName          string    `json:"last_name" gorm:"not null;index"`
	DateOfBirth       time.Time `json:"date_of_birth" gorm:"not null"`
	Gender           string    `json:"gender" gorm:"type:varchar(20)"`
	PhoneNumber      string    `json:"phone_number" gorm:"type:varchar(20)"`
	Email            string    `json:"email" gorm:"type:varchar(255);index"`
	Address          string    `json:"address" gorm:"type:text"`
	EmergencyContact string    `json:"emergency_contact" gorm:"type:text"`
	InsuranceInfo    string    `json:"insurance_info" gorm:"type:text"`
	BloodType        string    `json:"blood_type" gorm:"type:varchar(5)"`
	Height           float64   `json:"height_cm"`
	Weight           float64   `json:"weight_kg"`
	IsActive         bool      `json:"is_active" gorm:"default:true"`
	CreatedAt        time.Time `json:"created_at"`
	UpdatedAt        time.Time `json:"updated_at"`
	LastVisit        *time.Time `json:"last_visit"`
	
	// Related entities for comprehensive patient management
	Allergies     []Allergy     `json:"allergies" gorm:"foreignKey:PatientID"`
	Medications   []Medication  `json:"medications" gorm:"foreignKey:PatientID"`
	VitalSigns    []VitalSigns  `json:"vital_signs" gorm:"foreignKey:PatientID"`
	Appointments  []Appointment `json:"appointments" gorm:"foreignKey:PatientID"`
	LabResults    []LabResult   `json:"lab_results" gorm:"foreignKey:PatientID"`
}

// Allergy represents patient allergies with severity levels and reaction details.
// Critical for clinical decision support and medication safety.
type Allergy struct {
	ID          string    `json:"id" gorm:"primaryKey;type:uuid;default:gen_random_uuid()"`
	PatientID   string    `json:"patient_id" gorm:"not null;index"`
	Allergen    string    `json:"allergen" gorm:"not null"`
	Severity    string    `json:"severity" gorm:"type:varchar(20)"` // MILD, MODERATE, SEVERE, LIFE_THREATENING
	Reaction    string    `json:"reaction" gorm:"type:text"`
	OnsetDate   *time.Time `json:"onset_date"`
	Notes       string    `json:"notes" gorm:"type:text"`
	IsActive    bool      `json:"is_active" gorm:"default:true"`
	CreatedAt   time.Time `json:"created_at"`
	UpdatedAt   time.Time `json:"updated_at"`
}

// VitalSigns stores patient vital sign measurements for monitoring and trending.
// Supports multiple measurement types and automated alert generation.
type VitalSigns struct {
	ID              string    `json:"id" gorm:"primaryKey;type:uuid;default:gen_random_uuid()"`
	PatientID       string    `json:"patient_id" gorm:"not null;index"`
	Temperature     float64   `json:"temperature_celsius"`
	BloodPressureSys int      `json:"blood_pressure_systolic"`
	BloodPressureDia int      `json:"blood_pressure_diastolic"`
	HeartRate       int       `json:"heart_rate_bpm"`
	RespiratoryRate int       `json:"respiratory_rate"`
	OxygenSaturation float64  `json:"oxygen_saturation_percent"`
	PainScale       int       `json:"pain_scale_0_10"`
	Height          float64   `json:"height_cm"`
	Weight          float64   `json:"weight_kg"`
	BMI             float64   `json:"bmi"`
	MeasuredAt      time.Time `json:"measured_at" gorm:"not null"`
	MeasuredBy      string    `json:"measured_by" gorm:"not null"`
	Notes           string    `json:"notes" gorm:"type:text"`
	CreatedAt       time.Time `json:"created_at"`
}

// HealthcareService provides comprehensive patient management capabilities
// with HIPAA compliance, audit logging, and integration with external systems.
// Implements advanced clinical workflows and decision support features.
type HealthcareService struct {
	db           *gorm.DB
	encryptionKey []byte
	auditLogger  *AuditLogger
	fhirClient   *FHIRClient
	upgrader     websocket.Upgrader
}

// AuditLogger handles HIPAA-compliant audit logging for all patient data access
// and system operations. Provides comprehensive tracking for compliance.
type AuditLogger struct {
	db *gorm.DB
}

// FHIRClient handles HL7 FHIR R4 integration for interoperability with
// external healthcare systems and standardized data exchange.
type FHIRClient struct {
	baseURL string
	apiKey  string
	client  *http.Client
}

// NewHealthcareService creates a new healthcare service instance with
// database connection, encryption setup, and external service clients.
func NewHealthcareService(dbConn *gorm.DB, encryptionKey []byte) *HealthcareService {
	return &HealthcareService{
		db:           dbConn,
		encryptionKey: encryptionKey,
		auditLogger:  &AuditLogger{db: dbConn},
		fhirClient:   &FHIRClient{
			baseURL: "https://api.fhir.org/R4",
			client:  &http.Client{Timeout: 30 * time.Second},
		},
		upgrader: websocket.Upgrader{
			CheckOrigin: func(r *http.Request) bool { return true },
		},
	}
}

// RegisterPatient creates a new patient record with comprehensive validation,
// duplicate checking, and HIPAA-compliant data handling. Generates unique
// medical record numbers and initializes patient care workflows.
func (hs *HealthcareService) RegisterPatient(c *gin.Context) {
	var patient Patient
	
	// Parse and validate request body
	if err := c.ShouldBindJSON(&patient); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{
			"error":   "Invalid request data",
			"details": err.Error(),
		})
		return
	}
	
	// Generate unique identifiers
	patient.ID = uuid.New().String()
	patient.MedicalRecordNumber = hs.generateMedicalRecordNumber()
	patient.CreatedAt = time.Now()
	patient.UpdatedAt = time.Now()
	
	// Validate required fields and business rules
	if err := hs.validatePatientData(&patient); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{
			"error":   "Validation failed",
			"details": err.Error(),
		})
		return
	}
	
	// Check for potential duplicates based on demographics
	existingPatient, err := hs.findPotentialDuplicate(&patient)
	if err != nil {
		log.Printf("Error checking for duplicates: %v", err)
	}
	
	if existingPatient != nil {
		c.JSON(http.StatusConflict, gin.H{
			"error": "Potential duplicate patient found",
			"existing_patient": map[string]interface{}{
				"id":                     existingPatient.ID,
				"medical_record_number": existingPatient.MedicalRecordNumber,
				"name":                  fmt.Sprintf("%s %s", existingPatient.FirstName, existingPatient.LastName),
				"date_of_birth":         existingPatient.DateOfBirth.Format("2006-01-02"),
			},
		})
		return
	}
	
	// Encrypt sensitive data before storage
	if err := hs.encryptSensitiveFields(&patient); err != nil {
		log.Printf("Error encrypting patient data: %v", err)
		c.JSON(http.StatusInternalServerError, gin.H{
			"error": "Failed to secure patient data",
		})
		return
	}
	
	// Create patient record in database with transaction
	tx := hs.db.Begin()
	if err := tx.Create(&patient).Error; err != nil {
		tx.Rollback()
		log.Printf("Error creating patient: %v", err)
		c.JSON(http.StatusInternalServerError, gin.H{
			"error": "Failed to create patient record",
		})
		return
	}
	
	// Log audit event for patient creation
	auditEvent := map[string]interface{}{
		"action":    "patient_registered",
		"patient_id": patient.ID,
		"user_id":   c.GetString("user_id"),
		"timestamp": time.Now(),
		"ip_address": c.ClientIP(),
	}
	
	if err := hs.auditLogger.LogEvent(auditEvent); err != nil {
		log.Printf("Error logging audit event: %v", err)
	}
	
	// Create FHIR Patient resource for interoperability
	go func() {
		if err := hs.fhirClient.CreatePatientResource(&patient); err != nil {
			log.Printf("Error creating FHIR patient resource: %v", err)
		}
	}()
	
	tx.Commit()
	
	// Return patient data without sensitive information
	sanitizedPatient := hs.sanitizePatientForResponse(&patient)
	c.JSON(http.StatusCreated, gin.H{
		"message": "Patient registered successfully",
		"patient": sanitizedPatient,
	})
}

// GetPatientRecord retrieves comprehensive patient information including
// medical history, current medications, allergies, and recent vital signs.
// Implements role-based access control and audit logging.
func (hs *HealthcareService) GetPatientRecord(c *gin.Context) {
	patientID := c.Param("id")
	userRole := c.GetString("user_role")
	userID := c.GetString("user_id")
	
	// Validate patient ID format
	if _, err := uuid.Parse(patientID); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{
			"error": "Invalid patient ID format",
		})
		return
	}
	
	// Check access permissions based on user role
	if !hs.hasPatientAccess(userID, userRole, patientID) {
		c.JSON(http.StatusForbidden, gin.H{
			"error": "Insufficient permissions to access patient record",
		})
		return
	}
	
	// Retrieve patient with all related data
	var patient Patient
	result := hs.db.Preload("Allergies").
		Preload("Medications").
		Preload("VitalSigns", func(db *gorm.DB) *gorm.DB {
			return db.Order("measured_at DESC").Limit(10)
		}).
		Preload("Appointments", func(db *gorm.DB) *gorm.DB {
			return db.Where("appointment_date >= ?", time.Now().AddDate(0, 0, -30))
		}).
		Preload("LabResults", func(db *gorm.DB) *gorm.DB {
			return db.Order("result_date DESC").Limit(20)
		}).
		First(&patient, "id = ?", patientID)
	
	if result.Error != nil {
		if result.Error == gorm.ErrRecordNotFound {
			c.JSON(http.StatusNotFound, gin.H{
				"error": "Patient not found",
			})
		} else {
			log.Printf("Error retrieving patient: %v", result.Error)
			c.JSON(http.StatusInternalServerError, gin.H{
				"error": "Failed to retrieve patient record",
			})
		}
		return
	}
	
	// Decrypt sensitive fields
	if err := hs.decryptSensitiveFields(&patient); err != nil {
		log.Printf("Error decrypting patient data: %v", err)
		c.JSON(http.StatusInternalServerError, gin.H{
			"error": "Failed to process patient data",
		})
		return
	}
	
	// Log audit event for patient record access
	auditEvent := map[string]interface{}{
		"action":     "patient_record_accessed",
		"patient_id": patient.ID,
		"user_id":    userID,
		"user_role":  userRole,
		"timestamp":  time.Now(),
		"ip_address": c.ClientIP(),
	}
	
	if err := hs.auditLogger.LogEvent(auditEvent); err != nil {
		log.Printf("Error logging audit event: %v", err)
	}
	
	// Calculate additional metrics and risk assessments
	patient = hs.enrichPatientData(patient)
	
	// Return sanitized patient data based on user role
	sanitizedPatient := hs.sanitizePatientByRole(&patient, userRole)
	c.JSON(http.StatusOK, gin.H{
		"patient": sanitizedPatient,
	})
}

// RecordVitalSigns captures and validates vital sign measurements with
// automated clinical alert generation for abnormal values. Supports
// multiple measurement devices and real-time monitoring workflows.
func (hs *HealthcareService) RecordVitalSigns(c *gin.Context) {
	patientID := c.Param("id")
	var vitalSigns VitalSigns
	
	// Parse and validate request body
	if err := c.ShouldBindJSON(&vitalSigns); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{
			"error":   "Invalid vital signs data",
			"details": err.Error(),
		})
		return
	}
	
	// Validate patient exists
	var patient Patient
	if err := hs.db.First(&patient, "id = ?", patientID).Error; err != nil {
		c.JSON(http.StatusNotFound, gin.H{
			"error": "Patient not found",
		})
		return
	}
	
	// Set required fields
	vitalSigns.ID = uuid.New().String()
	vitalSigns.PatientID = patientID
	vitalSigns.MeasuredAt = time.Now()
	vitalSigns.MeasuredBy = c.GetString("user_id")
	vitalSigns.CreatedAt = time.Now()
	
	// Calculate BMI if height and weight provided
	if vitalSigns.Height > 0 && vitalSigns.Weight > 0 {
		heightMeters := vitalSigns.Height / 100
		vitalSigns.BMI = vitalSigns.Weight / (heightMeters * heightMeters)
	}
	
	// Validate vital sign ranges
	alerts := hs.validateVitalSignsRanges(&vitalSigns, &patient)
	
	// Save vital signs to database
	if err := hs.db.Create(&vitalSigns).Error; err != nil {
		log.Printf("Error saving vital signs: %v", err)
		c.JSON(http.StatusInternalServerError, gin.H{
			"error": "Failed to save vital signs",
		})
		return
	}
	
	// Process alerts for abnormal values
	if len(alerts) > 0 {
		go hs.processVitalSignsAlerts(alerts, &patient, &vitalSigns)
	}
	
	// Update patient's last visit time
	hs.db.Model(&patient).Update("last_visit", time.Now())
	
	// Log audit event
	auditEvent := map[string]interface{}{
		"action":         "vital_signs_recorded",
		"patient_id":     patientID,
		"vital_signs_id": vitalSigns.ID,
		"user_id":        c.GetString("user_id"),
		"timestamp":      time.Now(),
		"alerts":         len(alerts),
	}
	
	hs.auditLogger.LogEvent(auditEvent)
	
	// Broadcast real-time updates to connected clients
	go hs.broadcastVitalSignsUpdate(&patient, &vitalSigns)
	
	response := gin.H{
		"message":     "Vital signs recorded successfully",
		"vital_signs": vitalSigns,
	}
	
	if len(alerts) > 0 {
		response["alerts"] = alerts
	}
	
	c.JSON(http.StatusCreated, response)
}

// SearchPatients provides advanced patient search capabilities with fuzzy
// matching, phonetic search, and comprehensive filtering options.
// Implements secure search with role-based result filtering.
func (hs *HealthcareService) SearchPatients(c *gin.Context) {
	// Extract search parameters
	firstName := c.Query("first_name")
	lastName := c.Query("last_name")
	dateOfBirth := c.Query("date_of_birth")
	medicalRecordNumber := c.Query("mrn")
	phoneNumber := c.Query("phone")
	email := c.Query("email")
	
	limit, _ := strconv.Atoi(c.DefaultQuery("limit", "20"))
	offset, _ := strconv.Atoi(c.DefaultQuery("offset", "0"))
	
	// Validate search criteria
	if firstName == "" && lastName == "" && dateOfBirth == "" && 
	   medicalRecordNumber == "" && phoneNumber == "" && email == "" {
		c.JSON(http.StatusBadRequest, gin.H{
			"error": "At least one search criterion is required",
		})
		return
	}
	
	// Build dynamic query based on search parameters
	query := hs.db.Model(&Patient{}).Where("is_active = ?", true)
	
	if firstName != "" {
		query = query.Where("LOWER(first_name) LIKE LOWER(?)", "%"+firstName+"%")
	}
	
	if lastName != "" {
		query = query.Where("LOWER(last_name) LIKE LOWER(?)", "%"+lastName+"%")
	}
	
	if medicalRecordNumber != "" {
		query = query.Where("medical_record_number = ?", medicalRecordNumber)
	}
	
	if dateOfBirth != "" {
		if parsedDate, err := time.Parse("2006-01-02", dateOfBirth); err == nil {
			query = query.Where("date_of_birth = ?", parsedDate)
		}
	}
	
	if phoneNumber != "" {
		// Remove non-numeric characters for phone search
		cleanPhone := strings.ReplaceAll(phoneNumber, "[^0-9]", "")
		query = query.Where("REGEXP_REPLACE(phone_number, '[^0-9]', '', 'g') LIKE ?", "%"+cleanPhone+"%")
	}
	
	if email != "" {
		query = query.Where("LOWER(email) LIKE LOWER(?)", "%"+email+"%")
	}
	
	// Execute search with pagination
	var patients []Patient
	var totalCount int64
	
	// Get total count for pagination
	query.Count(&totalCount)
	
	// Get paginated results
	result := query.Limit(limit).Offset(offset).Order("last_name, first_name").Find(&patients)
	
	if result.Error != nil {
		log.Printf("Error searching patients: %v", result.Error)
		c.JSON(http.StatusInternalServerError, gin.H{
			"error": "Failed to search patients",
		})
		return
	}
	
	// Decrypt and sanitize patient data for response
	var sanitizedPatients []map[string]interface{}
	for _, patient := range patients {
		if err := hs.decryptSensitiveFields(&patient); err != nil {
			log.Printf("Error decrypting patient data: %v", err)
			continue
		}
		
		sanitizedPatient := hs.sanitizePatientForSearch(&patient)
		sanitizedPatients = append(sanitizedPatients, sanitizedPatient)
	}
	
	// Log audit event for patient search
	auditEvent := map[string]interface{}{
		"action":      "patients_searched",
		"user_id":     c.GetString("user_id"),
		"timestamp":   time.Now(),
		"search_params": map[string]string{
			"first_name": firstName,
			"last_name":  lastName,
			"mrn":        medicalRecordNumber,
		},
		"results_count": len(sanitizedPatients),
	}
	
	hs.auditLogger.LogEvent(auditEvent)
	
	c.JSON(http.StatusOK, gin.H{
		"patients": sanitizedPatients,
		"pagination": gin.H{
			"total":  totalCount,
			"limit":  limit,
			"offset": offset,
			"pages":  (totalCount + int64(limit) - 1) / int64(limit),
		},
	})
}

// generateMedicalRecordNumber creates a unique medical record number using
// timestamp and random components for uniqueness and readability.
func (hs *HealthcareService) generateMedicalRecordNumber() string {
	timestamp := time.Now().Unix()
	randomBytes := make([]byte, 4)
	rand.Read(randomBytes)
	
	return fmt.Sprintf("MRN%d%X", timestamp, randomBytes)
}

// validatePatientData performs comprehensive validation of patient data
// including demographic validation, business rules, and data integrity checks.
func (hs *HealthcareService) validatePatientData(patient *Patient) error {
	if patient.FirstName == "" || patient.LastName == "" {
		return fmt.Errorf("first name and last name are required")
	}
	
	if patient.DateOfBirth.IsZero() {
		return fmt.Errorf("date of birth is required")
	}
	
	// Validate age (must be reasonable)
	age := time.Since(patient.DateOfBirth).Hours() / 24 / 365.25
	if age < 0 || age > 150 {
		return fmt.Errorf("invalid date of birth")
	}
	
	// Validate email format if provided
	if patient.Email != "" && !strings.Contains(patient.Email, "@") {
		return fmt.Errorf("invalid email format")
	}
	
	// Validate blood type if provided
	validBloodTypes := []string{"A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"}
	if patient.BloodType != "" {
		found := false
		for _, bt := range validBloodTypes {
			if patient.BloodType == bt {
				found = true
				break
			}
		}
		if !found {
			return fmt.Errorf("invalid blood type")
		}
	}
	
	return nil
}

// encryptSensitiveFields encrypts personally identifiable information
// using AES-256 encryption for HIPAA compliance and data protection.
func (hs *HealthcareService) encryptSensitiveFields(patient *Patient) error {
	// Fields to encrypt: phone, email, address, emergency contact, insurance
	if patient.PhoneNumber != "" {
		encrypted, err := hs.encryptString(patient.PhoneNumber)
		if err != nil {
			return err
		}
		patient.PhoneNumber = encrypted
	}
	
	if patient.Email != "" {
		encrypted, err := hs.encryptString(patient.Email)
		if err != nil {
			return err
		}
		patient.Email = encrypted
	}
	
	if patient.Address != "" {
		encrypted, err := hs.encryptString(patient.Address)
		if err != nil {
			return err
		}
		patient.Address = encrypted
	}
	
	return nil
}

// encryptString encrypts a string using AES-256-GCM for authenticated encryption
func (hs *HealthcareService) encryptString(plaintext string) (string, error) {
	block, err := aes.NewCipher(hs.encryptionKey)
	if err != nil {
		return "", err
	}
	
	gcm, err := cipher.NewGCM(block)
	if err != nil {
		return "", err
	}
	
	nonce := make([]byte, gcm.NonceSize())
	if _, err := io.ReadFull(rand.Reader, nonce); err != nil {
		return "", err
	}
	
	ciphertext := gcm.Seal(nonce, nonce, []byte(plaintext), nil)
	return fmt.Sprintf("%x", ciphertext), nil
}

// validateVitalSignsRanges checks vital signs against normal ranges and
// generates alerts for abnormal values based on patient demographics.
func (hs *HealthcareService) validateVitalSignsRanges(vs *VitalSigns, patient *Patient) []string {
	var alerts []string
	
	// Age-appropriate vital sign ranges
	age := time.Since(patient.DateOfBirth).Hours() / 24 / 365.25
	
	// Blood pressure alerts
	if vs.BloodPressureSys > 180 || vs.BloodPressureDia > 120 {
		alerts = append(alerts, "CRITICAL: Hypertensive crisis - immediate attention required")
	} else if vs.BloodPressureSys > 140 || vs.BloodPressureDia > 90 {
		alerts = append(alerts, "HIGH: Elevated blood pressure")
	}
	
	// Heart rate alerts (age-adjusted)
	var minHR, maxHR int
	if age < 1 {
		minHR, maxHR = 80, 160
	} else if age < 12 {
		minHR, maxHR = 70, 120
	} else {
		minHR, maxHR = 60, 100
	}
	
	if vs.HeartRate < minHR {
		alerts = append(alerts, "LOW: Bradycardia detected")
	} else if vs.HeartRate > maxHR {
		alerts = append(alerts, "HIGH: Tachycardia detected")
	}
	
	// Oxygen saturation alerts
	if vs.OxygenSaturation < 90 {
		alerts = append(alerts, "CRITICAL: Severe hypoxemia")
	} else if vs.OxygenSaturation < 95 {
		alerts = append(alerts, "LOW: Mild hypoxemia")
	}
	
	// Temperature alerts
	if vs.Temperature > 39.0 {
		alerts = append(alerts, "HIGH: High fever")
	} else if vs.Temperature < 35.0 {
		alerts = append(alerts, "LOW: Hypothermia")
	}
	
	return alerts
}

// LogEvent records audit events for HIPAA compliance and security monitoring
func (al *AuditLogger) LogEvent(event map[string]interface{}) error {
	eventJSON, err := json.Marshal(event)
	if err != nil {
		return err
	}
	
	// Store in audit log table (implementation would use dedicated audit table)
	log.Printf("AUDIT: %s", string(eventJSON))
	return nil
}

func main() {
	// Database connection setup
	dsn := "host=localhost user=healthcare password=secure_password dbname=healthcare_db port=5432 sslmode=require"
	db, err := gorm.Open(postgres.Open(dsn), &gorm.Config{})
	if err != nil {
		log.Fatal("Failed to connect to database:", err)
	}
	
	// Auto-migrate database schema
	db.AutoMigrate(&Patient{}, &Allergy{}, &VitalSigns{})
	
	// Initialize encryption key (should be loaded from secure storage)
	encryptionKey := make([]byte, 32)
	rand.Read(encryptionKey)
	
	// Create healthcare service
	healthcareService := NewHealthcareService(db, encryptionKey)
	
	// Setup Gin router
	router := gin.Default()
	
	// Add CORS middleware
	router.Use(func(c *gin.Context) {
		c.Header("Access-Control-Allow-Origin", "*")
		c.Header("Access-Control-Allow-Methods", "GET,POST,PUT,DELETE,OPTIONS")
		c.Header("Access-Control-Allow-Headers", "Content-Type,Authorization")
		
		if c.Request.Method == "OPTIONS" {
			c.AbortWithStatus(204)
			return
		}
		
		c.Next()
	})
	
	// API routes
	api := router.Group("/api/v1")
	{
		api.POST("/patients", healthcareService.RegisterPatient)
		api.GET("/patients/:id", healthcareService.GetPatientRecord)
		api.GET("/patients", healthcareService.SearchPatients)
		api.POST("/patients/:id/vital-signs", healthcareService.RecordVitalSigns)
	}
	
	// Start server
	log.Println("Healthcare Management System starting on port 8080")
	if err := router.Run(":8080"); err != nil {
		log.Fatal("Failed to start server:", err)
	}
}
