# LocalChess

## Docker Setup
To set up LocalChess using Docker, follow these steps:
1. Ensure Docker is installed on your machine.
2. Clone the repository:
   ```bash
   git clone https://github.com/Licent1/LocalChess.git
   cd LocalChess
   ```
3. Build the Docker image:
   ```bash
   docker build -t localchess .
   ```
4. Run the Docker container:
   ```bash
   docker run -p 3000:3000 localchess
   ```

## Backend Installation
To install the backend, perform the following:
1. Navigate to the backend directory:
   ```bash
   cd backend
   ```
2. Install dependencies:
   ```bash
   npm install
   ```
3. Start the backend server:
   ```bash
   npm start
   ```

## Authentication API Functionality
The authentication API of LocalChess allows users to register and login. It supports JWT for managing user sessions. The following endpoints are available:
- **POST /auth/register**: Register a new user.
  - Body: `{
      "username": "string",
      "password": "string"
   }`

- **POST /auth/login**: Log in a user and receive a JWT.
  - Body: `{
      "username": "string",
      "password": "string"
   }`

Ensure to include the JWT in the Authorization header for any protected routes.

## License
This project is licensed under the MIT License.