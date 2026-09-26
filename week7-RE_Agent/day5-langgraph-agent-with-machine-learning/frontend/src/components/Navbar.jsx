import React, { useState, useEffect } from "react";
import { Home, Sparkles, Shield, User, LogIn, LogOut, PhoneCall, Calendar, ArrowUpRight } from "lucide-react";

export default function Navbar({
  currentUser,
  activeTab,
  setActiveTab,
  onOpenAuth,
  onLogout,
  onOpenAiWidget,
  backendConnected,
}) {
  const [scrolled, setScrolled] = useState(false);

  useEffect(() => {
    const handleScroll = () => {
      setScrolled(window.scrollY > 20);
    };
    window.addEventListener("scroll", handleScroll, { passive: true });
    return () => window.removeEventListener("scroll", handleScroll);
  }, []);

  return (
    <header
      className={`fixed top-0 left-0 right-0 z-50 w-full transition-all duration-300 ${
        scrolled
          ? "py-3 bg-[#06080e]/75 backdrop-blur-2xl border-b border-white/10 shadow-2xl shadow-black/60"
          : "py-5 bg-gradient-to-b from-black/60 via-black/20 to-transparent"
      }`}
    >
      <div className="max-w-7xl mx-auto px-4 sm:px-8 flex items-center justify-between gap-4">
        {/* Brand / Logo (matching reference photo) */}
        <div
          onClick={() => setActiveTab("properties")}
          className="flex items-center gap-3 cursor-pointer group select-none"
        >
          <div className="w-9 h-9 rounded-xl liquid-glass flex items-center justify-center border border-white/20 group-hover:border-[#7ca38c]/50 group-hover:shadow-[0_0_15px_rgba(124,163,140,0.25)] transition-all">
            <Home className="w-5 h-5 text-white group-hover:text-[#c4dbcd] transition-colors" />
          </div>
          <div className="flex items-center gap-2">
            <span className="font-heading font-bold text-lg sm:text-xl text-white tracking-tight">
              RealEstate Hub
            </span>
          </div>
        </div>

        {/* Center Navigation Links (matching reference photo) */}
        <nav className="hidden md:flex items-center gap-7">
          <button
            onClick={() => setActiveTab("properties")}
            className="relative py-1 text-xs sm:text-sm font-medium transition-colors text-white hover:text-white"
          >
            <span>Buy</span>
            {activeTab === "properties" && (
              <span className="absolute -bottom-1.5 left-0 right-0 h-[2px] bg-white rounded-full shadow-[0_0_8px_rgba(255,255,255,0.7)] animate-in fade-in duration-300" />
            )}
          </button>

          <button
            onClick={() => {
              setActiveTab("properties");
              const el = document.getElementById("properties-section");
              if (el) el.scrollIntoView({ behavior: "smooth" });
            }}
            className="text-xs sm:text-sm font-medium text-slate-300 hover:text-white transition-colors"
          >
            Rent
          </button>

          <button
            onClick={() => {
              setActiveTab("properties");
              const el = document.getElementById("properties-section");
              if (el) el.scrollIntoView({ behavior: "smooth" });
            }}
            className="text-xs sm:text-sm font-medium text-slate-300 hover:text-white transition-colors"
          >
            Commercial
          </button>

          <button
            onClick={() => setActiveTab("crm")}
            className={`relative py-1 text-xs sm:text-sm font-medium transition-colors ${
              activeTab === "crm" ? "text-white font-semibold" : "text-slate-300 hover:text-white"
            }`}
          >
            <span>Schedules</span>
            {activeTab === "crm" && (
              <span className="absolute -bottom-1.5 left-0 right-0 h-[2px] bg-[#8fa89b] rounded-full shadow-[0_0_8px_rgba(143,168,155,0.7)]" />
            )}
          </button>

          {currentUser?.role === "admin" && (
            <button
              onClick={() => setActiveTab("admin")}
              className={`relative py-1 text-xs sm:text-sm font-medium transition-colors ${
                activeTab === "admin" ? "text-amber-300 font-semibold" : "text-amber-200/80 hover:text-amber-200"
              }`}
            >
              <span>Admin</span>
              {activeTab === "admin" && (
                <span className="absolute -bottom-1.5 left-0 right-0 h-[2px] bg-amber-400 rounded-full shadow-[0_0_8px_rgba(251,191,36,0.7)]" />
              )}
            </button>
          )}

          <button
            onClick={() => {
              const el = document.getElementById("features-section");
              if (el) el.scrollIntoView({ behavior: "smooth" });
            }}
            className="text-xs sm:text-sm font-medium text-slate-300 hover:text-white transition-colors"
          >
            About
          </button>

          <button
            onClick={() => {
              setActiveTab("properties");
              setTimeout(() => {
                const el = document.getElementById("contact");
                if (el) el.scrollIntoView({ behavior: "smooth" });
              }, 50);
            }}
            className="text-xs sm:text-sm font-medium text-slate-300 hover:text-white transition-colors cursor-pointer"
          >
            Contact
          </button>
        </nav>

        {/* Right Action: "Talk to us ↗" and User Auth */}
        <div className="flex items-center gap-3">
          {/* Active Connection Indicator */}
          <div
            title={backendConnected ? "AI LangGraph Agent Online" : "Connecting to API..."}
            className="hidden lg:flex items-center gap-1.5 h-9 px-3 rounded-full liquid-glass text-[11px] text-slate-300 border border-white/10"
          >
            <span
              className={`w-2 h-2 rounded-full ${
                backendConnected ? "bg-emerald-400 shadow-[0_0_8px_rgba(52,211,153,0.8)] animate-pulse" : "bg-amber-400"
              }`}
            />
            <span className="text-[10px] uppercase font-semibold tracking-wider text-slate-300">
              {backendConnected ? "AI Live" : "Offline"}
            </span>
          </div>

          {/* "Talk to us ↗" Button matching exact header button size & theme */}
          <button
            onClick={onOpenAiWidget}
            className="h-9 px-4 rounded-full liquid-glass hover:bg-white/[0.12] border border-white/15 hover:border-amber-400/50 text-slate-200 hover:text-white transition-all flex items-center gap-1.5 cursor-pointer group shadow-sm text-xs font-medium"
            title="Talk with AI Voice & Chat Consultant"
          >
            <Sparkles className="w-3.5 h-3.5 text-amber-300 group-hover:rotate-12 transition-transform" />
            <span>Talk to us</span>
            <ArrowUpRight className="w-3.5 h-3.5 text-amber-300/80 group-hover:translate-x-0.5 group-hover:-translate-y-0.5 transition-transform" />
          </button>

          {/* User Profile / Sign In */}
          {currentUser ? (
            <div className="flex items-center gap-2">
              <div className="h-9 flex items-center gap-2 px-3.5 rounded-full liquid-glass border border-white/15">
                <div
                  className={`w-5 h-5 rounded-full flex items-center justify-center text-[10px] font-bold ${
                    currentUser.role === "admin"
                      ? "bg-amber-500/30 text-amber-300 border border-amber-500/40"
                      : "bg-[#24372c] text-[#c2decb] border border-[#3f5d4a]"
                  }`}
                >
                  {currentUser.name ? currentUser.name.charAt(0).toUpperCase() : "U"}
                </div>
                <span className="text-xs text-white font-medium hidden sm:inline truncate max-w-[100px]">
                  {currentUser.name}
                </span>
              </div>
              <button
                onClick={onLogout}
                title="Logout"
                className="h-9 w-9 rounded-full liquid-glass flex items-center justify-center text-slate-400 hover:text-red-400 hover:border-red-500/30 transition-colors"
              >
                <LogOut className="w-3.5 h-3.5" />
              </button>
            </div>
          ) : (
            <button
              onClick={onOpenAuth}
              className="h-9 px-4 rounded-full liquid-glass hover:bg-white/[0.12] border border-white/15 hover:border-amber-400/50 text-slate-200 hover:text-white transition-all flex items-center gap-1.5 cursor-pointer group shadow-sm text-xs font-medium"
              title="Sign In"
            >
              <User className="w-3.5 h-3.5 text-amber-300 group-hover:scale-110 transition-transform" />
              <span className="hidden sm:inline">Sign In</span>
            </button>
          )}
        </div>
      </div>
    </header>
  );
}
