import React, { useState, useEffect } from 'react';
import { useParams, useLocation, Link } from 'react-router-dom';
import { CheckCircleIcon, XCircleIcon, ExclamationTriangleIcon } from '@heroicons/react/24/solid';
import axios from 'axios';

function VerificationResult() {
  const { verificationId } = useParams();
  const location = useLocation();
  const [result, setResult] = useState(location.state?.result || null);
  const [loading, setLoading] = useState(!result);
  const [error, setError] = useState(null);
  
  useEffect(() => {
    // If result wasn't passed via location state, fetch it
    if (!result && verificationId) {
      const fetchResult = async () => {
        try {
          const response = await axios.get(`/api/verification/${verificationId}`);
          setResult(response.data);
        } catch (err) {
          console.error('Error fetching verification result:', err);
          setError('Could not load verification result. Please try again.');
        } finally {
          setLoading(false);
        }
      };
      
      fetchResult();
    } else {
      setLoading(false);
    }
  }, [result, verificationId]);
  
  if (loading) {
    return (
      <div className="flex justify-center items-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-primary-600"></div>
      </div>
    );
  }
  
  if (error || !result) {
    return (
      <div className="max-w-3xl mx-auto text-center">
        <div className="bg-red-50 border border-red-200 rounded-lg p-6">
          <XCircleIcon className="h-12 w-12 text-red-500 mx-auto" />
          <h2 className="mt-4 text-lg font-medium text-red-800">Error Loading Results</h2>
          <p className="mt-2 text-red-700">{error || 'Verification result not found'}</p>
          <Link 
            to="/verify" 
            className="mt-4 inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-primary-600 hover:bg-primary-700"
          >
            Try Again
          </Link>
        </div>
      </div>
    );
  }
  
  const isPassed = result.status === 'PASS';
  
  return (
    <div className="max-w-4xl mx-auto">
      <div className="text-center mb-8">
        <h1 className="text-3xl font-bold text-gray-900">Verification Result</h1>
        <p className="mt-2 text-lg text-gray-600">
          Certificate ID: {result.cert_id || 'Unknown'}
        </p>
      </div>
      
      <div className="bg-white rounded-lg shadow-md overflow-hidden">
        {/* Result Header */}
        <div className={`p-6 ${isPassed ? 'bg-green-50' : 'bg-red-50'}`}>
          <div className="flex items-center">
            {isPassed ? (
              <CheckCircleIcon className="h-10 w-10 text-green-500" />
            ) : (
              <ExclamationTriangleIcon className="h-10 w-10 text-red-500" />
            )}
            <div className="ml-4">
              <h2 className={`text-xl font-bold ${isPassed ? 'text-green-800' : 'text-red-800'}`}>
                {isPassed ? 'Certificate Verified' : 'Certificate Flagged'}
              </h2>
              <p className={`text-sm ${isPassed ? 'text-green-700' : 'text-red-700'}`}>
                {isPassed 
                  ? 'This certificate appears to be genuine and matches our records.' 
                  : 'This certificate has been flagged due to potential issues.'}
              </p>
            </div>
          </div>
        </div>
        
        {/* Certificate Details */}
        <div className="p-6 border-t border-gray-200">
          <h3 className="text-lg font-medium text-gray-900 mb-4">Certificate Details</h3>
          
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="bg-gray-50 p-4 rounded-md">
              <p className="text-sm font-medium text-gray-500">Name</p>
              <p className="mt-1 text-base font-medium text-gray-900">
                {result.details?.certificate?.name || 'Not available'}
              </p>
            </div>
            
            <div className="bg-gray-50 p-4 rounded-md">
              <p className="text-sm font-medium text-gray-500">Roll Number</p>
              <p className="mt-1 text-base font-medium text-gray-900">
                {result.details?.certificate?.roll_no || 'Not available'}
              </p>
            </div>
            
            <div className="bg-gray-50 p-4 rounded-md">
              <p className="text-sm font-medium text-gray-500">Course</p>
              <p className="mt-1 text-base font-medium text-gray-900">
                {result.details?.certificate?.course || 'Not available'}
              </p>
            </div>
            
            <div className="bg-gray-50 p-4 rounded-md">
              <p className="text-sm font-medium text-gray-500">Issue Date</p>
              <p className="mt-1 text-base font-medium text-gray-900">
                {result.details?.certificate?.issue_date 
                  ? new Date(result.details.certificate.issue_date).toLocaleDateString() 
                  : 'Not available'}
              </p>
            </div>
          </div>
        </div>
        
        {/* Verification Details */}
        {!isPassed && (
          <div className="p-6 border-t border-gray-200">
            <h3 className="text-lg font-medium text-gray-900 mb-4">Issues Detected</h3>
            
            <div className="space-y-4">
              {/* Data Mismatches */}
              {(result.details?.name_mismatch || 
                result.details?.roll_no_mismatch || 
                result.details?.course_mismatch || 
                result.details?.marks_mismatch) && (
                <div className="bg-yellow-50 p-4 rounded-md">
                  <h4 className="font-medium text-yellow-800">Data Mismatches</h4>
                  <ul className="mt-2 text-sm text-yellow-700 list-disc list-inside">
                    {result.details.name_mismatch && (
                      <li>Name mismatch: Expected "{result.details.name_mismatch.expected}"</li>
                    )}
                    {result.details.roll_no_mismatch && (
                      <li>Roll number mismatch: Expected "{result.details.roll_no_mismatch.expected}"</li>
                    )}
                    {result.details.course_mismatch && (
                      <li>Course mismatch: Expected "{result.details.course_mismatch.expected}"</li>
                    )}
                    {result.details.marks_mismatch && (
                      <li>Marks mismatch: Expected "{result.details.marks_mismatch.expected}"</li>
                    )}
                  </ul>
                </div>
              )}
              
              {/* Tamper Detection */}
              {result.details?.tamper_detection && (
                <div className="bg-red-50 p-4 rounded-md">
                  <h4 className="font-medium text-red-800">Tampering Detected</h4>
                  <p className="mt-1 text-sm text-red-700">
                    Confidence: {Math.round(result.details.tamper_detection.confidence * 100)}%
                  </p>
                  <p className="text-sm text-red-700">
                    Methods: {result.details.tamper_detection.methods.join(', ')}
                  </p>
                </div>
              )}
              
              {/* Blacklisted */}
              {result.details?.blacklisted && (
                <div className="bg-red-50 p-4 rounded-md">
                  <h4 className="font-medium text-red-800">Certificate Blacklisted</h4>
                  <p className="mt-1 text-sm text-red-700">
                    Reason: {result.details.blacklisted.reason}
                  </p>
                  <p className="text-sm text-red-700">
                    Date: {new Date(result.details.blacklisted.blacklisted_at).toLocaleDateString()}
                  </p>
                </div>
              )}
              
              {/* Not Found */}
              {result.details?.not_found && (
                <div className="bg-red-50 p-4 rounded-md">
                  <h4 className="font-medium text-red-800">Certificate Not Found</h4>
                  <p className="mt-1 text-sm text-red-700">
                    This certificate ID does not exist in our database.
                  </p>
                </div>
              )}
            </div>
          </div>
        )}
        
        {/* Actions */}
        <div className="p-6 border-t border-gray-200 bg-gray-50">
          <div className="flex flex-col sm:flex-row justify-between items-center">
            <p className="text-sm text-gray-500 mb-4 sm:mb-0">
              Verification ID: {verificationId}
            </p>
            <div className="flex space-x-4">
              <Link 
                to="/verify" 
                className="inline-flex items-center px-4 py-2 border border-gray-300 text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50"
              >
                Verify Another
              </Link>
              <button 
                onClick={() => window.print()} 
                className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-primary-600 hover:bg-primary-700"
              >
                Print Result
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default VerificationResult;