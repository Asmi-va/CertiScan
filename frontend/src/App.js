import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';

// Layout components
import Navbar from './components/layout/Navbar';
import Footer from './components/layout/Footer';

// Pages
import Home from './pages/Home';
import VerifyCertificate from './pages/VerifyCertificate';
import VerificationResult from './pages/VerificationResult';
import AdminDashboard from './pages/admin/AdminDashboard';
import AdminLogs from './pages/admin/AdminLogs';
import AdminBlacklist from './pages/admin/AdminBlacklist';
import InstitutionUpload from './pages/InstitutionUpload';
import NotFound from './pages/NotFound';

function App() {
  return (
    <Router>
      <div className="flex flex-col min-h-screen bg-gray-50">
        <Navbar />
        <main className="flex-grow container mx-auto px-4 py-8">
          <Routes>
            <Route path="/" element={<Home />} />
            <Route path="/verify" element={<VerifyCertificate />} />
            <Route path="/result/:verificationId" element={<VerificationResult />} />
            <Route path="/admin" element={<AdminDashboard />} />
            <Route path="/admin/logs" element={<AdminLogs />} />
            <Route path="/admin/blacklist" element={<AdminBlacklist />} />
            <Route path="/institution/upload" element={<InstitutionUpload />} />
            <Route path="*" element={<NotFound />} />
          </Routes>
        </main>
        <Footer />
      </div>
    </Router>
  );
}

export default App;