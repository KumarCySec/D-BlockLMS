"""
OpenAPI/Swagger documentation setup
"""
from flask import current_app, jsonify
from flask_swagger_ui import get_swaggerui_blueprint


def create_swagger_config():
    """Create OpenAPI specification for the API"""
    return {
        "openapi": "3.0.0",
        "info": {
            "title": "D-Block Library Management System API",
            "description": "RESTful API for managing library inventory, donors, and transactions",
            "version": "1.0.0",
            "contact": {
                "name": "D-Block Library System",
                "email": "admin@dblock-library.com"
            }
        },
        "servers": [
            {
                "url": "/api",
                "description": "API Server"
            }
        ],
        "components": {
            "securitySchemes": {
                "sessionAuth": {
                    "type": "apiKey",
                    "in": "cookie",
                    "name": "session"
                }
            },
            "schemas": {
                "Donor": {
                    "type": "object",
                    "required": ["name", "branch", "batch"],
                    "properties": {
                        "id": {"type": "integer", "readOnly": True},
                        "name": {"type": "string", "maxLength": 100, "example": "John Doe"},
                        "branch": {"type": "string", "maxLength": 50, "example": "CSE"},
                        "batch": {"type": "string", "maxLength": 10, "example": "2020-2024"},
                        "address": {"type": "string", "maxLength": 500, "nullable": True},
                        "phone": {"type": "string", "maxLength": 15, "nullable": True, "example": "9876543210"},
                        "email": {"type": "string", "format": "email", "nullable": True, "example": "john@example.com"},
                        "notes": {"type": "string", "maxLength": 1000, "nullable": True},
                        "created_at": {"type": "string", "format": "date-time", "readOnly": True},
                        "updated_at": {"type": "string", "format": "date-time", "readOnly": True}
                    }
                },
                "InventoryItem": {
                    "type": "object",
                    "required": ["item_type", "title", "donor_id", "date_of_donation", "total_quantity"],
                    "properties": {
                        "id": {"type": "integer", "readOnly": True},
                        "item_type": {"type": "string", "enum": ["book", "laptop", "kit"], "example": "book"},
                        "title": {"type": "string", "maxLength": 200, "example": "Python Programming Guide"},
                        "authors": {"type": "string", "maxLength": 200, "nullable": True, "example": "John Smith"},
                        "language": {"type": "string", "maxLength": 50, "nullable": True, "example": "English"},
                        "published_date": {"type": "string", "format": "date", "nullable": True},
                        "sku_code": {"type": "string", "maxLength": 50, "nullable": True, "example": "BOOK001"},
                        "description": {"type": "string", "maxLength": 1000, "nullable": True},
                        "donor_id": {"type": "integer", "example": 1},
                        "date_of_donation": {"type": "string", "format": "date", "example": "2024-01-01"},
                        "total_quantity": {"type": "integer", "minimum": 1, "example": 5},
                        "available_quantity": {"type": "integer", "readOnly": True, "example": 3},
                        "department_id": {"type": "integer", "nullable": True},
                        "created_at": {"type": "string", "format": "date-time", "readOnly": True},
                        "updated_at": {"type": "string", "format": "date-time", "readOnly": True}
                    }
                },
                "APIResponse": {
                    "type": "object",
                    "properties": {
                        "success": {"type": "boolean"},
                        "message": {"type": "string"},
                        "timestamp": {"type": "string", "format": "date-time"},
                        "data": {"type": "object"}
                    }
                },
                "APIError": {
                    "type": "object",
                    "properties": {
                        "success": {"type": "boolean", "example": False},
                        "message": {"type": "string", "example": "Validation failed"},
                        "timestamp": {"type": "string", "format": "date-time"},
                        "error": {
                            "type": "object",
                            "properties": {
                                "code": {"type": "string", "example": "VALIDATION_ERROR"},
                                "details": {"type": "object"}
                            }
                        }
                    }
                },
                "PaginationInfo": {
                    "type": "object",
                    "properties": {
                        "page": {"type": "integer", "example": 1},
                        "per_page": {"type": "integer", "example": 20},
                        "total": {"type": "integer", "example": 100},
                        "pages": {"type": "integer", "example": 5},
                        "has_next": {"type": "boolean", "example": True},
                        "has_prev": {"type": "boolean", "example": False}
                    }
                }
            }
        },
        "security": [{"sessionAuth": []}],
        "paths": {
            "/donors": {
                "get": {
                    "summary": "Get donors list",
                    "description": "Retrieve a paginated list of donors with optional filtering",
                    "tags": ["Donors"],
                    "parameters": [
                        {
                            "name": "q",
                            "in": "query",
                            "description": "Search query for donor name, email, or notes",
                            "schema": {"type": "string"}
                        },
                        {
                            "name": "branch",
                            "in": "query",
                            "description": "Filter by branch",
                            "schema": {"type": "string"}
                        },
                        {
                            "name": "batch",
                            "in": "query",
                            "description": "Filter by batch",
                            "schema": {"type": "string"}
                        },
                        {
                            "name": "page",
                            "in": "query",
                            "description": "Page number",
                            "schema": {"type": "integer", "minimum": 1, "default": 1}
                        },
                        {
                            "name": "per_page",
                            "in": "query",
                            "description": "Items per page (max 100)",
                            "schema": {"type": "integer", "minimum": 1, "maximum": 100, "default": 20}
                        }
                    ],
                    "responses": {
                        "200": {
                            "description": "Successful response",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "allOf": [
                                            {"$ref": "#/components/schemas/APIResponse"},
                                            {
                                                "properties": {
                                                    "data": {
                                                        "type": "object",
                                                        "properties": {
                                                            "donors": {
                                                                "type": "array",
                                                                "items": {"$ref": "#/components/schemas/Donor"}
                                                            },
                                                            "pagination": {"$ref": "#/components/schemas/PaginationInfo"}
                                                        }
                                                    }
                                                }
                                            }
                                        ]
                                    }
                                }
                            }
                        },
                        "401": {
                            "description": "Authentication required",
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/APIError"}
                                }
                            }
                        }
                    }
                },
                "post": {
                    "summary": "Create new donor",
                    "description": "Create a new donor record (Admin/Incharge only)",
                    "tags": ["Donors"],
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/Donor"}
                            }
                        }
                    },
                    "responses": {
                        "201": {
                            "description": "Donor created successfully",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "allOf": [
                                            {"$ref": "#/components/schemas/APIResponse"},
                                            {
                                                "properties": {
                                                    "data": {
                                                        "type": "object",
                                                        "properties": {
                                                            "donor": {"$ref": "#/components/schemas/Donor"}
                                                        }
                                                    }
                                                }
                                            }
                                        ]
                                    }
                                }
                            }
                        },
                        "400": {
                            "description": "Bad request (e.g., duplicate email)",
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/APIError"}
                                }
                            }
                        },
                        "422": {
                            "description": "Validation error",
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/APIError"}
                                }
                            }
                        },
                        "403": {
                            "description": "Access forbidden",
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/APIError"}
                                }
                            }
                        }
                    }
                }
            },
            "/donors/{donor_id}": {
                "get": {
                    "summary": "Get donor details",
                    "description": "Retrieve detailed information about a specific donor",
                    "tags": ["Donors"],
                    "parameters": [
                        {
                            "name": "donor_id",
                            "in": "path",
                            "required": True,
                            "description": "Donor ID",
                            "schema": {"type": "integer"}
                        }
                    ],
                    "responses": {
                        "200": {
                            "description": "Successful response",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "allOf": [
                                            {"$ref": "#/components/schemas/APIResponse"},
                                            {
                                                "properties": {
                                                    "data": {
                                                        "type": "object",
                                                        "properties": {
                                                            "donor": {"$ref": "#/components/schemas/Donor"}
                                                        }
                                                    }
                                                }
                                            }
                                        ]
                                    }
                                }
                            }
                        },
                        "404": {
                            "description": "Donor not found",
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/APIError"}
                                }
                            }
                        }
                    }
                }
            },
            "/inventory": {
                "get": {
                    "summary": "Get inventory items",
                    "description": "Retrieve a paginated list of inventory items with advanced filtering",
                    "tags": ["Inventory"],
                    "parameters": [
                        {
                            "name": "q",
                            "in": "query",
                            "description": "Search query for title, authors, description, or SKU",
                            "schema": {"type": "string"}
                        },
                        {
                            "name": "type",
                            "in": "query",
                            "description": "Filter by item type (comma-separated for multiple)",
                            "schema": {"type": "string", "enum": ["book", "laptop", "kit"]}
                        },
                        {
                            "name": "availability",
                            "in": "query",
                            "description": "Filter by availability",
                            "schema": {"type": "string", "enum": ["all", "available", "unavailable"]}
                        },
                        {
                            "name": "language",
                            "in": "query",
                            "description": "Filter by language",
                            "schema": {"type": "string"}
                        },
                        {
                            "name": "department",
                            "in": "query",
                            "description": "Filter by department ID",
                            "schema": {"type": "integer"}
                        },
                        {
                            "name": "donor",
                            "in": "query",
                            "description": "Filter by donor ID",
                            "schema": {"type": "integer"}
                        },
                        {
                            "name": "sort",
                            "in": "query",
                            "description": "Sort field",
                            "schema": {"type": "string", "enum": ["title", "authors", "created_at", "popularity", "availability"], "default": "title"}
                        },
                        {
                            "name": "order",
                            "in": "query",
                            "description": "Sort order",
                            "schema": {"type": "string", "enum": ["asc", "desc"], "default": "asc"}
                        },
                        {
                            "name": "page",
                            "in": "query",
                            "description": "Page number",
                            "schema": {"type": "integer", "minimum": 1, "default": 1}
                        },
                        {
                            "name": "per_page",
                            "in": "query",
                            "description": "Items per page (max 100)",
                            "schema": {"type": "integer", "minimum": 1, "maximum": 100, "default": 20}
                        }
                    ],
                    "responses": {
                        "200": {
                            "description": "Successful response",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "allOf": [
                                            {"$ref": "#/components/schemas/APIResponse"},
                                            {
                                                "properties": {
                                                    "data": {
                                                        "type": "object",
                                                        "properties": {
                                                            "items": {
                                                                "type": "array",
                                                                "items": {"$ref": "#/components/schemas/InventoryItem"}
                                                            },
                                                            "pagination": {"$ref": "#/components/schemas/PaginationInfo"},
                                                            "filters": {"type": "object"}
                                                        }
                                                    }
                                                }
                                            }
                                        ]
                                    }
                                }
                            }
                        }
                    }
                },
                "post": {
                    "summary": "Create inventory item",
                    "description": "Create a new inventory item (Admin/Incharge only)",
                    "tags": ["Inventory"],
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/InventoryItem"}
                            }
                        }
                    },
                    "responses": {
                        "201": {
                            "description": "Inventory item created successfully",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "allOf": [
                                            {"$ref": "#/components/schemas/APIResponse"},
                                            {
                                                "properties": {
                                                    "data": {
                                                        "type": "object",
                                                        "properties": {
                                                            "item": {"$ref": "#/components/schemas/InventoryItem"}
                                                        }
                                                    }
                                                }
                                            }
                                        ]
                                    }
                                }
                            }
                        },
                        "422": {
                            "description": "Validation error",
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/APIError"}
                                }
                            }
                        }
                    }
                }
            },
            "/search": {
                "get": {
                    "summary": "Search suggestions",
                    "description": "Get search suggestions for autocomplete",
                    "tags": ["Search"],
                    "parameters": [
                        {
                            "name": "q",
                            "in": "query",
                            "required": True,
                            "description": "Search query (minimum 2 characters)",
                            "schema": {"type": "string", "minLength": 2}
                        }
                    ],
                    "responses": {
                        "200": {
                            "description": "Search suggestions",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "allOf": [
                                            {"$ref": "#/components/schemas/APIResponse"},
                                            {
                                                "properties": {
                                                    "data": {
                                                        "type": "object",
                                                        "properties": {
                                                            "query": {"type": "string"},
                                                            "suggestions": {
                                                                "type": "object",
                                                                "properties": {
                                                                    "items": {"type": "array"},
                                                                    "donors": {"type": "array"}
                                                                }
                                                            }
                                                        }
                                                    }
                                                }
                                            }
                                        ]
                                    }
                                }
                            }
                        },
                        "400": {
                            "description": "Query too short",
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/APIError"}
                                }
                            }
                        }
                    }
                }
            }
        }
    }


def setup_swagger(app):
    """Setup Swagger UI for API documentation"""
    
    # Swagger UI blueprint
    SWAGGER_URL = '/api/docs'
    API_URL = '/api/swagger.json'
    
    swaggerui_blueprint = get_swaggerui_blueprint(
        SWAGGER_URL,
        API_URL,
        config={
            'app_name': "D-Block Library Management System API",
            'supportedSubmitMethods': ['get', 'post', 'put', 'delete'],
            'docExpansion': 'list',
            'defaultModelsExpandDepth': 2,
            'defaultModelExpandDepth': 2
        }
    )
    
    app.register_blueprint(swaggerui_blueprint, url_prefix=SWAGGER_URL)
    
    # Swagger JSON endpoint
    @app.route('/api/swagger.json')
    def swagger_json():
        return jsonify(create_swagger_config())
    
    return app