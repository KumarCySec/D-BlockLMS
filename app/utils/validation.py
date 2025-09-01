"""
Validation utilities using Marshmallow
"""
from marshmallow import Schema, fields, validate, ValidationError
from app.models.user import User


class UserRegistrationSchema(Schema):
    """Schema for user registration validation"""
    name = fields.Str(
        required=True,
        validate=validate.Length(min=2, max=100),
        error_messages={
            'required': 'Full name is required',
            'invalid': 'Name must be a valid string',
            'validator_failed': 'Name must be between 2 and 100 characters'
        }
    )
    
    roll_number = fields.Str(
        required=True,
        validate=validate.Length(min=3, max=20),
        error_messages={
            'required': 'Roll number is required',
            'invalid': 'Roll number must be a valid string',
            'validator_failed': 'Roll number must be between 3 and 20 characters'
        }
    )
    
    branch = fields.Str(
        required=True,
        validate=validate.OneOf([
            'CSE', 'ECE', 'EEE', 'Civil', 'Automobile', 'Mechanical', 'IT',
            'Computer Science', 'Electronics', 'Electrical'
        ]),
        error_messages={
            'required': 'Branch is required',
            'invalid': 'Branch must be a valid string',
            'validator_failed': 'Please select a valid branch'
        }
    )
    
    batch = fields.Str(
        required=True,
        validate=validate.Length(min=4, max=10),
        error_messages={
            'required': 'Batch is required',
            'invalid': 'Batch must be a valid string',
            'validator_failed': 'Batch must be between 4 and 10 characters (e.g., 2021-2025)'
        }
    )
    
    phone = fields.Str(
        required=True,
        validate=validate.Regexp(
            r'^\d{10}$',
            error='Phone number must be exactly 10 digits'
        ),
        error_messages={
            'required': 'Phone number is required',
            'invalid': 'Phone number must be a valid string'
        }
    )
    
    email = fields.Email(
        required=True,
        error_messages={
            'required': 'Email address is required',
            'invalid': 'Please provide a valid email address'
        }
    )
    
    password = fields.Str(
        required=True,
        validate=validate.Length(min=6, max=128),
        error_messages={
            'required': 'Password is required',
            'invalid': 'Password must be a valid string',
            'validator_failed': 'Password must be at least 6 characters long'
        }
    )
    
    confirm_password = fields.Str(
        required=True,
        error_messages={
            'required': 'Password confirmation is required',
            'invalid': 'Password confirmation must be a valid string'
        }
    )
    
    def validate_email_unique(self, value):
        """Validate email is unique"""
        if User.get_by_email(value):
            raise ValidationError('This email address is already registered')
    
    def validate_roll_number_unique(self, value):
        """Validate roll number is unique"""
        if User.get_by_roll_number(value):
            raise ValidationError('This roll number is already registered')
    
    def validate_passwords_match(self, data, **kwargs):
        """Validate passwords match"""
        if data.get('password') != data.get('confirm_password'):
            raise ValidationError('Passwords do not match', field_name='confirm_password')


class UserLoginSchema(Schema):
    """Schema for user login validation"""
    email = fields.Email(
        required=True,
        error_messages={
            'required': 'Email address is required',
            'invalid': 'Please provide a valid email address'
        }
    )
    
    password = fields.Str(
        required=True,
        error_messages={
            'required': 'Password is required',
            'invalid': 'Password must be a valid string'
        }
    )


class APIErrorFormatter:
    """Format validation errors for API responses"""
    
    @staticmethod
    def format_marshmallow_errors(errors):
        """Format Marshmallow validation errors"""
        formatted_errors = {}
        
        for field, messages in errors.items():
            if isinstance(messages, list):
                formatted_errors[field] = messages[0]  # Take first error message
            else:
                formatted_errors[field] = str(messages)
        
        return formatted_errors
    
    @staticmethod
    def create_validation_response(errors):
        """Create standardized validation error response"""
        return {
            'success': False,
            'message': 'Validation failed',
            'error': {
                'code': 'VALIDATION_ERROR',
                'details': APIErrorFormatter.format_marshmallow_errors(errors)
            }
        }


def validate_registration_data(data):
    """Validate user registration data"""
    schema = UserRegistrationSchema()
    
    try:
        # Validate basic fields
        result = schema.load(data)
        
        # Additional validations
        schema.validate_email_unique(data.get('email'))
        schema.validate_roll_number_unique(data.get('roll_number'))
        schema.validate_passwords_match(data)
        
        return result, None
        
    except ValidationError as err:
        return None, err.messages


def validate_login_data(data):
    """Validate user login data"""
    schema = UserLoginSchema()
    
    try:
        result = schema.load(data)
        return result, None
        
    except ValidationError as err:
        return None, err.messages