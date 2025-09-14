import React from 'react';
import { Link } from 'react-router-dom';
import { ShieldCheckIcon } from '@heroicons/react/24/solid';

function Footer() {
  return (
    <footer className="bg-white border-t border-gray-200">
      <div className="container mx-auto px-4 py-8">
        <div className="flex flex-col md:flex-row justify-between items-center">
          <div className="flex items-center mb-4 md:mb-0">
            <ShieldCheckIcon className="h-6 w-auto text-primary-600" />
            <span className="ml-2 text-lg font-semibold text-gray-900">CertVerify</span>
          </div>
          
          <div className="flex space-x-6">
            <Link to="/" className="text-sm text-gray-600 hover:text-primary-600 transition-colors">
              Home
            </Link>
            <Link to="/verify" className="text-sm text-gray-600 hover:text-primary-600 transition-colors">
              Verify Certificate
            </Link>
            <Link to="/admin" className="text-sm text-gray-600 hover:text-primary-600 transition-colors">
              Admin
            </Link>
          </div>
        </div>
        
        <div className="mt-8 border-t border-gray-200 pt-6 text-center">
          <p className="text-sm text-gray-500">
            &copy; {new Date().getFullYear()} CertVerify. All rights reserved.
          </p>
          <p className="text-xs text-gray-400 mt-2">
            A Fake Certificate Detection System built for Smart India Hackathon
          </p>
        </div>
      </div>
    </footer>
  );
}

export default Footer;