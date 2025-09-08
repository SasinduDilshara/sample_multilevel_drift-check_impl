package com.education.student;

import java.util.*;
import java.time.LocalDateTime;

/**
 * Student management service
 * Handles student enrollment and academic records
 */
public class StudentService {
    
    private Map<String, Student> students = new HashMap<>();
    
    // Register new student
    public String enrollStudent(String firstName, String lastName, String email) {
        String studentId = generateStudentId();
        
        Student student = new Student();
        student.setId(studentId);
        student.setFirstName(firstName);
        student.setLastName(lastName);
        student.setEmail(email);
        student.setEnrollmentDate(LocalDateTime.now());
        student.setStatus("ENROLLED");
        
        students.put(studentId, student);
        
        // Send welcome email (not implemented)
        sendWelcomeEmail(email);
        
        return studentId;
    }
    
    // Get student info
    public Student getStudent(String studentId) {
        return students.get(studentId);
    }
    
    // Update grades
    public void updateGrade(String studentId, String course, double grade) {
        Student student = students.get(studentId);
        if (student != null) {
            student.getGrades().put(course, grade);
        }
    }
    
    // Calculate GPA
    public double calculateGPA(String studentId) {
        Student student = students.get(studentId);
        if (student == null || student.getGrades().isEmpty()) {
            return 0.0;
        }
        
        double total = 0;
        for (double grade : student.getGrades().values()) {
            total += grade;
        }
        
        return total / student.getGrades().size();
    }
    
    // Simple helper methods
    private String generateStudentId() {
        return "STU" + System.currentTimeMillis();
    }
    
    private void sendWelcomeEmail(String email) {
        // Email sending logic would go here
        System.out.println("Welcome email sent to: " + email);
    }
}

class Student {
    private String id;
    private String firstName;
    private String lastName;
    private String email;
    private LocalDateTime enrollmentDate;
    private String status;
    private Map<String, Double> grades = new HashMap<>();
    
    // Getters and setters
    public String getId() { return id; }
    public void setId(String id) { this.id = id; }
    
    public String getFirstName() { return firstName; }
    public void setFirstName(String firstName) { this.firstName = firstName; }
    
    public String getLastName() { return lastName; }
    public void setLastName(String lastName) { this.lastName = lastName; }
    
    public String getEmail() { return email; }
    public void setEmail(String email) { this.email = email; }
    
    public LocalDateTime getEnrollmentDate() { return enrollmentDate; }
    public void setEnrollmentDate(LocalDateTime enrollmentDate) { this.enrollmentDate = enrollmentDate; }
    
    public String getStatus() { return status; }
    public void setStatus(String status) { this.status = status; }
    
    public Map<String, Double> getGrades() { return grades; }
    public void setGrades(Map<String, Double> grades) { this.grades = grades; }
}
