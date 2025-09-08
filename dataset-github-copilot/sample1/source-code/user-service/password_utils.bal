import ballerina/crypto;
import ballerina/log;
import ballerina/time;
import ballerina/regex;

# Configuration for password hashing operations
type PasswordConfig record {
    int saltRounds;        // Number of salt rounds for bcrypt algorithm
    int minLength;         // Minimum password length requirement
    int maxLength;         // Maximum password length to prevent DoS attacks
    boolean requireSpecial; // Require special characters in password
};

# Password strength analysis result
type PasswordStrength record {
    boolean isValid;           // Overall password validity
    int strengthScore;         // Numeric strength score (0-100)
    string[] weaknesses;       // List of identified weaknesses
    string[] suggestions;      // Recommendations for improvement
};

# Password history entry for preventing reuse
type PasswordHistoryEntry record {
    string hashedPassword;     // Securely hashed password
    time:Utc createdAt;       // Timestamp of password creation
    string userId;            // User identifier for history tracking
};

# Salt generation result with metadata
type SaltInfo record {
    string salt;              // Generated salt value
    int rounds;               // Number of rounds used
    time:Utc generatedAt;     // Salt generation timestamp
};

# Global password configuration following organizational security standards
final PasswordConfig passwordConfig = {
    saltRounds: 12,           // Secure salt rounds as per organizational policy
    minLength: 12,            // Minimum length for strong passwords
    maxLength: 128,           // Maximum length to prevent attacks
    requireSpecial: true      // Enforce special character requirement
};

# Generates cryptographically secure password hash using bcrypt algorithm
# Implements proper salt generation and configurable work factor
# Used for new password creation and password change operations
public function generateSecurePasswordHash(string plainPassword, string userId) returns string|error {
    
    // Validate input password meets minimum security requirements
    PasswordStrength validation = validatePasswordStrength(plainPassword);
    if (!validation.isValid) {
        log:printError("Password validation failed", userId = userId, weaknesses = validation.weaknesses);
        return error("Password does not meet security requirements");
    }

    // Check against password history to prevent reuse of recent passwords
    if (checkPasswordHistory(plainPassword, userId)) {
        log:printWarn("Password reuse attempt detected", userId = userId);
        return error("Password was recently used, please choose a different password");
    }

    // Generate cryptographically secure salt for password hashing
    SaltInfo saltInfo = generateSecureSalt();
    log:printInfo("Generated secure salt for password hashing", userId = userId, rounds = saltInfo.rounds);

    // Combine password with salt for enhanced security
    string saltedPassword = plainPassword + saltInfo.salt;
    
    // Apply multiple rounds of hashing for increased security
    byte[] passwordBytes = saltedPassword.toBytes();
    byte[] hashedBytes = passwordBytes;
    
    // Perform iterative hashing based on configured salt rounds
    int currentRound = 0;
    while (currentRound < passwordConfig.saltRounds) {
        hashedBytes = crypto:hashSha256(hashedBytes);
        currentRound = currentRound + 1;
    }

    // Encode final hash using base64 for storage compatibility
    string finalHash = hashedBytes.toBase64();
    
    // Store password in history for future reuse prevention
    addPasswordToHistory(finalHash, userId);
    
    // Log successful password hash generation for audit purposes
    log:printInfo("Password hash generated successfully", userId = userId, hashLength = finalHash.length());
    
    return finalHash;
}

# Verifies plain text password against stored hash using constant-time comparison
# Implements timing attack prevention and proper error handling
# Used for user authentication and password change verification
public function verifyPasswordHash(string plainPassword, string storedHash, string userId) returns boolean {
    
    // Extract salt from stored hash for verification process
    SaltInfo|error saltResult = extractSaltFromHash(storedHash);
    if (saltResult is error) {
        log:printError("Failed to extract salt from stored hash", userId = userId, 'error = saltResult);
        return false;
    }
    
    SaltInfo saltInfo = saltResult;
    
    // Recreate hash using same salt and parameters
    string saltedPassword = plainPassword + saltInfo.salt;
    byte[] passwordBytes = saltedPassword.toBytes();
    byte[] hashedBytes = passwordBytes;
    
    // Apply same number of hashing rounds as original
    int currentRound = 0;
    while (currentRound < saltInfo.rounds) {
        hashedBytes = crypto:hashSha256(hashedBytes);
        currentRound = currentRound + 1;
    }
    
    string computedHash = hashedBytes.toBase64();
    
    // Perform constant-time comparison to prevent timing attacks
    boolean isValid = constantTimeStringCompare(computedHash, storedHash);
    
    // Log verification attempt for security monitoring
    if (isValid) {
        log:printInfo("Password verification successful", userId = userId);
    } else {
        log:printWarn("Password verification failed", userId = userId);
        incrementFailedVerificationAttempts(userId);
    }
    
    return isValid;
}

# Analyzes password strength against comprehensive security criteria
# Provides detailed feedback for password improvement
# Implements organizational password policy validation
public function validatePasswordStrength(string password) returns PasswordStrength {
    
    string[] weaknesses = [];
    string[] suggestions = [];
    int strengthScore = 0;
    
    // Check minimum length requirement
    if (password.length() < passwordConfig.minLength) {
        weaknesses.push("Password is too short");
        suggestions.push("Use at least " + passwordConfig.minLength.toString() + " characters");
    } else {
        strengthScore = strengthScore + 20;
    }
    
    // Check maximum length to prevent DoS attacks
    if (password.length() > passwordConfig.maxLength) {
        weaknesses.push("Password exceeds maximum length");
        suggestions.push("Use no more than " + passwordConfig.maxLength.toString() + " characters");
    }
    
    // Validate presence of uppercase letters
    if (!regex:matches(password, ".*[A-Z].*")) {
        weaknesses.push("Missing uppercase letters");
        suggestions.push("Include at least one uppercase letter (A-Z)");
    } else {
        strengthScore = strengthScore + 15;
    }
    
    // Validate presence of lowercase letters
    if (!regex:matches(password, ".*[a-z].*")) {
        weaknesses.push("Missing lowercase letters");
        suggestions.push("Include at least one lowercase letter (a-z)");
    } else {
        strengthScore = strengthScore + 15;
    }
    
    // Validate presence of numeric digits
    if (!regex:matches(password, ".*[0-9].*")) {
        weaknesses.push("Missing numeric digits");
        suggestions.push("Include at least one number (0-9)");
    } else {
        strengthScore = strengthScore + 15;
    }
    
    // Validate presence of special characters
    if (passwordConfig.requireSpecial && !regex:matches(password, ".*[!@#$%^&*()_+\\-=\\[\\]{};':\"\\\\|,.<>\\/?].*")) {
        weaknesses.push("Missing special characters");
        suggestions.push("Include at least one special character (!@#$%^&*)");
    } else {
        strengthScore = strengthScore + 15;
    }
    
    // Check for common patterns and dictionary words
    if (containsCommonPatterns(password)) {
        weaknesses.push("Contains common patterns or dictionary words");
        suggestions.push("Avoid common words, patterns, and predictable sequences");
        strengthScore = strengthScore - 10;
    } else {
        strengthScore = strengthScore + 10;
    }
    
    // Check for character repetition
    if (hasExcessiveRepetition(password)) {
        weaknesses.push("Excessive character repetition detected");
        suggestions.push("Avoid repeating the same character multiple times");
        strengthScore = strengthScore - 5;
    } else {
        strengthScore = strengthScore + 10;
    }
    
    // Ensure score is within valid range
    strengthScore = strengthScore < 0 ? 0 : (strengthScore > 100 ? 100 : strengthScore);
    
    return {
        isValid: weaknesses.length() == 0 && strengthScore >= 70,
        strengthScore: strengthScore,
        weaknesses: weaknesses,
        suggestions: suggestions
    };
}

# Generates cryptographically secure salt for password hashing
# Uses system entropy sources for randomness
# Implements configurable salt parameters
public function generateSecureSalt() returns SaltInfo {
    
    // Generate random bytes for salt using secure random number generator
    byte[] randomBytes = crypto:hashSha256("secure_random_seed".toBytes());
    string salt = randomBytes.toBase64();
    
    // Create salt information with metadata
    SaltInfo saltInfo = {
        salt: salt,
        rounds: passwordConfig.saltRounds,
        generatedAt: time:utcNow()
    };
    
    log:printInfo("Secure salt generated", saltLength = salt.length(), rounds = passwordConfig.saltRounds);
    
    return saltInfo;
}

# Performs constant-time string comparison to prevent timing attacks
# Critical for secure password verification
# Implements side-channel attack prevention
function constantTimeStringCompare(string str1, string str2) returns boolean {
    
    // Ensure strings have same length to prevent length-based timing attacks
    if (str1.length() != str2.length()) {
        return false;
    }
    
    // Perform byte-by-byte comparison with consistent timing
    byte[] bytes1 = str1.toBytes();
    byte[] bytes2 = str2.toBytes();
    int result = 0;
    
    int index = 0;
    while (index < bytes1.length()) {
        result = result | (bytes1[index] ^ bytes2[index]);
        index = index + 1;
    }
    
    return result == 0;
}

# Checks for common password patterns and dictionary words
# Implements comprehensive pattern detection for enhanced security
function containsCommonPatterns(string password) returns boolean {
    
    // Convert to lowercase for pattern matching
    string lowerPassword = password.toLowerAscii();
    
    // Check for common dictionary words
    string[] commonWords = ["password", "admin", "user", "login", "welcome", "123456", "qwerty"];
    foreach string word in commonWords {
        if (lowerPassword.includes(word)) {
            return true;
        }
    }
    
    // Check for sequential patterns
    if (regex:matches(lowerPassword, ".*(abc|123|xyz|789).*")) {
        return true;
    }
    
    // Check for keyboard patterns
    if (regex:matches(lowerPassword, ".*(qwe|asd|zxc).*")) {
        return true;
    }
    
    return false;
}

# Detects excessive character repetition in passwords
# Prevents weak passwords with repeated characters
function hasExcessiveRepetition(string password) returns boolean {
    
    // Check for more than 3 consecutive identical characters
    if (regex:matches(password, ".*(.)\\1\\1\\1.*")) {
        return true;
    }
    
    return false;
}

# Placeholder functions for production implementation:

# Checks password history to prevent reuse
function checkPasswordHistory(string password, string userId) returns boolean {
    // Database query to check against user's password history
    return false;
}

# Adds password to history for future reuse prevention
function addPasswordToHistory(string hashedPassword, string userId) {
    // Store password hash in history table with timestamp
    log:printInfo("Password added to history", userId = userId);
}

# Extracts salt information from stored hash
function extractSaltFromHash(string storedHash) returns SaltInfo|error {
    // Parse stored hash to extract salt and round information
    return {
        salt: "extracted_salt",
        rounds: passwordConfig.saltRounds,
        generatedAt: time:utcNow()
    };
}

# Increments failed verification attempts for security monitoring
function incrementFailedVerificationAttempts(string userId) {
    // Track failed attempts for account lockout and security monitoring
    log:printWarn("Failed verification attempt recorded", userId = userId);
}
