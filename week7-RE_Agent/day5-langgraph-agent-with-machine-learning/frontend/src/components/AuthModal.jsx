import React, { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  X,
  Lock,
  Mail,
  User,
  Phone,
  ArrowRight,
  Home,
  Building2,
  ShieldCheck,
  Sparkles,
  CheckCircle2,
} from "lucide-react";
import confetti from "canvas-confetti";

export default function AuthModal({ isOpen, onClose, onAuthSuccess }) {
  if (!isOpen) return null;

  const [mode, setMode] = useState("signin"); // "signin" | "signup"
  const [role, setRole] = useState("user"); // "user" | "admin"
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [phone, setPhone] = useState("");
  const [loading, setLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState("");

  const handleSubmit = async (e) => {
    e.preventDefault();
    setErrorMsg("");
    setLoading(true);

    try {
      const endpoint = mode === "signin" ? "/api/auth/login" : "/api/auth/signup";
      const payload =
        mode === "signin"
          ? { email, password }
          : { name, email, password, role, phone };

      const res = await fetch(endpoint, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const data = await res.json();

      if (!res.ok || !data.ok) {
        throw new Error(data.error || "Authentication failed. Please check your credentials.");
      }

      // Elegant golden champagne celebration burst on login/signup
      confetti({
        particleCount: 65,
        spread: 65,
        origin: { y: 0.6 },
        colors: ["#fbbf24", "#f59e0b", "#fef3c7", "#ffffff", "#d97706"],
      });

      onAuthSuccess(data.user, data.token);
      onClose();
    } catch (err) {
      setErrorMsg(err.message || "Failed to authenticate. Please check your credentials.");
    } finally {
      setLoading(false);
    }
  };

  const fillDemo = (demoRole) => {
    setErrorMsg("");
    if (demoRole === "admin") {
      setMode("signin");
      setEmail("admin@realestatehub.pk");
      setPassword("admin123");
    } else {
      setMode("signin");
      setEmail("user@realestatehub.pk");
      setPassword("user123");
    }
  };

  return (
    <AnimatePresence>
      <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
        {/* Backdrop with Smooth Fade & Twilight Obsidian Blur */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          onClick={onClose}
          className="fixed inset-0 bg-[#060910]/80 backdrop-blur-xl transition-opacity"
        />

        {/* Ambient Villa Interior Warm Glow Leak */}
        <div className="absolute w-[450px] h-[450px] rounded-full bg-[radial-gradient(circle,_rgba(245,180,100,0.12)_0%,_transparent_70%)] blur-3xl pointer-events-none -translate-y-10" />
        <div className="absolute w-[400px] h-[400px] rounded-full bg-[radial-gradient(circle,_rgba(56,189,248,0.05)_0%,_transparent_70%)] blur-3xl pointer-events-none translate-y-20 translate-x-20" />

        {/* Main Modal Dialog Card (Liquid Glass Obsidian with Gold Accents) */}
        <motion.div
          initial={{ opacity: 0, scale: 0.94, y: 15 }}
          animate={{ opacity: 1, scale: 1, y: 0 }}
          exit={{ opacity: 0, scale: 0.94, y: 15 }}
          transition={{ duration: 0.35, ease: [0.16, 1, 0.3, 1] }}
          onClick={(e) => e.stopPropagation()}
          className="relative z-10 w-full max-w-[430px] p-7 sm:p-9 rounded-3xl bg-[#0e1422]/90 backdrop-blur-3xl border border-white/15 shadow-[0_30px_90px_rgba(0,0,0,0.9),inset_0_1px_1px_rgba(255,255,255,0.15)] overflow-hidden text-left"
        >
          {/* Subtle Specular Gold Top Rim Highlight */}
          <div className="absolute top-0 inset-x-8 h-[1.5px] bg-gradient-to-r from-transparent via-amber-400/50 to-transparent pointer-events-none" />

          {/* Close Button */}
          <button
            onClick={onClose}
            className="absolute top-5 right-5 w-8 h-8 rounded-full bg-white/[0.06] hover:bg-white/[0.14] border border-white/15 hover:border-white/30 flex items-center justify-center text-slate-300 hover:text-white transition-all cursor-pointer shadow-sm"
          >
            <X className="w-4 h-4" />
          </button>

          {/* Header (Architectural Luxury Aesthetic) */}
          <div className="text-center mb-6">
            <div className="relative w-12 h-12 mx-auto mb-3 flex items-center justify-center">
              <div className="absolute inset-0 rounded-2xl bg-amber-400/20 blur-md" />
              <div className="relative w-12 h-12 rounded-2xl bg-white/[0.08] backdrop-blur-xl border border-white/20 flex items-center justify-center shadow-inner">
                <Building2 className="w-5 h-5 text-amber-300" />
              </div>
            </div>

            <h2 className="font-display-serif text-3xl font-normal text-white tracking-tight">
              {mode === "signin" ? "Welcome Back" : "Create Account"}
            </h2>
            <p className="text-xs text-slate-400 mt-1.5 font-light leading-relaxed max-w-xs mx-auto">
              {mode === "signin"
                ? "Access your private portfolio, site visit schedule & AI consultant"
                : "Register to explore 750+ verified luxury properties across Pakistan"}
            </p>
          </div>

          {/* Tab Switcher: Sign In vs Create Account */}
          <div className="flex p-1 rounded-full bg-black/40 border border-white/10 mb-6">
            <button
              type="button"
              onClick={() => {
                setMode("signin");
                setErrorMsg("");
              }}
              className={`flex-1 py-2 text-xs font-semibold rounded-full transition-all cursor-pointer ${
                mode === "signin"
                  ? "bg-gradient-to-r from-amber-400 via-amber-300 to-amber-500 text-slate-950 font-bold shadow-[0_2px_12px_rgba(245,180,100,0.3)]"
                  : "text-slate-400 hover:text-slate-200"
              }`}
            >
              Sign In
            </button>
            <button
              type="button"
              onClick={() => {
                setMode("signup");
                setErrorMsg("");
              }}
              className={`flex-1 py-2 text-xs font-semibold rounded-full transition-all cursor-pointer ${
                mode === "signup"
                  ? "bg-gradient-to-r from-amber-400 via-amber-300 to-amber-500 text-slate-950 font-bold shadow-[0_2px_12px_rgba(245,180,100,0.3)]"
                  : "text-slate-400 hover:text-slate-200"
              }`}
            >
              Create Account
            </button>
          </div>

          {/* Error Alert */}
          {errorMsg && (
            <motion.div
              initial={{ opacity: 0, y: -6 }}
              animate={{ opacity: 1, y: 0 }}
              className="mb-4 p-3 rounded-2xl bg-red-500/10 border border-red-500/25 text-red-200 text-xs flex items-center gap-2 shadow-sm"
            >
              <span className="w-1.5 h-1.5 rounded-full bg-red-400 flex-shrink-0" />
              <span>{errorMsg}</span>
            </motion.div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            {mode === "signup" && (
              <>
                {/* Role Picker */}
                <div>
                  <label className="block text-[10px] font-semibold tracking-widest text-slate-300 uppercase mb-1.5">
                    Account Type
                  </label>
                  <div className="grid grid-cols-2 gap-2">
                    <button
                      type="button"
                      onClick={() => setRole("user")}
                      className={`py-2 px-3 rounded-xl text-xs font-medium flex items-center justify-center gap-2 border transition-all cursor-pointer ${
                        role === "user"
                          ? "bg-amber-400/15 border-amber-400/50 text-amber-200 shadow-[0_0_15px_rgba(245,180,100,0.15)]"
                          : "bg-white/[0.04] border-white/10 text-slate-400 hover:text-white"
                      }`}
                    >
                      <User className={`w-3.5 h-3.5 ${role === "user" ? "text-amber-300" : "text-slate-400"}`} />
                      <span>Client / Buyer</span>
                    </button>
                    <button
                      type="button"
                      onClick={() => setRole("admin")}
                      className={`py-2 px-3 rounded-xl text-xs font-medium flex items-center justify-center gap-2 border transition-all cursor-pointer ${
                        role === "admin"
                          ? "bg-amber-400/15 border-amber-400/50 text-amber-200 shadow-[0_0_15px_rgba(245,180,100,0.15)]"
                          : "bg-white/[0.04] border-white/10 text-slate-400 hover:text-white"
                      }`}
                    >
                      <ShieldCheck className={`w-3.5 h-3.5 ${role === "admin" ? "text-amber-300" : "text-slate-400"}`} />
                      <span>Administrator</span>
                    </button>
                  </div>
                </div>

                {/* Name */}
                <div>
                  <label className="block text-[10px] font-semibold tracking-widest text-slate-300 uppercase mb-1.5">
                    Full Name
                  </label>
                  <div className="relative">
                    <User className="w-4 h-4 text-amber-300/70 absolute left-3.5 top-1/2 -translate-y-1/2" />
                    <input
                      type="text"
                      required
                      value={name}
                      onChange={(e) => setName(e.target.value)}
                      placeholder="Tariq Mehmood"
                      className="w-full pl-10 pr-3.5 py-2.5 rounded-xl bg-white/[0.04] border border-white/12 text-white placeholder-slate-500 text-xs focus:outline-none focus:border-amber-400/60 focus:bg-white/[0.07] focus:ring-1 focus:ring-amber-400/30 transition-all"
                    />
                  </div>
                </div>

                {/* Phone */}
                <div>
                  <label className="block text-[10px] font-semibold tracking-widest text-slate-300 uppercase mb-1.5">
                    Phone Number
                  </label>
                  <div className="relative">
                    <Phone className="w-4 h-4 text-amber-300/70 absolute left-3.5 top-1/2 -translate-y-1/2" />
                    <input
                      type="tel"
                      value={phone}
                      onChange={(e) => setPhone(e.target.value)}
                      placeholder="+92 300 1234567"
                      className="w-full pl-10 pr-3.5 py-2.5 rounded-xl bg-white/[0.04] border border-white/12 text-white placeholder-slate-500 text-xs focus:outline-none focus:border-amber-400/60 focus:bg-white/[0.07] focus:ring-1 focus:ring-amber-400/30 transition-all"
                    />
                  </div>
                </div>
              </>
            )}

            {/* Email */}
            <div>
              <label className="block text-[10px] font-semibold tracking-widest text-slate-300 uppercase mb-1.5">
                Email Address
              </label>
              <div className="relative">
                <Mail className="w-4 h-4 text-amber-300/70 absolute left-3.5 top-1/2 -translate-y-1/2" />
                <input
                  type="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="client@realestatehub.pk"
                  className="w-full pl-10 pr-3.5 py-2.5 rounded-xl bg-white/[0.04] border border-white/12 text-white placeholder-slate-500 text-xs focus:outline-none focus:border-amber-400/60 focus:bg-white/[0.07] focus:ring-1 focus:ring-amber-400/30 transition-all"
                />
              </div>
            </div>

            {/* Password */}
            <div>
              <label className="block text-[10px] font-semibold tracking-widest text-slate-300 uppercase mb-1.5">
                Password
              </label>
              <div className="relative">
                <Lock className="w-4 h-4 text-amber-300/70 absolute left-3.5 top-1/2 -translate-y-1/2" />
                <input
                  type="password"
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••"
                  className="w-full pl-10 pr-3.5 py-2.5 rounded-xl bg-white/[0.04] border border-white/12 text-white placeholder-slate-500 text-xs focus:outline-none focus:border-amber-400/60 focus:bg-white/[0.07] focus:ring-1 focus:ring-amber-400/30 transition-all"
                />
              </div>
            </div>

            {/* Submit Action Button (Liquid Golden Amber CTA matching theme) */}
            <motion.button
              whileHover={{ scale: 1.02, y: -1 }}
              whileTap={{ scale: 0.98 }}
              type="submit"
              disabled={loading}
              className="relative w-full py-3 px-4 rounded-full bg-gradient-to-r from-amber-400 via-amber-300 to-amber-500 hover:from-amber-300 hover:to-amber-400 text-slate-950 font-bold text-xs sm:text-sm flex items-center justify-center gap-2 group/btn cursor-pointer shadow-[0_4px_20px_rgba(245,180,100,0.35)] hover:shadow-[0_6px_28px_rgba(245,180,100,0.6)] transition-all overflow-hidden mt-3"
            >
              {/* Dynamic Shimmer Light Reflection Sweep on Hover */}
              <div className="absolute inset-0 -translate-x-full group-hover/btn:translate-x-full transition-transform duration-700 bg-gradient-to-r from-transparent via-white/50 to-transparent pointer-events-none" />

              {loading ? (
                <span className="inline-block w-4 h-4 border-2 border-slate-950/30 border-t-slate-950 rounded-full animate-spin" />
              ) : (
                <>
                  {/* Lively Pulse Radar Dot */}
                  <span className="relative flex h-2 w-2 flex-shrink-0">
                    <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-slate-950 opacity-75" />
                    <span className="relative inline-flex rounded-full h-2 w-2 bg-slate-950" />
                  </span>

                  <span>{mode === "signin" ? "Sign In to Dashboard" : "Complete Registration"}</span>
                  <ArrowRight className="w-4 h-4 text-slate-950/80 group-hover/btn:translate-x-1 transition-transform" />
                </>
              )}
            </motion.button>
          </form>

          {/* 1-Click Demo Accounts (Obsidian Liquid Glass with Gold Accents) */}
          <div className="mt-6 pt-5 border-t border-white/10">
            <div className="text-[10px] font-mono tracking-widest text-slate-400 text-center mb-3 uppercase flex items-center justify-center gap-2">
              <div className="w-8 h-[1px] bg-gradient-to-r from-transparent via-amber-400/30 to-transparent" />
              <span>1-Click Demo Access</span>
              <div className="w-8 h-[1px] bg-gradient-to-r from-transparent via-amber-400/30 to-transparent" />
            </div>

            <div className="grid grid-cols-2 gap-2.5">
              <motion.button
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.98 }}
                type="button"
                onClick={() => fillDemo("admin")}
                className="py-2.5 px-3 rounded-xl bg-white/[0.05] hover:bg-white/[0.1] border border-white/12 hover:border-amber-400/40 text-slate-200 hover:text-white text-xs font-medium flex items-center justify-center gap-2 transition-all cursor-pointer group shadow-sm"
              >
                <ShieldCheck className="w-3.5 h-3.5 text-amber-300 group-hover:scale-110 transition-transform" />
                <span>Admin Demo</span>
              </motion.button>

              <motion.button
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.98 }}
                type="button"
                onClick={() => fillDemo("user")}
                className="py-2.5 px-3 rounded-xl bg-white/[0.05] hover:bg-white/[0.1] border border-white/12 hover:border-amber-400/40 text-slate-200 hover:text-white text-xs font-medium flex items-center justify-center gap-2 transition-all cursor-pointer group shadow-sm"
              >
                <User className="w-3.5 h-3.5 text-amber-300 group-hover:scale-110 transition-transform" />
                <span>Client Demo</span>
              </motion.button>
            </div>
          </div>
        </motion.div>
      </div>
    </AnimatePresence>
  );
}
