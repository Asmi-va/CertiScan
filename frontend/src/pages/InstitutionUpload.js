import React, { useState } from 'react';
import { useDropzone } from 'react-dropzone';
import { CloudArrowUpIcon, DocumentTextIcon, ExclamationTriangleIcon, CheckCircleIcon, XCircleIcon } from '@heroicons/react/24/outline';
import axios from 'axios';

function InstitutionUpload() {
  const [file, setFile] = useState(null);
  const [fileType, setFileType] = useState(null); // 'csv' or 'json'
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [institutionId, setInstitutionId] = useState('');
  const [institutionName, setInstitutionName] = useState('');
  const [institutionEmail, setInstitutionEmail] = useState('');
  const [showInstitutionForm, setShowInstitutionForm] = useState(false);

  const onDrop = (acceptedFiles) => {
    const selectedFile = acceptedFiles[0];
    if (selectedFile) {
      setFile(selectedFile);
      
      // Determine file type
      if (selectedFile.name.endsWith('.csv')) {
        setFileType('csv');
      } else if (selectedFile.name.endsWith('.json')) {
        setFileType('json');
      } else {
        setFileType(null);
        setError('Unsupported file format. Please upload a CSV or JSON file.');
      }
      
      setError(null);
      setResult(null);
    }
  };

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'text/csv': ['.csv'],
      'application/json': ['.json']
    },
    maxFiles: 1
  });

  const handleUpload = async (e) => {
    e.preventDefault();
    
    if (!file) {
      setError('Please select a file to upload');
      return;
    }
    
    if (!institutionId) {
      setError('Institution ID is required');
      return;
    }
    
    setLoading(true);
    setError(null);
    
    const formData = new FormData();
    formData.append('file', file);
    formData.append('institution_id', institutionId);
    
    try {
      const response = await axios.post('/api/institution/upload', formData, {
        headers: {
          'Content-Type': 'multipart/form-data'
        }
      });
      
      setResult({
        success: true,
        message: 'File uploaded successfully',
        details: response.data
      });
    } catch (err) {
      console.error('Error uploading file:', err);
      setResult({
        success: false,
        message: err.response?.data?.detail || 'Failed to upload file'
      });
    } finally {
      setLoading(false);
    }
  };

  const handleRegisterInstitution = async (e) => {
    e.preventDefault();
    
    if (!institutionId || !institutionName || !institutionEmail) {
      setError('All fields are required');
      return;
    }
    
    setLoading(true);
    setError(null);
    
    try {
      const response = await axios.post('/api/institution/register', {
        institution_id: institutionId,
        name: institutionName,
        email: institutionEmail
      });
      
      setResult({
        success: true,
        message: 'Institution registered successfully',
        details: response.data
      });
      
      // Hide the form after successful registration
      setShowInstitutionForm(false);
    } catch (err) {
      console.error('Error registering institution:', err);
      setResult({
        success: false,
        message: err.response?.data?.detail || 'Failed to register institution'
      });
    } finally {
      setLoading(false);
    }
  };

  const resetForm = () => {
    setFile(null);
    setFileType(null);
    setResult(null);
    setError(null);
    setInstitutionId('');
  };

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900">Institution Certificate Upload</h1>
        <p className="mt-2 text-lg text-gray-600">
          Upload certificate records in bulk using CSV or JSON format
        </p>
      </div>

      {/* Error Message */}
      {error && (
        <div className="rounded-md bg-red-50 p-4 mb-6">
          <div className="flex">
            <div className="flex-shrink-0">
              <XCircleIcon className="h-5 w-5 text-red-400" aria-hidden="true" />
            </div>
            <div className="ml-3">
              <h3 className="text-sm font-medium text-red-800">{error}</h3>
            </div>
          </div>
        </div>
      )}

      {/* Result Message */}
      {result && (
        <div className={`rounded-md ${result.success ? 'bg-green-50' : 'bg-red-50'} p-4 mb-6`}>
          <div className="flex">
            <div className="flex-shrink-0">
              {result.success ? (
                <CheckCircleIcon className="h-5 w-5 text-green-400" aria-hidden="true" />
              ) : (
                <XCircleIcon className="h-5 w-5 text-red-400" aria-hidden="true" />
              )}
            </div>
            <div className="ml-3">
              <h3 className={`text-sm font-medium ${result.success ? 'text-green-800' : 'text-red-800'}`}>
                {result.message}
              </h3>
              {result.details && result.success && (
                <div className="mt-2 text-sm text-green-700">
                  <p>Successfully processed {result.details.processed_count} records.</p>
                  {result.details.error_count > 0 && (
                    <p className="text-yellow-700">{result.details.error_count} records had errors.</p>
                  )}
                </div>
              )}
              <div className="mt-4">
                <button
                  type="button"
                  onClick={resetForm}
                  className="rounded-md bg-white px-3.5 py-2 text-sm font-semibold text-gray-900 shadow-sm ring-1 ring-inset ring-gray-300 hover:bg-gray-50"
                >
                  Upload Another File
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {!result && (
        <div className="bg-white shadow rounded-lg overflow-hidden">
          <div className="px-4 py-5 sm:p-6">
            {/* Institution Registration Toggle */}
            <div className="mb-6">
              <button
                type="button"
                onClick={() => setShowInstitutionForm(!showInstitutionForm)}
                className="text-primary-600 hover:text-primary-800 font-medium"
              >
                {showInstitutionForm ? 'Hide Registration Form' : 'Register New Institution'}
              </button>
            </div>

            {/* Institution Registration Form */}
            {showInstitutionForm && (
              <div className="bg-gray-50 p-4 rounded-md mb-6">
                <h3 className="text-lg font-medium text-gray-900 mb-4">Register Institution</h3>
                <form onSubmit={handleRegisterInstitution} className="space-y-4">
                  <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
                    <div>
                      <label htmlFor="institution_id" className="block text-sm font-medium text-gray-700">
                        Institution ID
                      </label>
                      <input
                        type="text"
                        name="institution_id"
                        id="institution_id"
                        value={institutionId}
                        onChange={(e) => setInstitutionId(e.target.value)}
                        className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 sm:text-sm"
                        required
                      />
                    </div>
                    <div>
                      <label htmlFor="institution_name" className="block text-sm font-medium text-gray-700">
                        Institution Name
                      </label>
                      <input
                        type="text"
                        name="institution_name"
                        id="institution_name"
                        value={institutionName}
                        onChange={(e) => setInstitutionName(e.target.value)}
                        className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 sm:text-sm"
                        required
                      />
                    </div>
                    <div>
                      <label htmlFor="institution_email" className="block text-sm font-medium text-gray-700">
                        Institution Email
                      </label>
                      <input
                        type="email"
                        name="institution_email"
                        id="institution_email"
                        value={institutionEmail}
                        onChange={(e) => setInstitutionEmail(e.target.value)}
                        className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 sm:text-sm"
                        required
                      />
                    </div>
                  </div>
                  <div className="flex justify-end">
                    <button
                      type="submit"
                      disabled={loading}
                      className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-primary-600 hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500 disabled:opacity-50"
                    >
                      {loading ? 'Registering...' : 'Register Institution'}
                    </button>
                  </div>
                </form>
              </div>
            )}

            {/* File Upload Section */}
            <div>
              <h3 className="text-lg font-medium text-gray-900 mb-4">Upload Certificate Records</h3>
              
              <div className="space-y-6">
                {/* Institution ID Input */}
                <div>
                  <label htmlFor="upload_institution_id" className="block text-sm font-medium text-gray-700">
                    Institution ID
                  </label>
                  <input
                    type="text"
                    name="upload_institution_id"
                    id="upload_institution_id"
                    value={institutionId}
                    onChange={(e) => setInstitutionId(e.target.value)}
                    className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-primary-500 focus:ring-primary-500 sm:text-sm"
                    required
                  />
                </div>

                {/* File Dropzone */}
                <div>
                  <div 
                    {...getRootProps()} 
                    className={`mt-1 flex justify-center px-6 pt-5 pb-6 border-2 ${isDragActive ? 'border-primary-500 bg-primary-50' : 'border-gray-300'} border-dashed rounded-md cursor-pointer hover:bg-gray-50`}
                  >
                    <div className="space-y-1 text-center">
                      <CloudArrowUpIcon className="mx-auto h-12 w-12 text-gray-400" />
                      <div className="flex text-sm text-gray-600">
                        <input {...getInputProps()} />
                        <p className="pl-1">
                          <span className="text-primary-600 font-medium">Click to upload</span> or drag and drop
                        </p>
                      </div>
                      <p className="text-xs text-gray-500">
                        CSV or JSON file up to 10MB
                      </p>
                    </div>
                  </div>
                </div>

                {/* Selected File Info */}
                {file && (
                  <div className="flex items-center p-4 bg-gray-50 rounded-md">
                    <DocumentTextIcon className="h-8 w-8 text-gray-400 mr-3" />
                    <div>
                      <p className="text-sm font-medium text-gray-900">{file.name}</p>
                      <p className="text-xs text-gray-500">
                        {(file.size / 1024).toFixed(2)} KB • {fileType?.toUpperCase()}
                      </p>
                    </div>
                  </div>
                )}

                {/* Upload Button */}
                <div className="flex justify-end">
                  <button
                    type="button"
                    onClick={handleUpload}
                    disabled={loading || !file || !fileType}
                    className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-primary-600 hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500 disabled:opacity-50"
                  >
                    {loading ? (
                      <>
                        <svg className="animate-spin -ml-1 mr-2 h-4 w-4 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                        </svg>
                        Uploading...
                      </>
                    ) : (
                      'Upload File'
                    )}
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* File Format Guide */}
      <div className="mt-8 bg-white shadow rounded-lg overflow-hidden">
        <div className="px-4 py-5 sm:p-6">
          <h3 className="text-lg font-medium text-gray-900 mb-4">File Format Guide</h3>
          
          <div className="bg-yellow-50 border-l-4 border-yellow-400 p-4 mb-6">
            <div className="flex">
              <div className="flex-shrink-0">
                <ExclamationTriangleIcon className="h-5 w-5 text-yellow-400" aria-hidden="true" />
              </div>
              <div className="ml-3">
                <p className="text-sm text-yellow-700">
                  Make sure your file follows the required format. Incorrect formats may cause upload failures.
                </p>
              </div>
            </div>
          </div>
          
          <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
            {/* CSV Format */}
            <div>
              <h4 className="text-md font-medium text-gray-900 mb-2">CSV Format</h4>
              <div className="bg-gray-50 p-4 rounded-md">
                <pre className="text-xs text-gray-700 overflow-x-auto">
                  cert_id,name,roll_no,course,marks,issue_date
                  CERT2025-001,John Doe,12345,B.Tech CSE,85%,2024-06-10
                  CERT2025-002,Jane Smith,12346,B.Tech ECE,92%,2024-06-10
                </pre>
              </div>
            </div>
            
            {/* JSON Format */}
            <div>
              <h4 className="text-md font-medium text-gray-900 mb-2">JSON Format</h4>
              <div className="bg-gray-50 p-4 rounded-md">
                <pre className="text-xs text-gray-700 overflow-x-auto">
                  {JSON.stringify([
                    {
                      "cert_id": "CERT2025-001",
                      "name": "John Doe",
                      "roll_no": "12345",
                      "course": "B.Tech CSE",
                      "marks": "85%",
                      "issue_date": "2024-06-10"
                    },
                    {
                      "cert_id": "CERT2025-002",
                      "name": "Jane Smith",
                      "roll_no": "12346",
                      "course": "B.Tech ECE",
                      "marks": "92%",
                      "issue_date": "2024-06-10"
                    }
                  ], null, 2)}
                </pre>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default InstitutionUpload;