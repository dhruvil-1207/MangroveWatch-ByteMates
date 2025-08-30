# Community Mangrove Watch

## Overview

Community Mangrove Watch is a web-based environmental monitoring platform designed to empower coastal communities in protecting mangrove ecosystems. The application enables citizens, fishermen, and coastal residents to report environmental incidents through an easy-to-use interface, creating a direct communication channel between local observers and conservation authorities. The platform serves as a bridge between community knowledge and official conservation action, transforming passive observers into active environmental guardians.

## User Preferences

Preferred communication style: Simple, everyday language.

## System Architecture

### Frontend Architecture
- **Template Engine**: Jinja2 templates with Flask for server-side rendering
- **CSS Framework**: Bootstrap 5.3.0 for responsive design and components
- **Icons**: Font Awesome 6.0.0 for consistent iconography
- **JavaScript**: Vanilla JavaScript with utility functions for enhanced interactivity
- **Responsive Design**: Mobile-first approach optimized for field use on mobile devices
- **Progressive Enhancement**: Core functionality works without JavaScript, enhanced features with JS

### Backend Architecture
- **Web Framework**: Flask (Python) with modular route organization
- **Authentication**: Flask-Login for session management and user authentication
- **Security**: Werkzeug security utilities for password hashing and validation
- **File Handling**: Secure file upload system with size limits (16MB) and type validation
- **Configuration**: Environment-based configuration with fallback defaults
- **Logging**: Built-in Python logging for debugging and monitoring

### Data Storage Solutions
- **Primary Database**: SQLAlchemy ORM with SQLite default (PostgreSQL ready)
- **Connection Management**: Connection pooling with health checks and recycling
- **Schema Design**: User-centric model with relationships between users and reports
- **Data Types**: Support for geospatial data (latitude/longitude), timestamps, and media references
- **Migration Ready**: DeclarativeBase setup for future schema evolution

### Authentication and Authorization
- **User Management**: Flask-Login integration with persistent sessions
- **Password Security**: Werkzeug password hashing with salt
- **User Types**: Role-based system (community, authority, ngo) for future feature differentiation
- **Session Security**: Configurable session keys with production security considerations
- **Access Control**: Login-required decorators for protected routes

### Application Structure
- **MVC Pattern**: Clear separation of models, views (templates), and controllers (routes)
- **Static Assets**: Organized CSS and JavaScript with custom styling and utility functions
- **File Organization**: Modular structure with separate files for models, routes, and configuration
- **Template Inheritance**: Base template system for consistent UI across pages

## External Dependencies

### Core Framework Dependencies
- **Flask**: Web application framework
- **Flask-SQLAlchemy**: Database ORM and migrations
- **Flask-Login**: User session management
- **Werkzeug**: WSGI utilities and security functions

### Frontend Libraries
- **Bootstrap 5.3.0**: CSS framework from CDN
- **Font Awesome 6.0.0**: Icon library from CDN

### Production Considerations
- **ProxyFix**: Werkzeug middleware for deployment behind reverse proxies
- **Environment Variables**: Support for DATABASE_URL and SESSION_SECRET configuration
- **File Upload**: Local filesystem storage with configurable upload directory

### Future Integration Points
- **Geolocation Services**: Browser-based location detection for incident reporting
- **Email Services**: For user registration confirmation and notifications
- **Mapping Services**: Integration ready for displaying incident locations
- **Image Processing**: Foundation for photo validation and optimization
- **API Integration**: Structure supports future integration with conservation databases and government systems

The architecture is designed for scalability and easy deployment, with clear separation of concerns and standard web development patterns that facilitate maintenance and feature expansion.