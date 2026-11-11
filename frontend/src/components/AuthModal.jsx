import { useState } from 'react';
import { User, Lock, Mail, ArrowRight, ShieldCheck, Sparkles } from 'lucide-react';

export default function AuthModal({ onLoginSuccess }) {
  const [isSignUp, setIsSignUp] = useState(false);
  
  // Sign In State
  const [signInId, setSignInId] = useState('');
  const [signInPw, setSignInPw] = useState('');
  
  // Sign Up State
  const [fullName, setFullName] = useState('');
  const [signUpId, setSignUpId] = useState('');
  const [signUpPw, setSignUpPw] = useState('');
  const [confirmPw, setConfirmPw] = useState('');
  
  const [error, setError] = useState('');

  const handleSignIn = (e) => {
    e.preventDefault();
    setError('');

    if (!signInId.trim() || !signInPw.trim()) {
      setError('Please fill in both User ID and Password.');
      return;
    }

    // Retrieve accounts from localStorage or accept admin/demo
    const accounts = JSON.parse(localStorage.getItem('sb_accounts') || '[]');
    const existing = accounts.find(
      (acc) => (acc.userId === signInId.trim() || acc.email === signInId.trim()) && acc.password === signInPw
    );

    if (existing) {
      const user = { name: existing.name, userId: existing.userId };
      localStorage.setItem('sb_currentUser', JSON.stringify(user));
      onLoginSuccess(user);
    } else if (signInPw.length >= 4) {
      // Allow flexible demo sign-in
      const user = { 
        name: signInId.includes('@') ? signInId.split('@')[0] : signInId, 
        userId: signInId.trim() 
      };
      localStorage.setItem('sb_currentUser', JSON.stringify(user));
      onLoginSuccess(user);
    } else {
      setError('Invalid credentials. Password must be at least 4 characters.');
    }
  };

  const handleSignUp = (e) => {
    e.preventDefault();
    setError('');

    if (!fullName.trim() || !signUpId.trim() || !signUpPw.trim()) {
      setError('All fields are required.');
      return;
    }

    if (signUpPw.length < 4) {
      setError('Password must be at least 4 characters.');
      return;
    }

    if (signUpPw !== confirmPw) {
      setError('Passwords do not match.');
      return;
    }

    const accounts = JSON.parse(localStorage.getItem('sb_accounts') || '[]');
    const isTaken = accounts.some((acc) => acc.userId === signUpId.trim());
    if (isTaken) {
      setError('This User ID is already taken. Please choose another.');
      return;
    }

    const newUser = {
      name: fullName.trim(),
      userId: signUpId.trim(),
      password: signUpPw
    };
    accounts.push(newUser);
    localStorage.setItem('sb_accounts', JSON.stringify(accounts));
    
    // Auto-login after sign-up
    const userSession = { name: newUser.name, userId: newUser.userId };
    localStorage.setItem('sb_currentUser', JSON.stringify(userSession));
    onLoginSuccess(userSession);
  };

  const handleQuickDemo = (roleName) => {
    const demoUser = {
      name: roleName === 'signer' ? 'Arokiya (Signer)' : 'Alex (Participant)',
      userId: roleName === 'signer' ? 'signer_demo' : 'guest_demo'
    };
    localStorage.setItem('sb_currentUser', JSON.stringify(demoUser));
    onLoginSuccess(demoUser);
  };

  return (
    <div className="w-full min-h-screen flex items-center justify-center p-4 relative">
      {/* Decorative Google Glow orbs */}
      <div className="absolute top-1/4 left-1/3 w-80 h-80 bg-blue-500/15 rounded-full blur-3xl pointer-events-none"></div>
      <div className="absolute bottom-1/4 right-1/3 w-80 h-80 bg-emerald-500/10 rounded-full blur-3xl pointer-events-none"></div>

      <div className="glass-panel w-full max-w-md rounded-3xl p-8 shadow-2xl relative z-10 border border-white/10 transition-all">
        {/* Brand Header */}
        <div className="text-center mb-6">
          <div className="inline-flex items-center justify-center w-14 h-14 rounded-2xl bg-gradient-to-tr from-blue-600 via-indigo-500 to-purple-600 shadow-lg shadow-blue-500/25 mb-3">
            <span className="text-2xl">🤟</span>
          </div>
          <h1 className="text-2xl font-bold tracking-tight bg-gradient-to-r from-white via-gray-100 to-gray-300 bg-clip-text text-transparent">
            SignBridge
          </h1>
          <p className="text-sm text-gray-400 mt-1">
            Google Meet Sign Language & Speech Translation
          </p>
        </div>

        {/* Tab Toggle: Sign In vs Sign Up */}
        <div className="flex bg-white/5 p-1 rounded-xl mb-6 border border-white/5">
          <button
            type="button"
            onClick={() => { setIsSignUp(false); setError(''); }}
            className={`flex-1 py-2 text-sm font-medium rounded-lg transition-all ${
              !isSignUp
                ? 'bg-blue-600 text-white shadow-md'
                : 'text-gray-400 hover:text-white'
            }`}
          >
            Sign In
          </button>
          <button
            type="button"
            onClick={() => { setIsSignUp(true); setError(''); }}
            className={`flex-1 py-2 text-sm font-medium rounded-lg transition-all ${
              isSignUp
                ? 'bg-blue-600 text-white shadow-md'
                : 'text-gray-400 hover:text-white'
            }`}
          >
            Create Account
          </button>
        </div>

        {/* Error Alert */}
        {error && (
          <div className="mb-4 px-3.5 py-2.5 rounded-xl bg-red-500/15 border border-red-500/30 text-red-300 text-xs flex items-center gap-2 animate-fadeIn">
            <span>⚠️</span>
            <span>{error}</span>
          </div>
        )}

        {/* Forms */}
        {!isSignUp ? (
          /* Sign In Form */
          <form onSubmit={handleSignIn} className="space-y-4">
            <div>
              <label className="block text-xs font-medium text-gray-300 mb-1.5 ml-1">
                User ID or Email
              </label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-gray-400">
                  <User size={16} />
                </div>
                <input
                  type="text"
                  value={signInId}
                  onChange={(e) => setSignInId(e.target.value)}
                  placeholder="e.g. user or your email"
                  className="glass-input w-full pl-10 pr-4 py-2.5 rounded-xl text-sm text-white placeholder-gray-500"
                />
              </div>
            </div>

            <div>
              <label className="block text-xs font-medium text-gray-300 mb-1.5 ml-1">
                Password
              </label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-gray-400">
                  <Lock size={16} />
                </div>
                <input
                  type="password"
                  value={signInPw}
                  onChange={(e) => setSignInPw(e.target.value)}
                  placeholder="••••••••"
                  className="glass-input w-full pl-10 pr-4 py-2.5 rounded-xl text-sm text-white placeholder-gray-500"
                />
              </div>
            </div>

            <button
              type="submit"
              className="w-full mt-2 py-3 px-4 rounded-xl font-medium text-sm text-white bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 transition-all shadow-lg shadow-blue-500/20 flex items-center justify-center gap-2 group"
            >
              <span>Sign In to Meeting</span>
              <ArrowRight size={16} className="group-hover:translate-x-0.5 transition-transform" />
            </button>
          </form>
        ) : (
          /* Sign Up Form */
          <form onSubmit={handleSignUp} className="space-y-3.5">
            <div>
              <label className="block text-xs font-medium text-gray-300 mb-1 ml-1">
                Full Name
              </label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-gray-400">
                  <User size={16} />
                </div>
                <input
                  type="text"
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                  placeholder="Your Name"
                  className="glass-input w-full pl-10 pr-4 py-2 rounded-xl text-sm text-white placeholder-gray-500"
                />
              </div>
            </div>

            <div>
              <label className="block text-xs font-medium text-gray-300 mb-1 ml-1">
                User ID
              </label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-gray-400">
                  <Mail size={16} />
                </div>
                <input
                  type="text"
                  value={signUpId}
                  onChange={(e) => setSignUpId(e.target.value)}
                  placeholder="Choose username or ID"
                  className="glass-input w-full pl-10 pr-4 py-2 rounded-xl text-sm text-white placeholder-gray-500"
                />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-2.5">
              <div>
                <label className="block text-xs font-medium text-gray-300 mb-1 ml-1">
                  Password
                </label>
                <div className="relative">
                  <input
                    type="password"
                    value={signUpPw}
                    onChange={(e) => setSignUpPw(e.target.value)}
                    placeholder="••••••"
                    className="glass-input w-full px-3 py-2 rounded-xl text-sm text-white placeholder-gray-500"
                  />
                </div>
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-300 mb-1 ml-1">
                  Confirm
                </label>
                <div className="relative">
                  <input
                    type="password"
                    value={confirmPw}
                    onChange={(e) => setConfirmPw(e.target.value)}
                    placeholder="••••••"
                    className="glass-input w-full px-3 py-2 rounded-xl text-sm text-white placeholder-gray-500"
                  />
                </div>
              </div>
            </div>

            <button
              type="submit"
              className="w-full mt-2 py-3 px-4 rounded-xl font-medium text-sm text-white bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 transition-all shadow-lg shadow-blue-500/20 flex items-center justify-center gap-2 group"
            >
              <span>Create Free Account</span>
              <ArrowRight size={16} className="group-hover:translate-x-0.5 transition-transform" />
            </button>
          </form>
        )}

        {/* Quick Demo Login Option */}
        <div className="mt-6 pt-5 border-t border-white/10">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs text-gray-400 flex items-center gap-1.5">
              <Sparkles size={12} className="text-yellow-400" />
              Instant Demo Access:
            </span>
          </div>
          <div className="grid grid-cols-2 gap-2">
            <button
              type="button"
              onClick={() => handleQuickDemo('signer')}
              className="py-1.5 px-2 rounded-lg bg-white/5 hover:bg-white/10 border border-white/10 text-xs text-gray-300 hover:text-white transition-colors flex items-center justify-center gap-1.5"
            >
              <span>🤟</span> Signer User
            </button>
            <button
              type="button"
              onClick={() => handleQuickDemo('normal')}
              className="py-1.5 px-2 rounded-lg bg-white/5 hover:bg-white/10 border border-white/10 text-xs text-gray-300 hover:text-white transition-colors flex items-center justify-center gap-1.5"
            >
              <span>💬</span> Hearing User
            </button>
          </div>
        </div>

        {/* Security badge */}
        <div className="mt-4 flex items-center justify-center gap-1.5 text-[11px] text-gray-500">
          <ShieldCheck size={13} className="text-emerald-400" />
          <span>Client-side private inference • WebRTC encrypted</span>
        </div>
      </div>
    </div>
  );
}
