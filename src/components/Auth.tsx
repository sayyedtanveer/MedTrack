import React, { useState } from "react";
import { KeyRound, Building2, User, Mail, Sparkles, LogIn, ArrowRight } from "lucide-react";

interface AuthProps {
  onLoginSuccess: (user: any, tenant: any, token: string) => void;
}

export default function Auth({ onLoginSuccess }: AuthProps) {
  const [isRegister, setIsRegister] = useState(false);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [name, setName] = useState("");
  const [tenantName, setTenantName] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError("");

    try {
      const endpoint = isRegister ? "/api/v1/auth/register-tenant" : "/api/v1/auth/login";
      const payload = isRegister 
        ? { tenantName, adminEmail: email, adminName: name, adminPassword: password }
        : { email, password };

      const response = await fetch(endpoint, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });

      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.error || "Authentication failed");
      }

      onLoginSuccess(data.user, data.tenant, data.token);
    } catch (err: any) {
      setError(err.message || "An unexpected error occurred");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-900 text-gray-100 p-4 relative overflow-hidden">
      {/* Background ambient glow blur */}
      <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-indigo-600/20 rounded-full blur-3xl"></div>
      <div className="absolute bottom-1/4 right-1/4 w-96 h-96 bg-purple-600/20 rounded-full blur-3xl"></div>

      <div className="w-full max-w-md relative z-10">
        <div className="text-center mb-8">
          <div className="inline-flex p-3 bg-indigo-600/10 border border-indigo-500/20 rounded-2xl text-indigo-400 mb-4 animate-pulse">
            <Building2 className="w-8 h-8" />
          </div>
          <h1 className="text-3xl font-bold tracking-tight text-white font-sans">
            MedTrack <span className="text-indigo-400">ERP</span>
          </h1>
          <p className="text-gray-400 mt-2 text-sm">
            Manufacturing Multi-Tenant Resource Planning
          </p>
        </div>

        <div className="bg-gray-800/80 backdrop-blur-xl border border-gray-700/50 rounded-3xl shadow-2xl p-8">
          <div className="flex items-center justify-between mb-8 border-b border-gray-700 pb-4">
            <button
              onClick={() => { setIsRegister(false); setError(""); }}
              className={`text-lg font-medium pb-2 transition-colors relative ${
                !isRegister ? "text-white font-semibold" : "text-gray-400 hover:text-gray-200"
              }`}
            >
              Sign In
              {!isRegister && (
                <div className="absolute bottom-0 left-0 right-0 h-0.5 bg-indigo-500 rounded-full"></div>
              )}
            </button>
            <button
              onClick={() => { setIsRegister(true); setError(""); }}
              className={`text-lg font-medium pb-2 transition-colors relative ${
                isRegister ? "text-white font-semibold" : "text-gray-400 hover:text-gray-200"
              }`}
            >
              Onboard Tenant
              {isRegister && (
                <div className="absolute bottom-0 left-0 right-0 h-0.5 bg-indigo-500 rounded-full"></div>
              )}
            </button>
          </div>

          {error && (
            <div className="mb-6 p-4 bg-red-900/30 border border-red-500/40 text-red-200 text-xs rounded-xl flex items-center gap-2">
              <span className="w-1.5 h-1.5 rounded-full bg-red-400 shrink-0"></span>
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-5">
            {isRegister && (
              <>
                <div>
                  <label className="block text-xs font-medium text-gray-400 mb-2 uppercase tracking-wider">
                    Company / Tenant Name
                  </label>
                  <div className="relative">
                    <Building2 className="absolute left-3.5 top-3.5 h-5 w-5 text-gray-500" />
                    <input
                      type="text"
                      required
                      value={tenantName}
                      onChange={(e) => setTenantName(e.target.value)}
                      placeholder="e.g. Apex Biotech"
                      className="w-full pl-11 pr-4 py-3 bg-gray-900/50 border border-gray-700 rounded-xl text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent transition-all"
                    />
                  </div>
                </div>

                <div>
                  <label className="block text-xs font-medium text-gray-400 mb-2 uppercase tracking-wider">
                    Administrator Name
                  </label>
                  <div className="relative">
                    <User className="absolute left-3.5 top-3.5 h-5 w-5 text-gray-500" />
                    <input
                      type="text"
                      required
                      value={name}
                      onChange={(e) => setName(e.target.value)}
                      placeholder="e.g. John Doe"
                      className="w-full pl-11 pr-4 py-3 bg-gray-900/50 border border-gray-700 rounded-xl text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent transition-all"
                    />
                  </div>
                </div>
              </>
            )}

            <div>
              <label className="block text-xs font-medium text-gray-400 mb-2 uppercase tracking-wider">
                Email Address
              </label>
              <div className="relative">
                <Mail className="absolute left-3.5 top-3.5 h-5 w-5 text-gray-500" />
                <input
                  type="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="admin@apex.com"
                  className="w-full pl-11 pr-4 py-3 bg-gray-900/50 border border-gray-700 rounded-xl text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent transition-all"
                />
              </div>
            </div>

            <div>
              <div className="flex justify-between items-center mb-2">
                <label className="block text-xs font-medium text-gray-400 uppercase tracking-wider">
                  Password
                </label>
                {!isRegister && (
                  <span className="text-[11px] text-gray-500 cursor-not-allowed">
                    Demo pass: password123
                  </span>
                )}
              </div>
              <div className="relative">
                <KeyRound className="absolute left-3.5 top-3.5 h-5 w-5 text-gray-500" />
                <input
                  type="password"
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••"
                  className="w-full pl-11 pr-4 py-3 bg-gray-900/50 border border-gray-700 rounded-xl text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent transition-all"
                />
              </div>
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full mt-4 flex items-center justify-center gap-2 py-3.5 px-4 bg-indigo-600 hover:bg-indigo-500 disabled:bg-indigo-800 text-white font-medium rounded-xl transition-all shadow-lg hover:shadow-indigo-500/20 focus:outline-none focus:ring-2 focus:ring-indigo-500"
            >
              {loading ? (
                <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin"></div>
              ) : (
                <>
                  {isRegister ? "Launch Tenant" : "Enter Dashboard"}
                  <ArrowRight className="w-4 h-4" />
                </>
              )}
            </button>
          </form>

          {!isRegister && (
            <div className="mt-6 p-3 bg-indigo-950/20 border border-indigo-900/40 rounded-xl text-center">
              <p className="text-xs text-indigo-300 flex items-center justify-center gap-1.5">
                <Sparkles className="w-3.5 h-3.5 text-indigo-400" />
                Try logging in with: <strong>admin@apex.com</strong> / <strong>password123</strong>
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
