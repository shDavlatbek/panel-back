# JWT Authentication Test Frontend

This is a Vue.js 3 frontend application for testing the Django REST Framework JWT authentication backend.

## Features

- Login with JWT token stored in HTTP-only cookies
- Protected routes with authentication guards
- Test authentication status
- Logout functionality
- Centralized error handling
- Consistent UI with alerts for success and error messages

## Setup

### Prerequisites

- Node.js 16+ and npm
- Running DRF backend at http://localhost:8000

### Installation

```bash
# Install dependencies
npm install
```

### Development Server

```bash
# Start development server
npm run dev
```

The application will be available at http://localhost:5173 by default.

## Configuration

The API URL is configured in `src/services/auth.service.js`. By default, it points to `http://localhost:8000/api/auth/`. Update this if your backend is running on a different port.

## Usage

1. **Starting the Application**:
   - Start your Django backend server
   - Start this frontend application with `npm run dev`
   - Open the application in your browser

2. **Authentication Flow**:
   - Click "Login" in the navigation bar
   - Enter the username and password (default admin credentials created in the backend)
   - On successful login, you'll be redirected to the dashboard
   - The dashboard shows your username and provides buttons to test authentication and logout

3. **Testing Authentication**:
   - The "Test Authentication" button on the dashboard will make a request to the protected endpoint
   - The response is displayed below
   - If authentication fails, you'll be redirected to the login page

4. **Logout**:
   - The "Logout" button will clear your session by removing the HTTP-only cookie
   - After logout, you'll be redirected to the login page

## Project Structure

- `src/`
  - `components/` - UI components
  - `views/` - Page components
  - `router/` - Vue Router configuration with authentication guards
  - `stores/` - Pinia stores for state management
  - `services/` - API services and axios configuration
  - `assets/` - Static assets

## Authentication Details

This frontend is designed to work with the DRF JWT authentication backend using HTTP-only cookies. It doesn't store any tokens in localStorage for enhanced security.

## Troubleshooting

- **CORS Issues**: Make sure your Django backend has CORS configured properly to allow requests from the frontend domain
- **Cookie Issues**: Ensure your browser accepts cookies and the Django backend is configured to send HTTP-only cookies
- **Authentication Failures**: Check the console for error messages and the network tab to see the API responses
