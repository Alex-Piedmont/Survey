import { useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { api } from '../api/client';
import { useAuth } from '../context/AuthContext';

export function LoginPage() {
  const [email, setEmail] = useState('');
  const [code, setCode] = useState('');
  const [step, setStep] = useState<'email' | 'code'>('email');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const { login } = useAuth();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const redirect = searchParams.get('redirect') || '/';

  const requestOTP = async () => {
    setError('');
    setLoading(true);
    try {
      const res = await api.post<{ message: string; _dev_code?: string }>(
        '/auth/otp/request',
        { email }
      );
      // In dev mode, auto-fill the code
      if (res._dev_code) {
        setCode(res._dev_code);
      }
      setStep('code');
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  const verifyOTP = async () => {
    setError('');
    setLoading(true);
    try {
      const res = await api.post<{ access_token: string }>('/auth/otp/verify', {
        email,
        code,
      });
      login(res.access_token, email);
      navigate(redirect, { replace: true });
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 px-4">
      <div className="max-w-sm w-full bg-white rounded-xl shadow-md p-8">
        <h1 className="text-2xl font-bold text-gray-900 mb-6 text-center">
          Classroom Survey
        </h1>

        {error && (
          <div className="mb-4 p-3 bg-red-50 border border-red-200 text-red-700 rounded-lg text-sm">
            {error}
          </div>
        )}

        {step === 'email' ? (
          <>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Email address
            </label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="you@university.edu"
              className="w-full px-3 py-2 border border-gray-300 rounded-lg mb-4 focus:outline-none focus:ring-2 focus:ring-blue-500"
              onKeyDown={(e) => e.key === 'Enter' && requestOTP()}
            />
            <button
              onClick={requestOTP}
              disabled={!email || loading}
              className="w-full py-2 bg-blue-600 text-white rounded-lg font-medium hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {loading ? 'Sending...' : 'Send verification code'}
            </button>
          </>
        ) : (
          <>
            <p className="text-sm text-gray-600 mb-4">
              We sent a code to <strong>{email}</strong>
            </p>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Verification code
            </label>
            <input
              type="text"
              value={code}
              onChange={(e) => setCode(e.target.value)}
              placeholder="123456"
              maxLength={6}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg mb-4 focus:outline-none focus:ring-2 focus:ring-blue-500 text-center text-2xl tracking-widest"
              onKeyDown={(e) => e.key === 'Enter' && verifyOTP()}
            />
            <button
              onClick={verifyOTP}
              disabled={code.length !== 6 || loading}
              className="w-full py-2 bg-blue-600 text-white rounded-lg font-medium hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {loading ? 'Verifying...' : 'Verify & sign in'}
            </button>
            <button
              onClick={() => { setStep('email'); setCode(''); }}
              className="w-full mt-2 py-2 text-gray-600 text-sm hover:text-gray-900"
            >
              Use a different email
            </button>
          </>
        )}
      </div>
    </div>
  );
}
