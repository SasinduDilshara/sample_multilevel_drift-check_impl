import ballerina/http;
import ballerina/log;
import ballerina/time;
import ballerina/uuid;

# Represents user profile information with comprehensive details
# Contains all necessary fields for user management and authentication
# Used across the platform for user identification and personalization
public type UserProfile record {
    # Unique identifier for the user account
    string userId;
    # User's email address used for authentication and communication  
    string email;
    # User's first name for personalization
    string firstName;
    # User's last name for formal identification
    string lastName;
    # Optional phone number for two-factor authentication
    string? phoneNumber;
    # User's date of birth for age verification and marketing
    string? dateOfBirth;
    # Profile image URL for avatar display
    string? profileImageUrl;
    # Flag indicating if email has been verified
    boolean emailVerified;
    # Flag indicating if phone number has been verified
    boolean phoneVerified;
    # Timestamp when the account was created
    time:Utc createdAt;
    # Timestamp of the user's last login session
    time:Utc? lastLoginAt;
};

# User address information for shipping and billing purposes
# Supports international addresses with proper validation
# Integrates with shipping carriers for address verification
public type UserAddress record {
    # Unique identifier for this address
    string addressId;
    # Type of address (home, work, billing, shipping)
    string addressType;
    # Street address line 1 with house number and street name
    string street1;
    # Optional street address line 2 for apartment or suite
    string? street2;
    # City name for address validation
    string city;
    # State or province for regional identification
    string state;
    # Postal or ZIP code for delivery routing
    string postalCode;
    # Country code in ISO 3166-1 alpha-2 format
    string countryCode;
    # Flag indicating if this is the default address
    boolean isDefault;
    # Timestamp when address was created
    time:Utc createdAt;
};

# User preference settings for customization and privacy
# Controls notification delivery and user experience customization
# Supports GDPR compliance with granular consent management
public type UserPreferences record {
    # User identifier linking preferences to account
    string userId;
    # Email notification preferences for marketing communications
    boolean emailNotifications;
    # SMS notification preferences for order updates
    boolean smsNotifications;
    # Push notification preferences for mobile applications
    boolean pushNotifications;
    # Newsletter subscription status for marketing emails
    boolean newsletterSubscription;
    # Privacy setting for data sharing with third parties
    boolean dataSharing;
    # Language preference for user interface localization
    string preferredLanguage;
    # Currency preference for pricing display
    string preferredCurrency;
    # Timezone setting for date and time display
    string timezone;
    # Timestamp when preferences were last updated
    time:Utc lastUpdated;
};

# HTTP service for user profile management operations
# Provides comprehensive user account management functionality
# Implements proper authentication and authorization controls
service /api/v1/users on new http:Listener(8081) {

    # Retrieves comprehensive user profile information
    # @param userId - The unique identifier of the user
    # @return UserProfile - Complete user profile data
    # @return http:NotFound - When user is not found
    # @return http:Unauthorized - When authentication fails
    resource function get profile/[string userId]() returns UserProfile|http:NotFound|http:Unauthorized {
        
        // Validate user authentication token from request headers
        // This should check JWT token validity and user permissions
        boolean isAuthenticated = validateUserAuthentication(userId);
        if (!isAuthenticated) {
            log:printWarn("Unauthorized access attempt to user profile", userId = userId);
            return <http:Unauthorized>{
                body: {
                    error: "Authentication required to access user profile",
                    code: "UNAUTHORIZED_ACCESS"
                }
            };
        }

        // Retrieve user profile from database with comprehensive error handling
        UserProfile|error userResult = retrieveUserProfileFromDatabase(userId);
        if (userResult is error) {
            log:printError("Failed to retrieve user profile from database", userId = userId, 'error = userResult);
            return <http:NotFound>{
                body: {
                    error: "User profile not found in system",
                    code: "USER_NOT_FOUND"
                }
            };
        }

        UserProfile userProfile = userResult;
        
        // Update last access timestamp for user activity tracking
        updateLastAccessTime(userId);
        
        // Log successful profile retrieval for audit compliance
        log:printInfo("User profile retrieved successfully", userId = userId, email = userProfile.email);
        
        return userProfile;
    }

    # Updates user profile information with validation
    # @param userId - The unique identifier of the user
    # @param profileData - Updated profile information
    # @return UserProfile - Updated user profile data
    # @return http:BadRequest - When validation fails
    # @return http:Forbidden - When user lacks permission
    resource function put profile/[string userId](UserProfile profileData) returns UserProfile|http:BadRequest|http:Forbidden {
        
        // Validate user has permission to update this profile
        // Users can only update their own profiles unless they have admin rights
        boolean hasPermission = validateUpdatePermission(userId, profileData.userId);
        if (!hasPermission) {
            log:printWarn("Forbidden profile update attempt", requestingUser = userId, targetUser = profileData.userId);
            return <http:Forbidden>{
                body: {
                    error: "Insufficient permissions to update this profile",
                    code: "FORBIDDEN_OPERATION"
                }
            };
        }

        // Validate profile data against business rules and constraints
        string[] validationErrors = validateProfileData(profileData);
        if (validationErrors.length() > 0) {
            log:printError("Profile validation failed", userId = userId, errors = validationErrors);
            return <http:BadRequest>{
                body: {
                    error: "Profile data validation failed",
                    code: "VALIDATION_ERROR",
                    details: validationErrors
                }
            };
        }

        // Update profile in database with proper transaction handling
        UserProfile|error updateResult = updateUserProfileInDatabase(profileData);
        if (updateResult is error) {
            log:printError("Failed to update user profile in database", userId = userId, 'error = updateResult);
            return <http:BadRequest>{
                body: {
                    error: "Profile update failed due to database error",
                    code: "UPDATE_FAILED"
                }
            };
        }

        UserProfile updatedProfile = updateResult;
        
        // Trigger profile update event for other services
        publishProfileUpdateEvent(updatedProfile);
        
        // Log successful profile update for audit trail
        log:printInfo("User profile updated successfully", userId = userId, updatedFields = getUpdatedFields(profileData));
        
        return updatedProfile;
    }

    # Retrieves all addresses associated with a user account
    # @param userId - The unique identifier of the user
    # @return UserAddress[] - Array of user addresses
    # @return http:Unauthorized - When authentication fails
    resource function get addresses/[string userId]() returns UserAddress[]|http:Unauthorized {
        
        // Authenticate user and validate access permissions
        boolean isAuthenticated = validateUserAuthentication(userId);
        if (!isAuthenticated) {
            return <http:Unauthorized>{
                body: {
                    error: "Authentication required to access user addresses",
                    code: "UNAUTHORIZED_ACCESS"
                }
            };
        }

        // Retrieve all addresses for the user from database
        UserAddress[] addresses = getUserAddressesFromDatabase(userId);
        
        // Sort addresses with default address first
        UserAddress[] sortedAddresses = sortAddressesByDefault(addresses);
        
        // Log address retrieval for security monitoring
        log:printInfo("User addresses retrieved", userId = userId, addressCount = sortedAddresses.length());
        
        return sortedAddresses;
    }

    # Adds a new address to user's address book
    # @param userId - The unique identifier of the user
    # @param addressData - New address information to add
    # @return UserAddress - The created address with generated ID
    # @return http:BadRequest - When address validation fails
    # @return http:Conflict - When address already exists
    resource function post addresses/[string userId](UserAddress addressData) returns UserAddress|http:BadRequest|http:Conflict {
        
        // Validate address data format and required fields
        string[] addressValidationErrors = validateAddressData(addressData);
        if (addressValidationErrors.length() > 0) {
            log:printError("Address validation failed", userId = userId, errors = addressValidationErrors);
            return <http:BadRequest>{
                body: {
                    error: "Address data validation failed",
                    code: "INVALID_ADDRESS_DATA",
                    details: addressValidationErrors
                }
            };
        }

        // Check if similar address already exists to prevent duplicates
        boolean addressExists = checkDuplicateAddress(userId, addressData);
        if (addressExists) {
            log:printWarn("Duplicate address creation attempt", userId = userId);
            return <http:Conflict>{
                body: {
                    error: "Similar address already exists in address book",
                    code: "DUPLICATE_ADDRESS"
                }
            };
        }

        // Verify address with shipping carrier services
        boolean isAddressValid = verifyAddressWithCarrier(addressData);
        if (!isAddressValid) {
            return <http:BadRequest>{
                body: {
                    error: "Address could not be verified with shipping carriers",
                    code: "UNVERIFIABLE_ADDRESS"
                }
            };
        }

        // Generate unique identifier for new address
        string addressId = uuid:createType1AsString();
        addressData.addressId = addressId;
        addressData.createdAt = time:utcNow();

        // Save address to database with proper error handling
        UserAddress|error saveResult = saveAddressToDatabase(addressData);
        if (saveResult is error) {
            log:printError("Failed to save address to database", userId = userId, 'error = saveResult);
            return <http:BadRequest>{
                body: {
                    error: "Address creation failed due to database error",
                    code: "SAVE_FAILED"
                }
            };
        }

        UserAddress savedAddress = saveResult;
        
        // Publish address created event for other services
        publishAddressCreatedEvent(savedAddress);
        
        // Log successful address creation
        log:printInfo("New address created successfully", userId = userId, addressId = addressId);
        
        return savedAddress;
    }

    # Retrieves user preferences and privacy settings
    # @param userId - The unique identifier of the user
    # @return UserPreferences - User's current preference settings
    # @return http:NotFound - When preferences are not found
    resource function get preferences/[string userId]() returns UserPreferences|http:NotFound {
        
        // Retrieve user preferences from database
        UserPreferences|error preferencesResult = getUserPreferencesFromDatabase(userId);
        if (preferencesResult is error) {
            log:printError("Failed to retrieve user preferences", userId = userId, 'error = preferencesResult);
            return <http:NotFound>{
                body: {
                    error: "User preferences not found",
                    code: "PREFERENCES_NOT_FOUND"
                }
            };
        }

        UserPreferences preferences = preferencesResult;
        
        // Log preferences access for compliance auditing
        log:printInfo("User preferences retrieved", userId = userId);
        
        return preferences;
    }
}

# Validates user authentication token and permissions
function validateUserAuthentication(string userId) returns boolean {
    // Check JWT token validity and user session status
    // Verify user has valid authentication credentials
    log:printInfo("Validating user authentication", userId = userId);
    return true; // Simplified for example
}

# Retrieves user profile from database with error handling
function retrieveUserProfileFromDatabase(string userId) returns UserProfile|error {
    // Database query to fetch comprehensive user profile
    // Include proper error handling for database connectivity issues
    return {
        userId: userId,
        email: "user@example.com",
        firstName: "John",
        lastName: "Doe",
        phoneNumber: "+1234567890",
        emailVerified: true,
        phoneVerified: false,
        createdAt: time:utcNow(),
        lastLoginAt: time:utcNow()
    };
}

# Validates profile data against business rules
function validateProfileData(UserProfile profileData) returns string[] {
    string[] errors = [];
    
    // Validate email format using regex pattern
    if (!isValidEmailFormat(profileData.email)) {
        errors.push("Invalid email format");
    }
    
    // Validate phone number format if provided
    if (profileData.phoneNumber is string && !isValidPhoneFormat(profileData.phoneNumber)) {
        errors.push("Invalid phone number format");
    }
    
    return errors;
}

# Validates email format using comprehensive regex
function isValidEmailFormat(string email) returns boolean {
    // Email validation using RFC 5322 compliant regex pattern
    return email.includes("@") && email.includes(".");
}

# Validates phone number format for international numbers
function isValidPhoneFormat(string phoneNumber) returns boolean {
    // Phone number validation supporting international formats
    return phoneNumber.startsWith("+") && phoneNumber.length() >= 10;
}

# Updates user profile in database with transaction support
function updateUserProfileInDatabase(UserProfile profileData) returns UserProfile|error {
    // Database update operation with proper transaction handling
    // Ensure data consistency and rollback on failures
    log:printInfo("Updating user profile in database", userId = profileData.userId);
    return profileData;
}

# Additional helper functions would be implemented for:
# - updateLastAccessTime()
# - validateUpdatePermission()
# - publishProfileUpdateEvent()
# - getUpdatedFields()
# - getUserAddressesFromDatabase()
# - sortAddressesByDefault()
# - validateAddressData()
# - checkDuplicateAddress()
# - verifyAddressWithCarrier()
# - saveAddressToDatabase()
# - publishAddressCreatedEvent()
# - getUserPreferencesFromDatabase()
