import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useDropzone } from 'react-dropzone';
import { DocumentArrowUpIcon, ArrowPathIcon } from '@heroicons/react/24/outline';
import axios from 'axios';

function VerifyCertificate() {
  const [file, setFile] = useState(null);
  const [preview, setPreview] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [institutionId, setInstitutionId] = useState('');
  const navigate = useNavigate();

  const onDrop = (acceptedFiles) => {
    setError(null);
    const selectedFile = acceptedFiles[0];
    
    // Check file type
    const allowedTypes = ['image/jpeg', 'image/png', 'image/jpg', 'application/pdf'];
    if (!allowedTypes.includes(selectedFile.type)) {
      setError('Please upload a valid certificate file (JPG, PNG, or PDF)');
      return;
    }
    
    // Check file size (max 10MB)
    if (selectedFile.size > 10 * 1024 * 1024) {
      setError('File size exceeds 10MB limit');
      return;
    }
    
    setFile(selectedFile);
    
    // Create preview for images
    if (selectedFile.type.startsWith('image/')) {
      const reader = new FileReader();
      reader.onload = () => {
        setPreview(reader.result);
      };
      reader.readAsDataURL(selectedFile);
    } else {
      // For PDFs, just show an icon or text
      setPreview('pdf');
    }
  };
  
  const { getRootProps, getInputProps, isDragActive } = useDropzone({ 
    onDrop,
    accept: {
      'image/jpeg': ['.jpg', '.jpeg'],
      'image/png': ['.png'],
      'application/pdf': ['.pdf']
    },
    multiple: false
  });
  
  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!file) {
      setError('Please select a certificate file to verify');
      return;
    }
    
    setLoading(true);
    setError(null);
    
    try {
      const formData = new FormData();
      formData.append('file', file);
      
      if (institutionId) {
        formData.append('institution_id', institutionId);
      }
      
      const response = await axios.post('/api/upload', formData, {
        headers: {
          'Content-Type': 'multipart/form-data'
        }
      });
      
      // Navigate to result page with verification ID
      navigate(`/result/${response.data.verification_id}`, { 
        state: { result: response.data } 
      });
      
    } catch (err) {
      console.error('Verification error:', err);
      setError(err.response?.data?.detail || 'Error verifying certificate. Please try again.');
    } finally {
      setLoading(false);
    }
  };
  
  const resetForm = () => {
    setFile(null);
    setPreview(null);
    setError(null);
    setInstitutionId('');
  };

  return (
    <div className="max-w-3xl mx-auto">
      <div className="text-center mb-8">
        <h1 className="text-3xl font-bold text-gray-900">Verify Certificate</h1>
        <p className="mt-2 text-lg text-gray-600">
          Upload a certificate to verify its authenticity
        </p>
      </div>
      
      <div className="bg-white rounded-lg shadow-md p-6">
        <form onSubmit={handleSubmit}>
          <div className="mb-6">
            <label htmlFor="institution" className="block text-sm font-medium text-gray-700 mb-1">
              Institution ID (Optional)
            </label>
            <input
              type="text"
              id="institution"
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-primary-500 focus:border-primary-500"
              placeholder="Enter institution ID if known"
              value={institutionId}
              onChange={(e) => setInstitutionId(e.target.value)}
            />
            <p className="mt-1 text-xs text-gray-500">
              Providing an institution ID improves verification accuracy
            </p>
          </div>
          
          <div 
            {...getRootProps()} 
            className={`certificate-upload-area p-6 flex flex-col items-center justify-center cursor-pointer ${isDragActive ? 'active' : ''} ${preview ? 'bg-gray-50' : ''}`}
          >
            <input {...getInputProps()} />
            
            {preview ? (
              <div className="text-center">
                {preview === 'pdf' ? (
                  <div className="flex flex-col items-center">
                    <DocumentArrowUpIcon className="h-16 w-16 text-primary-500" />
                    <p className="mt-2 text-sm font-medium text-gray-900">{file.name}</p>
                    <p className="text-xs text-gray-500">{(file.size / 1024 / 1024).toFixed(2)} MB</p>
                  </div>
                ) : (
                  <div>
                    <img 
                      src={preview} 
                      alt="Certificate preview" 
                      className="max-h-64 max-w-full mx-auto rounded-md" 
                    />
                    <p className="mt-2 text-sm font-medium text-gray-900">{file.name}</p>
                  </div>
                )}
                <button 
                  type="button"
                  onClick={(e) => {
                    e.stopPropagation();
                    resetForm();
                  }}
                  className="mt-4 inline-flex items-center px-3 py-1.5 border border-gray-300 text-xs font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500"
                >
                  Change file
                </button>
              </div>
            ) : (
              <div className="text-center">
                <DocumentArrowUpIcon className="mx-auto h-12 w-12 text-gray-400" />
                <p className="mt-2 text-sm font-medium text-gray-900">
                  {isDragActive ? 'Drop the certificate here' : 'Drag & drop certificate here'}
                </p>
                <p className="mt-1 text-xs text-gray-500">
                  or click to browse (JPG, PNG, PDF up to 10MB)
                </p>
              </div>
            )}
          </div>
          
          {error && (
            <div className="mt-4 bg-red-50 border border-red-200 rounded-md p-4">
              <p className="text-sm text-red-600">{error}</p>
            </div>
          )}
          
          <div className="mt-6 flex justify-center">
            <button
              type="submit"
              disabled={!file || loading}
              className="inline-flex items-center px-6 py-3 border border-transparent text-base font-medium rounded-md shadow-sm text-white bg-primary-600 hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500 disabled:bg-gray-300 disabled:cursor-not-allowed"
            >
              {loading ? (
                <>
                  <ArrowPathIcon className="animate-spin -ml-1 mr-2 h-5 w-5 text-white" />
                  Verifying...
                </>
              ) : 'Verify Certificate'}
            </button>
          </div>
        </form>
      </div>
      
      <div className="mt-8 bg-blue-50 border border-blue-200 rounded-md p-4">
        <h3 className="text-sm font-medium text-blue-800">How verification works:</h3>
        <ul className="mt-2 text-sm text-blue-700 list-disc list-inside">
          <li>OCR technology extracts text from your certificate</li>
          <li>Extracted data is compared with institutional records</li>
          <li>AI-powered tamper detection identifies signs of forgery</li>
          <li>Results show whether the certificate is genuine or flagged</li>
        </ul>
      </div>
    </div>
  );
}

export default VerifyCertificate;