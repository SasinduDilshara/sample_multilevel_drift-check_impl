# Education Platform API Documentation

## Overview
The Education Platform API provides comprehensive access to learning management functionality, student information systems, and educational content delivery. Built with modern microservices architecture and designed for scalability and reliability.

## Authentication
All API endpoints require authentication using JWT tokens obtained through the OAuth 2.0 flow:

```http
Authorization: Bearer <jwt-token>
Content-Type: application/json
```

## Base URLs
- **Production**: `https://api.eduplatform.edu/v1`
- **Staging**: `https://staging-api.eduplatform.edu/v1`
- **Development**: `http://localhost:3000/api/v1`

## Student Management APIs

### Create Student Profile
Create a new student account with comprehensive profile information.

```http
POST /students
```

**Request Body:**
```json
{
  "studentId": "STU2024001234",
  "firstName": "John",
  "lastName": "Doe",
  "email": "john.doe@email.com",
  "dateOfBirth": "2000-05-15",
  "grade": "12",
  "program": "Computer Science",
  "enrollmentStatus": "ACTIVE",
  "parentContact": {
    "name": "Jane Doe",
    "email": "jane.doe@email.com",
    "phone": "+1-555-0123"
  },
  "academicYear": "2024-2025"
}
```

**Response:**
```json
{
  "message": "Student profile created successfully",
  "student": {
    "id": "uuid-12345",
    "studentId": "STU2024001234",
    "firstName": "John",
    "lastName": "Doe",
    "email": "john.doe@email.com",
    "grade": "12",
    "enrollmentStatus": "ACTIVE",
    "createdAt": "2024-01-15T10:30:00Z"
  }
}
```

### Get Student Profile
Retrieve comprehensive student information including academic records and enrollment details.

```http
GET /students/{studentId}
```

**Response:**
```json
{
  "student": {
    "id": "uuid-12345",
    "studentId": "STU2024001234",
    "firstName": "John",
    "lastName": "Doe",
    "email": "john.doe@email.com",
    "grade": "12",
    "program": "Computer Science",
    "enrollmentStatus": "ACTIVE",
    "gpa": 3.75,
    "totalCredits": 48,
    "enrolledCourses": [
      {
        "courseId": "CS101",
        "courseName": "Introduction to Programming",
        "instructor": "Dr. Smith",
        "credits": 3,
        "currentGrade": "A-"
      }
    ],
    "academicHistory": {
      "transcripts": "/api/v1/students/uuid-12345/transcripts",
      "achievements": "/api/v1/students/uuid-12345/achievements"
    }
  }
}
```

### Update Student Information
Update student profile information with validation and change tracking.

```http
PUT /students/{studentId}
```

## Course Management APIs

### Get Course Catalog
Retrieve available courses with filtering and search capabilities.

```http
GET /courses
```

**Query Parameters:**
- `department`: Filter by department (e.g., "Computer Science")
- `level`: Course level filter (e.g., "undergraduate", "graduate")
- `semester`: Semester filter (e.g., "Fall 2024")
- `search`: Text search in course titles and descriptions
- `limit`: Maximum results per page (default: 50)
- `offset`: Pagination offset (default: 0)

**Response:**
```json
{
  "courses": [
    {
      "courseId": "CS101",
      "title": "Introduction to Programming",
      "description": "Fundamental programming concepts using Python",
      "department": "Computer Science",
      "credits": 3,
      "prerequisites": [],
      "instructor": {
        "name": "Dr. Smith",
        "email": "smith@eduplatform.edu"
      },
      "schedule": {
        "days": ["Monday", "Wednesday", "Friday"],
        "time": "10:00-11:00",
        "location": "Room 201"
      },
      "capacity": 30,
      "enrolled": 25,
      "waitlist": 3
    }
  ],
  "pagination": {
    "total": 150,
    "limit": 50,
    "offset": 0,
    "pages": 3
  }
}
```

### Enroll Student in Course
Enroll a student in a specific course with prerequisite validation.

```http
POST /students/{studentId}/enrollments
```

**Request Body:**
```json
{
  "courseId": "CS101",
  "semester": "Fall 2024",
  "enrollmentType": "REGULAR"
}
```

## Grade Management APIs

### Submit Grade
Submit or update a grade for a student in a specific course.

```http
POST /courses/{courseId}/grades
```

**Request Body:**
```json
{
  "studentId": "STU2024001234",
  "assignmentType": "EXAM",
  "assignmentName": "Midterm Exam",
  "score": 85,
  "maxScore": 100,
  "weight": 0.25,
  "submittedAt": "2024-02-15T14:30:00Z",
  "gradedBy": "instructor-id-123"
}
```

### Get Student Grades
Retrieve grades for a specific student across all courses.

```http
GET /students/{studentId}/grades
```

**Query Parameters:**
- `semester`: Filter by semester
- `courseId`: Filter by specific course
- `assignmentType`: Filter by assignment type (EXAM, QUIZ, HOMEWORK, PROJECT)

### Calculate GPA
Calculate current GPA for a student based on completed courses.

```http
GET /students/{studentId}/gpa
```

**Response:**
```json
{
  "currentGPA": 3.75,
  "cumulativeGPA": 3.68,
  "totalCredits": 48,
  "completedCourses": 16,
  "semesterGPAs": [
    {
      "semester": "Fall 2023",
      "gpa": 3.85,
      "credits": 12
    },
    {
      "semester": "Spring 2024",
      "gpa": 3.65,
      "credits": 15
    }
  ]
}
```

## Assignment Management APIs

### Create Assignment
Create a new assignment for a course with detailed specifications.

```http
POST /courses/{courseId}/assignments
```

**Request Body:**
```json
{
  "title": "Database Design Project",
  "description": "Design and implement a relational database schema",
  "type": "PROJECT",
  "dueDate": "2024-03-15T23:59:59Z",
  "maxScore": 100,
  "weight": 0.30,
  "instructions": "Detailed assignment instructions...",
  "submissionFormat": "PDF",
  "allowLateSubmissions": true,
  "latePenalty": 0.10
}
```

### Submit Assignment
Submit student work for an assignment.

```http
POST /assignments/{assignmentId}/submissions
```

**Request Body (multipart/form-data):**
- `studentId`: Student identifier
- `submissionFile`: Assignment file upload
- `comments`: Optional student comments

### Grade Assignment Submission
Grade a submitted assignment with detailed feedback.

```http
PUT /assignments/{assignmentId}/submissions/{submissionId}/grade
```

**Request Body:**
```json
{
  "score": 88,
  "feedback": "Excellent work on the database schema design. Consider optimizing the indexing strategy for better performance.",
  "rubricScores": {
    "technical_accuracy": 9,
    "documentation": 8,
    "creativity": 9,
    "presentation": 8
  },
  "gradedBy": "instructor-id-123",
  "gradedAt": "2024-03-20T15:30:00Z"
}
```

## Learning Analytics APIs

### Student Performance Analytics
Get comprehensive analytics for student performance and engagement.

```http
GET /students/{studentId}/analytics
```

**Response:**
```json
{
  "performance": {
    "overallGPA": 3.75,
    "trendDirection": "IMPROVING",
    "strengthAreas": ["Programming", "Mathematics"],
    "improvementAreas": ["Writing", "Presentation"],
    "riskLevel": "LOW"
  },
  "engagement": {
    "loginFrequency": "DAILY",
    "assignmentSubmissionRate": 0.95,
    "forumParticipation": "ACTIVE",
    "officeHoursAttendance": 3
  },
  "predictions": {
    "semesterGPA": 3.8,
    "graduationProbability": 0.92,
    "recommendedActions": [
      "Continue current study patterns",
      "Consider advanced courses in programming"
    ]
  }
}
```

### Course Performance Analytics
Analyze performance across an entire course.

```http
GET /courses/{courseId}/analytics
```

## Communication APIs

### Send Notification
Send notifications to students, parents, or instructors.

```http
POST /notifications/send
```

**Request Body:**
```json
{
  "recipientType": "STUDENT",
  "recipientIds": ["STU2024001234"],
  "type": "GRADE_POSTED",
  "subject": "New Grade Posted - CS101",
  "message": "Your midterm exam grade has been posted.",
  "priority": "NORMAL",
  "channels": ["EMAIL", "IN_APP"]
}
```

### Get Student Messages
Retrieve messages and announcements for a student.

```http
GET /students/{studentId}/messages
```

## Schedule Management APIs

### Get Student Schedule
Retrieve class schedule for a student.

```http
GET /students/{studentId}/schedule
```

**Query Parameters:**
- `semester`: Specific semester (default: current)
- `week`: Specific week filter
- `format`: Response format ("weekly", "daily", "full")

### Check Schedule Conflicts
Validate potential schedule conflicts before enrollment.

```http
POST /schedule/conflicts
```

**Request Body:**
```json
{
  "studentId": "STU2024001234",
  "courseIds": ["CS101", "MATH201", "ENG102"],
  "semester": "Fall 2024"
}
```

## Error Handling

### Standard Error Response Format
```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid student enrollment data",
    "details": {
      "field": "grade",
      "reason": "Grade must be between 1 and 12"
    },
    "timestamp": "2024-01-15T10:30:00Z",
    "requestId": "req-12345"
  }
}
```

### Common Error Codes
- `STUDENT_NOT_FOUND`: Student record not found
- `COURSE_FULL`: Course enrollment capacity reached
- `PREREQUISITE_NOT_MET`: Course prerequisites not satisfied
- `GRADE_ALREADY_SUBMITTED`: Duplicate grade submission
- `INVALID_ENROLLMENT_PERIOD`: Outside enrollment window
- `AUTHENTICATION_REQUIRED`: Valid JWT token required
- `INSUFFICIENT_PERMISSIONS`: User lacks required permissions

## Rate Limiting
- **Standard endpoints**: 1000 requests per hour per user
- **Analytics endpoints**: 100 requests per hour per user
- **File upload endpoints**: 10 uploads per minute per user

## Webhooks

### Supported Events
- `student.enrolled`: Student enrolled in course
- `student.withdrawn`: Student withdrawn from course
- `grade.posted`: New grade posted
- `assignment.submitted`: Assignment submitted
- `attendance.recorded`: Attendance recorded

### Webhook Payload Example
```json
{
  "eventType": "grade.posted",
  "eventId": "evt-123abc",
  "timestamp": "2024-01-15T10:30:00Z",
  "data": {
    "studentId": "STU2024001234",
    "courseId": "CS101",
    "assignmentId": "assignment-456",
    "grade": 88,
    "instructor": "instructor-id-123"
  }
}
```
