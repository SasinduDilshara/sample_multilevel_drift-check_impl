/**
 * Learning Management System (LMS) Service
 * 
 * This service provides comprehensive learning management functionality including
 * student enrollment, course management, assignment tracking, grade calculation,
 * and learning analytics. Built with TypeScript, Express.js, and MongoDB.
 * 
 * Features:
 * - Student information system with comprehensive profiles
 * - Course catalog and enrollment management
 * - Assignment creation, submission, and grading workflows
 * - Real-time grade calculations and GPA tracking
 * - Learning analytics and performance insights
 * - Parent portal for K-12 students
 * - Integration with external educational tools
 * 
 * @author Education Platform Development Team
 * @version 2.0.0
 * @since 1.0.0
 */

import express, { Request, Response, NextFunction } from 'express';
import mongoose, { Document, Schema, Model } from 'mongoose';
import bcrypt from 'bcryptjs';
import jwt from 'jsonwebtoken';
import multer from 'multer';
import nodemailer from 'nodemailer';
import { v4 as uuidv4 } from 'uuid';
import rateLimit from 'express-rate-limit';
import helmet from 'helmet';
import cors from 'cors';
import compression from 'compression';

// Environment configuration with production defaults
const PORT = process.env.PORT || 3000;
const MONGODB_URI = process.env.MONGODB_URI || 'mongodb://localhost:27017/education_platform';
const JWT_SECRET = process.env.JWT_SECRET || 'your-secret-key';
const SMTP_CONFIG = {
  host: process.env.SMTP_HOST || 'localhost',
  port: parseInt(process.env.SMTP_PORT || '587'),
  auth: {
    user: process.env.SMTP_USER || 'noreply@eduplatform.edu',
    pass: process.env.SMTP_PASS || 'password'
  }
};

// Express application setup with security middleware
const app = express();

// Security and performance middleware
app.use(helmet()); // Security headers
app.use(cors()); // Cross-origin resource sharing
app.use(compression()); // Response compression
app.use(express.json({ limit: '10mb' })); // JSON parsing with size limit
app.use(express.urlencoded({ extended: true }));

// Rate limiting configuration
const limiter = rateLimit({
  windowMs: 15 * 60 * 1000, // 15 minutes
  max: 1000, // Limit each IP to 1000 requests per windowMs
  message: 'Too many requests from this IP, please try again later.'
});
app.use('/api/', limiter);

// Student interface definition with comprehensive academic information
interface IStudent extends Document {
  studentId: string;
  firstName: string;
  lastName: string;
  email: string;
  passwordHash: string;
  dateOfBirth: Date;
  grade: string;
  program: string;
  enrollmentStatus: 'ACTIVE' | 'INACTIVE' | 'GRADUATED' | 'TRANSFERRED';
  enrollmentDate: Date;
  expectedGraduation: Date;
  parentContact?: {
    name: string;
    email: string;
    phone: string;
    relationship: string;
  };
  academicRecord: {
    currentGPA: number;
    cumulativeGPA: number;
    totalCredits: number;
    completedCourses: number;
    academicStanding: 'GOOD' | 'PROBATION' | 'SUSPENSION';
    honorsStatus?: string;
  };
  personalInfo: {
    address: string;
    phone: string;
    emergencyContact: string;
    medicalAlerts?: string[];
    specialNeeds?: string;
  };
  preferences: {
    learningStyle: string;
    communicationPreference: 'EMAIL' | 'SMS' | 'APP';
    languagePreference: string;
    timezone: string;
  };
  enrolledCourses: mongoose.Types.ObjectId[];
  createdAt: Date;
  updatedAt: Date;
  lastLogin?: Date;
}

// Course interface with comprehensive academic information
interface ICourse extends Document {
  courseId: string;
  title: string;
  description: string;
  department: string;
  level: 'UNDERGRADUATE' | 'GRADUATE' | 'CONTINUING_ED';
  credits: number;
  prerequisites: string[];
  corequisites: string[];
  instructor: {
    id: mongoose.Types.ObjectId;
    name: string;
    email: string;
    officeHours: string;
    officeLocation: string;
  };
  schedule: {
    days: string[];
    startTime: string;
    endTime: string;
    location: string;
    format: 'IN_PERSON' | 'ONLINE' | 'HYBRID';
  };
  enrollment: {
    capacity: number;
    enrolled: number;
    waitlist: number;
    enrollmentDeadline: Date;
    withdrawalDeadline: Date;
  };
  syllabus: {
    objectives: string[];
    topics: string[];
    textbooks: string[];
    gradingPolicy: string;
    attendancePolicy: string;
  };
  semester: string;
  academicYear: string;
  isActive: boolean;
  createdAt: Date;
  updatedAt: Date;
}

// Assignment interface with detailed grading criteria
interface IAssignment extends Document {
  assignmentId: string;
  courseId: mongoose.Types.ObjectId;
  title: string;
  description: string;
  type: 'HOMEWORK' | 'QUIZ' | 'EXAM' | 'PROJECT' | 'DISCUSSION' | 'LAB';
  instructions: string;
  dueDate: Date;
  availableFrom: Date;
  maxScore: number;
  weight: number; // Weight in final grade calculation
  submissionFormat: string[];
  allowLateSubmissions: boolean;
  latePenalty: number; // Percentage penalty per day
  gradingRubric: {
    criteria: string;
    points: number;
    description: string;
  }[];
  isPublished: boolean;
  createdBy: mongoose.Types.ObjectId;
  createdAt: Date;
  updatedAt: Date;
}

// Grade interface with comprehensive tracking
interface IGrade extends Document {
  studentId: mongoose.Types.ObjectId;
  courseId: mongoose.Types.ObjectId;
  assignmentId: mongoose.Types.ObjectId;
  score: number;
  maxScore: number;
  percentage: number;
  letterGrade: string;
  feedback: string;
  rubricScores: {
    criteria: string;
    score: number;
    maxScore: number;
    feedback: string;
  }[];
  submissionDate: Date;
  gradedDate: Date;
  gradedBy: mongoose.Types.ObjectId;
  isExcused: boolean;
  isLate: boolean;
  lateDays: number;
  attempts: number;
  extraCredit: number;
  createdAt: Date;
  updatedAt: Date;
}

// Mongoose schema definitions with comprehensive validation
const StudentSchema = new Schema<IStudent>({
  studentId: { type: String, required: true, unique: true, index: true },
  firstName: { type: String, required: true, trim: true },
  lastName: { type: String, required: true, trim: true },
  email: { type: String, required: true, unique: true, lowercase: true },
  passwordHash: { type: String, required: true },
  dateOfBirth: { type: Date, required: true },
  grade: { type: String, required: true },
  program: { type: String, required: true },
  enrollmentStatus: { 
    type: String, 
    enum: ['ACTIVE', 'INACTIVE', 'GRADUATED', 'TRANSFERRED'],
    default: 'ACTIVE'
  },
  enrollmentDate: { type: Date, default: Date.now },
  expectedGraduation: Date,
  parentContact: {
    name: String,
    email: String,
    phone: String,
    relationship: String
  },
  academicRecord: {
    currentGPA: { type: Number, default: 0.0, min: 0, max: 4.0 },
    cumulativeGPA: { type: Number, default: 0.0, min: 0, max: 4.0 },
    totalCredits: { type: Number, default: 0 },
    completedCourses: { type: Number, default: 0 },
    academicStanding: {
      type: String,
      enum: ['GOOD', 'PROBATION', 'SUSPENSION'],
      default: 'GOOD'
    },
    honorsStatus: String
  },
  personalInfo: {
    address: String,
    phone: String,
    emergencyContact: String,
    medicalAlerts: [String],
    specialNeeds: String
  },
  preferences: {
    learningStyle: { type: String, default: 'VISUAL' },
    communicationPreference: {
      type: String,
      enum: ['EMAIL', 'SMS', 'APP'],
      default: 'EMAIL'
    },
    languagePreference: { type: String, default: 'en' },
    timezone: { type: String, default: 'America/New_York' }
  },
  enrolledCourses: [{ type: Schema.Types.ObjectId, ref: 'Course' }],
  lastLogin: Date
}, {
  timestamps: true,
  collection: 'students'
});

const CourseSchema = new Schema<ICourse>({
  courseId: { type: String, required: true, unique: true, uppercase: true },
  title: { type: String, required: true, trim: true },
  description: { type: String, required: true },
  department: { type: String, required: true, index: true },
  level: {
    type: String,
    enum: ['UNDERGRADUATE', 'GRADUATE', 'CONTINUING_ED'],
    required: true
  },
  credits: { type: Number, required: true, min: 0, max: 6 },
  prerequisites: [String],
  corequisites: [String],
  instructor: {
    id: { type: Schema.Types.ObjectId, ref: 'Instructor' },
    name: { type: String, required: true },
    email: { type: String, required: true },
    officeHours: String,
    officeLocation: String
  },
  schedule: {
    days: [String],
    startTime: String,
    endTime: String,
    location: String,
    format: {
      type: String,
      enum: ['IN_PERSON', 'ONLINE', 'HYBRID'],
      default: 'IN_PERSON'
    }
  },
  enrollment: {
    capacity: { type: Number, required: true, min: 1 },
    enrolled: { type: Number, default: 0 },
    waitlist: { type: Number, default: 0 },
    enrollmentDeadline: Date,
    withdrawalDeadline: Date
  },
  syllabus: {
    objectives: [String],
    topics: [String],
    textbooks: [String],
    gradingPolicy: String,
    attendancePolicy: String
  },
  semester: { type: String, required: true },
  academicYear: { type: String, required: true },
  isActive: { type: Boolean, default: true }
}, {
  timestamps: true,
  collection: 'courses'
});

const AssignmentSchema = new Schema<IAssignment>({
  assignmentId: { type: String, required: true, unique: true },
  courseId: { type: Schema.Types.ObjectId, ref: 'Course', required: true },
  title: { type: String, required: true, trim: true },
  description: { type: String, required: true },
  type: {
    type: String,
    enum: ['HOMEWORK', 'QUIZ', 'EXAM', 'PROJECT', 'DISCUSSION', 'LAB'],
    required: true
  },
  instructions: String,
  dueDate: { type: Date, required: true },
  availableFrom: { type: Date, default: Date.now },
  maxScore: { type: Number, required: true, min: 0 },
  weight: { type: Number, required: true, min: 0, max: 1 },
  submissionFormat: [String],
  allowLateSubmissions: { type: Boolean, default: true },
  latePenalty: { type: Number, default: 0.1, min: 0, max: 1 },
  gradingRubric: [{
    criteria: String,
    points: Number,
    description: String
  }],
  isPublished: { type: Boolean, default: false },
  createdBy: { type: Schema.Types.ObjectId, ref: 'Instructor', required: true }
}, {
  timestamps: true,
  collection: 'assignments'
});

const GradeSchema = new Schema<IGrade>({
  studentId: { type: Schema.Types.ObjectId, ref: 'Student', required: true },
  courseId: { type: Schema.Types.ObjectId, ref: 'Course', required: true },
  assignmentId: { type: Schema.Types.ObjectId, ref: 'Assignment', required: true },
  score: { type: Number, required: true, min: 0 },
  maxScore: { type: Number, required: true, min: 0 },
  percentage: { type: Number, min: 0, max: 100 },
  letterGrade: String,
  feedback: String,
  rubricScores: [{
    criteria: String,
    score: Number,
    maxScore: Number,
    feedback: String
  }],
  submissionDate: Date,
  gradedDate: Date,
  gradedBy: { type: Schema.Types.ObjectId, ref: 'Instructor' },
  isExcused: { type: Boolean, default: false },
  isLate: { type: Boolean, default: false },
  lateDays: { type: Number, default: 0 },
  attempts: { type: Number, default: 1 },
  extraCredit: { type: Number, default: 0 }
}, {
  timestamps: true,
  collection: 'grades'
});

// Create Mongoose models
const Student: Model<IStudent> = mongoose.model('Student', StudentSchema);
const Course: Model<ICourse> = mongoose.model('Course', CourseSchema);
const Assignment: Model<IAssignment> = mongoose.model('Assignment', AssignmentSchema);
const Grade: Model<IGrade> = mongoose.model('Grade', GradeSchema);

// Authentication middleware for JWT token validation
const authenticateToken = (req: Request, res: Response, next: NextFunction): void => {
  const authHeader = req.headers['authorization'];
  const token = authHeader && authHeader.split(' ')[1];

  if (!token) {
    res.status(401).json({ error: 'Access token required' });
    return;
  }

  jwt.verify(token, JWT_SECRET, (err: any, user: any) => {
    if (err) {
      res.status(403).json({ error: 'Invalid or expired token' });
      return;
    }
    req.user = user;
    next();
  });
};

// Student Management Service Class
class StudentManagementService {
  
  /**
   * Creates a new student record with comprehensive validation and
   * duplicate checking. Generates unique student IDs and initializes
   * academic tracking systems.
   */
  static async createStudent(studentData: Partial<IStudent>): Promise<IStudent> {
    // Generate unique student ID with academic year prefix
    const academicYear = new Date().getFullYear();
    const randomSuffix = Math.floor(Math.random() * 100000).toString().padStart(5, '0');
    const studentId = `STU${academicYear}${randomSuffix}`;
    
    // Hash password for security
    const saltRounds = 12;
    const passwordHash = await bcrypt.hash(studentData.passwordHash || 'defaultPassword', saltRounds);
    
    // Create student with generated fields
    const student = new Student({
      ...studentData,
      studentId,
      passwordHash,
      academicRecord: {
        currentGPA: 0.0,
        cumulativeGPA: 0.0,
        totalCredits: 0,
        completedCourses: 0,
        academicStanding: 'GOOD'
      }
    });
    
    // Validate and save student
    await student.save();
    
    // Send welcome email to student and parent
    await this.sendWelcomeEmail(student);
    
    return student;
  }
  
  /**
   * Retrieves comprehensive student information including academic
   * history, current enrollments, and performance analytics.
   */
  static async getStudentProfile(studentId: string): Promise<IStudent | null> {
    const student = await Student.findOne({ studentId })
      .populate('enrolledCourses')
      .exec();
    
    if (!student) {
      throw new Error('Student not found');
    }
    
    // Calculate current metrics
    await this.updateAcademicMetrics(student);
    
    return student;
  }
  
  /**
   * Enrolls a student in a course with prerequisite validation
   * and capacity checking. Handles waitlist management.
   */
  static async enrollStudentInCourse(studentId: string, courseId: string): Promise<void> {
    const student = await Student.findOne({ studentId });
    const course = await Course.findOne({ courseId });
    
    if (!student || !course) {
      throw new Error('Student or course not found');
    }
    
    // Check prerequisites
    const hasPrerequisites = await this.validatePrerequisites(student, course);
    if (!hasPrerequisites) {
      throw new Error('Prerequisites not met');
    }
    
    // Check course capacity
    if (course.enrollment.enrolled >= course.enrollment.capacity) {
      // Add to waitlist
      course.enrollment.waitlist += 1;
      await course.save();
      throw new Error('Course full - added to waitlist');
    }
    
    // Enroll student
    student.enrolledCourses.push(course._id);
    course.enrollment.enrolled += 1;
    
    await Promise.all([student.save(), course.save()]);
    
    // Send enrollment confirmation
    await this.sendEnrollmentConfirmation(student, course);
  }
  
  /**
   * Calculates and updates student GPA based on completed courses
   * and current semester performance.
   */
  static async calculateGPA(studentId: string): Promise<{ currentGPA: number; cumulativeGPA: number }> {
    const student = await Student.findOne({ studentId });
    if (!student) {
      throw new Error('Student not found');
    }
    
    // Get all grades for the student
    const grades = await Grade.find({ studentId: student._id })
      .populate('courseId')
      .populate('assignmentId');
    
    // Calculate course GPAs
    const courseGPAs = new Map<string, { totalPoints: number; credits: number }>();
    
    for (const grade of grades) {
      const course = grade.courseId as ICourse;
      const assignment = grade.assignmentId as IAssignment;
      
      if (!courseGPAs.has(course.courseId)) {
        courseGPAs.set(course.courseId, { totalPoints: 0, credits: course.credits });
      }
      
      const courseData = courseGPAs.get(course.courseId)!;
      const gradePoints = this.convertToGradePoints(grade.percentage);
      courseData.totalPoints += gradePoints * assignment.weight;
    }
    
    // Calculate overall GPA
    let totalQualityPoints = 0;
    let totalCredits = 0;
    
    for (const [courseId, data] of courseGPAs) {
      totalQualityPoints += data.totalPoints * data.credits;
      totalCredits += data.credits;
    }
    
    const cumulativeGPA = totalCredits > 0 ? totalQualityPoints / totalCredits : 0;
    
    // Update student record
    student.academicRecord.cumulativeGPA = cumulativeGPA;
    student.academicRecord.totalCredits = totalCredits;
    await student.save();
    
    return {
      currentGPA: cumulativeGPA,
      cumulativeGPA: cumulativeGPA
    };
  }
  
  /**
   * Validates course prerequisites for student enrollment
   */
  private static async validatePrerequisites(student: IStudent, course: ICourse): Promise<boolean> {
    if (course.prerequisites.length === 0) {
      return true;
    }
    
    // Get completed courses for student
    const completedGrades = await Grade.find({
      studentId: student._id,
      percentage: { $gte: 60 } // Passing grade
    }).populate('courseId');
    
    const completedCourseIds = completedGrades.map(
      grade => (grade.courseId as ICourse).courseId
    );
    
    // Check if all prerequisites are met
    return course.prerequisites.every(
      prereq => completedCourseIds.includes(prereq)
    );
  }
  
  /**
   * Converts percentage grade to 4.0 GPA scale
   */
  private static convertToGradePoints(percentage: number): number {
    if (percentage >= 97) return 4.0;
    if (percentage >= 93) return 3.7;
    if (percentage >= 90) return 3.3;
    if (percentage >= 87) return 3.0;
    if (percentage >= 83) return 2.7;
    if (percentage >= 80) return 2.3;
    if (percentage >= 77) return 2.0;
    if (percentage >= 73) return 1.7;
    if (percentage >= 70) return 1.3;
    if (percentage >= 67) return 1.0;
    if (percentage >= 65) return 0.7;
    return 0.0;
  }
  
  /**
   * Updates student academic metrics and standing
   */
  private static async updateAcademicMetrics(student: IStudent): Promise<void> {
    const gpaData = await this.calculateGPA(student.studentId);
    
    // Update academic standing based on GPA
    let academicStanding: 'GOOD' | 'PROBATION' | 'SUSPENSION' = 'GOOD';
    if (gpaData.cumulativeGPA < 2.0) {
      academicStanding = 'SUSPENSION';
    } else if (gpaData.cumulativeGPA < 2.5) {
      academicStanding = 'PROBATION';
    }
    
    student.academicRecord.academicStanding = academicStanding;
    await student.save();
  }
  
  /**
   * Sends welcome email to new students
   */
  private static async sendWelcomeEmail(student: IStudent): Promise<void> {
    const transporter = nodemailer.createTransporter(SMTP_CONFIG);
    
    const mailOptions = {
      from: 'noreply@eduplatform.edu',
      to: student.email,
      subject: 'Welcome to Education Platform',
      html: `
        <h1>Welcome ${student.firstName}!</h1>
        <p>Your student ID is: <strong>${student.studentId}</strong></p>
        <p>Please log in to access your courses and assignments.</p>
      `
    };
    
    await transporter.sendMail(mailOptions);
  }
  
  /**
   * Sends enrollment confirmation email
   */
  private static async sendEnrollmentConfirmation(student: IStudent, course: ICourse): Promise<void> {
    const transporter = nodemailer.createTransporter(SMTP_CONFIG);
    
    const mailOptions = {
      from: 'noreply@eduplatform.edu',
      to: student.email,
      subject: `Enrollment Confirmation - ${course.title}`,
      html: `
        <h1>Enrollment Confirmed</h1>
        <p>You have been successfully enrolled in:</p>
        <p><strong>${course.courseId}: ${course.title}</strong></p>
        <p>Instructor: ${course.instructor.name}</p>
        <p>Credits: ${course.credits}</p>
      `
    };
    
    await transporter.sendMail(mailOptions);
  }
}

// REST API Endpoints

/**
 * Create new student profile with comprehensive validation
 */
app.post('/api/v1/students', async (req: Request, res: Response) => {
  try {
    const student = await StudentManagementService.createStudent(req.body);
    
    // Remove sensitive information from response
    const { passwordHash, ...studentResponse } = student.toObject();
    
    res.status(201).json({
      message: 'Student created successfully',
      student: studentResponse
    });
  } catch (error) {
    console.error('Error creating student:', error);
    res.status(400).json({
      error: 'Failed to create student',
      details: error instanceof Error ? error.message : 'Unknown error'
    });
  }
});

/**
 * Get student profile with academic information
 */
app.get('/api/v1/students/:studentId', authenticateToken, async (req: Request, res: Response) => {
  try {
    const student = await StudentManagementService.getStudentProfile(req.params.studentId);
    
    if (!student) {
      res.status(404).json({ error: 'Student not found' });
      return;
    }
    
    // Remove sensitive information
    const { passwordHash, ...studentResponse } = student.toObject();
    
    res.json({ student: studentResponse });
  } catch (error) {
    console.error('Error retrieving student:', error);
    res.status(500).json({ error: 'Failed to retrieve student' });
  }
});

/**
 * Enroll student in course
 */
app.post('/api/v1/students/:studentId/enrollments', authenticateToken, async (req: Request, res: Response) => {
  try {
    const { courseId } = req.body;
    
    await StudentManagementService.enrollStudentInCourse(req.params.studentId, courseId);
    
    res.json({ message: 'Student enrolled successfully' });
  } catch (error) {
    console.error('Error enrolling student:', error);
    res.status(400).json({
      error: 'Failed to enroll student',
      details: error instanceof Error ? error.message : 'Unknown error'
    });
  }
});

/**
 * Calculate student GPA
 */
app.get('/api/v1/students/:studentId/gpa', authenticateToken, async (req: Request, res: Response) => {
  try {
    const gpaData = await StudentManagementService.calculateGPA(req.params.studentId);
    res.json(gpaData);
  } catch (error) {
    console.error('Error calculating GPA:', error);
    res.status(500).json({ error: 'Failed to calculate GPA' });
  }
});

// Database connection and server startup
mongoose.connect(MONGODB_URI)
  .then(() => {
    console.log('Connected to MongoDB');
    
    app.listen(PORT, () => {
      console.log(`Education Platform LMS running on port ${PORT}`);
      console.log(`Environment: ${process.env.NODE_ENV || 'development'}`);
    });
  })
  .catch((error) => {
    console.error('Database connection error:', error);
    process.exit(1);
  });

// Export for testing
export { app, StudentManagementService };
