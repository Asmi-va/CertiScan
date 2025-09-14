# Certificate Verification System

A modern, responsive web application for verifying educational and professional certificates using blockchain technology. This frontend is built with React and integrates with a blockchain backend for secure and tamper-proof certificate verification.

## Features

- **User-Friendly Interface**: Clean and intuitive UI built with React and Tailwind CSS
- **Role-Based Access**: Different dashboards for institutions, employers, and government entities
- **Document Verification**: Secure upload and verification of certificates
- **Analytics Dashboard**: Visual representation of verification statistics using Chart.js
- **Responsive Design**: Works seamlessly on desktop and mobile devices

## Tech Stack

- **Frontend**: React 18
- **Styling**: Tailwind CSS
- **Routing**: React Router v6
- **HTTP Client**: Axios
- **UI Components**: Headless UI, Hero Icons
- **Data Visualization**: Chart.js, React-Chartjs-2
- **File Handling**: React Dropzone

## Getting Started

### Prerequisites

- Node.js (v16 or later)
- npm (v8 or later) or yarn

### Installation

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd frontend
   ```

2. Install dependencies:
   ```bash
   npm install
   # or
   yarn install
   ```

3. Start the development server:
   ```bash
   npm start
   # or
   yarn start
   ```

4. Open [http://localhost:3000](http://localhost:3000) to view it in your browser.

## Available Scripts

- `npm start` - Runs the app in development mode
- `npm test` - Launches the test runner
- `npm run build` - Builds the app for production to the `build` folder
- `npm run eject` - Ejects from Create React App (use with caution)

## Project Structure

```
frontend/
├── public/               # Static files
├── src/
│   ├── components/       # Reusable UI components
│   ├── pages/            # Page components
│   │   ├── admin/        # Admin dashboard
│   │   ├── Home.js       # Landing page
│   │   └── ...
│   ├── App.js            # Main application component
│   ├── index.js          # Application entry point
│   └── index.css         # Global styles
├── package.json          # Project dependencies and scripts
└── tailwind.config.js    # Tailwind CSS configuration
```

## Environment Variables

Create a `.env` file in the root directory and add the following variables:

```
REACT_APP_API_BASE_URL=your_api_base_url
# Add other environment variables as needed
```

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- Built with Create React App
- Styled with Tailwind CSS
- Icons by Hero Icons

## Support

For support, email support@certificatescan.com or open an issue in the repository.
