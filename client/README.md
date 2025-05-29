# React + Vite
# Document Evaluator Web Client

This is the web client for the Document Evaluator application, which allows users to select and process documents with various LLM configurations and prompts.

## Getting Started

### Prerequisites

- Node.js (v16.0.0 or later recommended)
- npm (usually comes with Node.js)
- The backend server running on http://localhost:5001

### Starting the Application

#### On Windows

Run the launch script:

```
launch_client.bat
```

#### On macOS/Linux

Make the launch script executable and run it:

```bash
chmod +x launch_client.sh
./launch_client.sh
```

### Manual Setup

If the launch scripts don't work for you, you can manually set up and start the application:

1. Install dependencies:
   ```
   npm install
   ```

2. Start the development server:
   ```
   npm run dev
   ```

## Features

- Upload and process documents (PDF, TXT, DOCX, XLSX)
- Select from available LLM configurations and prompts
- Monitor processing progress in real-time
- View processing errors

## Configuration

Create a `.env` file in the root of the client directory with the following content:

```
VITE_API_URL=http://localhost:5001
```

Change the URL if your backend is running on a different host or port.

## Development

### Project Structure

- `src/` - Source code for the application
  - `components/` - React components
  - `services/` - API service functions
  - `hooks/` - Custom React hooks
  - `utils/` - Utility functions
  - `App.jsx` - Main application component
  - `main.jsx` - Entry point

### Building for Production

To create a production build:

```
npm run build
```

The build artifacts will be stored in the `dist/` directory.
This template provides a minimal setup to get React working in Vite with HMR and some ESLint rules.

Currently, two official plugins are available:

- [@vitejs/plugin-react](https://github.com/vitejs/vite-plugin-react/blob/main/packages/plugin-react) uses [Babel](https://babeljs.io/) for Fast Refresh
- [@vitejs/plugin-react-swc](https://github.com/vitejs/vite-plugin-react/blob/main/packages/plugin-react-swc) uses [SWC](https://swc.rs/) for Fast Refresh

## Expanding the ESLint configuration

If you are developing a production application, we recommend using TypeScript with type-aware lint rules enabled. Check out the [TS template](https://github.com/vitejs/vite/tree/main/packages/create-vite/template-react-ts) for information on how to integrate TypeScript and [`typescript-eslint`](https://typescript-eslint.io) in your project.
