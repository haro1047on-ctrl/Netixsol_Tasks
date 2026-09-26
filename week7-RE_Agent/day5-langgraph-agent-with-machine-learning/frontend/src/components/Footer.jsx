import React, { useState } from "react";
import { motion } from "framer-motion";
import {
  Building2,
  MapPin,
  Phone,
  Mail,
  Clock,
  ShieldCheck,
  Sparkles,
  Send,
  CheckCircle2,
  Globe,
  Award,
  ArrowRight,
  Headphones,
  Check,
} from "lucide-react";

export default function Footer({ onOpenAi, onOpenBooking }) {
  const [email, setEmail] = useState("");
  const [subscribed, setSubscribed] = useState(false);

  const handleSubscribe = (e) => {
    e.preventDefault();
    if (!email.trim() || !email.includes("@")) return;
    setSubscribed(true);
    setTimeout(() => {
      setEmail("");
    }, 3000);
  };

  return (
    <footer className="relative w-full overflow-hidden border-t border-white/10 bg-[#060912] text-slate-300">
      {/* 1. Elegant High-Resolution Architectural Mansion Background Image */}
      <div className="absolute inset-0 pointer-events-none select-none overflow-hidden">
        <img
          src="/footer-bg.jpg"
          alt="Luxury Architectural Residence at Dusk"
          className="w-full h-full object-cover object-bottom opacity-28 scale-105 filter blur-[0.5px]"
          loading="lazy"
        />
        {/* Layered Gradient Overlays for Guaranteed Text Legibility & Seamless Transition */}
        <div className="absolute inset-0 bg-gradient-to-b from-[#090d16] via-[#070b14]/90 to-[#04060b]/98" />
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top,_rgba(245,180,100,0.07),_transparent_65%)]" />
        <div className="absolute inset-x-0 top-0 h-24 bg-gradient-to-b from-[#090d16] to-transparent" />
      </div>

      <div className="relative z-10 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pt-16 pb-12">
        {/* 2. Top Architectural Highlights Ribbon */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 pb-12 mb-12 border-b border-white/10">
          <div className="flex items-center gap-3.5 p-3.5 rounded-2xl bg-white/[0.03] border border-white/10 backdrop-blur-md">
            <div className="w-10 h-10 rounded-xl bg-amber-400/10 border border-amber-400/30 flex items-center justify-center flex-shrink-0 text-amber-300 shadow-[0_0_15px_rgba(245,180,100,0.15)]">
              <ShieldCheck className="w-5 h-5" />
            </div>
            <div>
              <div className="text-white text-xs font-semibold tracking-wide">100% Verified Titles</div>
              <div className="text-[11px] text-slate-400">CDA, LDA & RDA vetted</div>
            </div>
          </div>

          <div className="flex items-center gap-3.5 p-3.5 rounded-2xl bg-white/[0.03] border border-white/10 backdrop-blur-md">
            <div className="w-10 h-10 rounded-xl bg-sky-400/10 border border-sky-400/30 flex items-center justify-center flex-shrink-0 text-sky-300 shadow-[0_0_15px_rgba(56,189,248,0.15)]">
              <Headphones className="w-5 h-5" />
            </div>
            <div>
              <div className="text-white text-xs font-semibold tracking-wide">AI Voice Consultant</div>
              <div className="text-[11px] text-slate-400">Conversational Urdu & English</div>
            </div>
          </div>

          <div className="flex items-center gap-3.5 p-3.5 rounded-2xl bg-white/[0.03] border border-white/10 backdrop-blur-md">
            <div className="w-10 h-10 rounded-xl bg-amber-400/10 border border-amber-400/30 flex items-center justify-center flex-shrink-0 text-amber-300 shadow-[0_0_15px_rgba(245,180,100,0.15)]">
              <Award className="w-5 h-5" />
            </div>
            <div>
              <div className="text-white text-xs font-semibold tracking-wide">Curated Estates</div>
              <div className="text-[11px] text-slate-400">Islamabad, Lahore, Pindi</div>
            </div>
          </div>

          <div className="flex items-center gap-3.5 p-3.5 rounded-2xl bg-white/[0.03] border border-white/10 backdrop-blur-md">
            <div className="w-10 h-10 rounded-xl bg-emerald-400/10 border border-emerald-400/30 flex items-center justify-center flex-shrink-0 text-emerald-300 shadow-[0_0_15px_rgba(52,211,153,0.15)]">
              <Globe className="w-5 h-5" />
            </div>
            <div>
              <div className="text-white text-xs font-semibold tracking-wide">Overseas Desk</div>
              <div className="text-[11px] text-slate-400">Seamless diaspora advisory</div>
            </div>
          </div>
        </div>

        {/* 3. Main Footer Multi-Column Grid */}
        <div className="grid grid-cols-1 md:grid-cols-12 gap-10 lg:gap-12 pb-14 border-b border-white/10 text-left">
          {/* Column 1: About Us & Brand Persona (5 cols) */}
          <div className="md:col-span-12 lg:col-span-5 space-y-5">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-amber-400 to-amber-600 flex items-center justify-center text-slate-950 shadow-[0_0_20px_rgba(245,180,100,0.4)]">
                <Building2 className="w-5 h-5" />
              </div>
              <div>
                <span className="font-heading text-lg font-bold text-white tracking-tight">RealEstate Hub</span>
                <span className="block text-[10px] font-mono tracking-widest text-amber-300/90 uppercase">Pakistan Luxury Portal</span>
              </div>
            </div>

            {/* About Us Paragraph */}
            <div className="space-y-3">
              <h4 className="text-xs font-semibold uppercase tracking-widest text-amber-300 font-mono">About Us</h4>
              <p className="text-xs text-slate-300 font-light leading-relaxed">
                RealEstate Hub is Pakistan’s premier AI-powered luxury real estate platform. We curate
                the most prestigious residential villas, penthouses, and prime commercial plots across Islamabad,
                Lahore, and Rawalpindi.
              </p>
              <p className="text-xs text-slate-400 font-light leading-relaxed">
                Combining human architectural expertise with autonomous LangGraph AI multi-agent workflows and
                fluent Urdu voice intelligence, we provide discerning homeowners, overseas Pakistanis, and institutional
                investors with unmatched transparency, verified titles, and seamless site appointments.
              </p>
            </div>

            {/* Micro Stats */}
            <div className="flex items-center gap-6 pt-1">
              <div>
                <div className="text-lg font-heading font-semibold text-white">750+</div>
                <div className="text-[10px] text-slate-400 uppercase tracking-wider">Verified Properties</div>
              </div>
              <div className="w-[1px] h-8 bg-white/10" />
              <div>
                <div className="text-lg font-heading font-semibold text-amber-300">PKR 50B+</div>
                <div className="text-[10px] text-slate-400 uppercase tracking-wider">Portfolio Under Advisory</div>
              </div>
              <div className="w-[1px] h-8 bg-white/10" />
              <div>
                <div className="text-lg font-heading font-semibold text-emerald-400">99.8%</div>
                <div className="text-[10px] text-slate-400 uppercase tracking-wider">Title Accuracy</div>
              </div>
            </div>
          </div>

          {/* Column 2: Prime Localities (2 cols) */}
          <div className="md:col-span-4 lg:col-span-2 space-y-4">
            <h4 className="text-xs font-semibold uppercase tracking-widest text-white font-mono flex items-center gap-2">
              <MapPin className="w-3.5 h-3.5 text-amber-300" />
              <span>Prime Locations</span>
            </h4>
            <ul className="space-y-2.5 text-xs text-slate-400">
              <li>
                <a href="#properties" className="hover:text-amber-300 transition-colors flex items-center gap-1.5">
                  <span className="text-slate-600">›</span> Sector F-6 & F-7, Islamabad
                </a>
              </li>
              <li>
                <a href="#properties" className="hover:text-amber-300 transition-colors flex items-center gap-1.5">
                  <span className="text-slate-600">›</span> DHA Phase 2 & 5, Islamabad
                </a>
              </li>
              <li>
                <a href="#properties" className="hover:text-amber-300 transition-colors flex items-center gap-1.5">
                  <span className="text-slate-600">›</span> Bahria Golf City, Murree Exp
                </a>
              </li>
              <li>
                <a href="#properties" className="hover:text-amber-300 transition-colors flex items-center gap-1.5">
                  <span className="text-slate-600">›</span> DHA Phase 5 & 6, Lahore
                </a>
              </li>
              <li>
                <a href="#properties" className="hover:text-amber-300 transition-colors flex items-center gap-1.5">
                  <span className="text-slate-600">›</span> Gulberg III & Cantt, Lahore
                </a>
              </li>
              <li>
                <a href="#properties" className="hover:text-amber-300 transition-colors flex items-center gap-1.5">
                  <span className="text-slate-600">›</span> Bahria Town, Rawalpindi
                </a>
              </li>
            </ul>
          </div>

          {/* Column 3: AI Intelligence & Services (2 cols) */}
          <div className="md:col-span-4 lg:col-span-2 space-y-4">
            <h4 className="text-xs font-semibold uppercase tracking-widest text-white font-mono flex items-center gap-2">
              <Sparkles className="w-3.5 h-3.5 text-amber-300" />
              <span>AI & Services</span>
            </h4>
            <ul className="space-y-2.5 text-xs text-slate-400">
              <li>
                <button
                  onClick={onOpenAi}
                  className="hover:text-amber-300 transition-colors flex items-center gap-1.5 cursor-pointer text-left"
                >
                  <span className="text-slate-600">›</span> Urdu AI Voice Consultant
                </button>
              </li>
              <li>
                <button
                  onClick={onOpenAi}
                  className="hover:text-amber-300 transition-colors flex items-center gap-1.5 cursor-pointer text-left"
                >
                  <span className="text-slate-600">›</span> Smart Property Recommender
                </button>
              </li>
              <li>
                <button
                  onClick={onOpenBooking}
                  className="hover:text-amber-300 transition-colors flex items-center gap-1.5 cursor-pointer text-left"
                >
                  <span className="text-slate-600">›</span> VIP Private Site Visits
                </button>
              </li>
              <li>
                <a href="#properties" className="hover:text-amber-300 transition-colors flex items-center gap-1.5">
                  <span className="text-slate-600">›</span> Real Marla/Kanal Estimator
                </a>
              </li>
              <li>
                <a href="#properties" className="hover:text-amber-300 transition-colors flex items-center gap-1.5">
                  <span className="text-slate-600">›</span> Off-Market Luxury Mansions
                </a>
              </li>
              <li>
                <a href="#properties" className="hover:text-amber-300 transition-colors flex items-center gap-1.5">
                  <span className="text-slate-600">›</span> Title & Deed Due Diligence
                </a>
              </li>
            </ul>
          </div>

          {/* Column 4: Contact & VIP Newsletter (3 cols) */}
          <div className="md:col-span-4 lg:col-span-3 space-y-5">
            <div className="space-y-3">
              <h4 className="text-xs font-semibold uppercase tracking-widest text-white font-mono flex items-center gap-2">
                <Phone className="w-3.5 h-3.5 text-amber-300" />
                <span>Headquarters</span>
              </h4>
              <div className="space-y-2 text-xs text-slate-300">
                <div className="flex items-start gap-2.5">
                  <MapPin className="w-3.5 h-3.5 text-amber-300 flex-shrink-0 mt-0.5" />
                  <span className="font-light">Executive Tower, Jinnah Ave, Sector F-7, Islamabad</span>
                </div>
                <div className="flex items-center gap-2.5">
                  <Phone className="w-3.5 h-3.5 text-amber-300 flex-shrink-0" />
                  <a href="tel:+92518849000" className="hover:text-amber-300 transition-colors font-mono">
                    +92 (051) 884-9000
                  </a>
                </div>
                <div className="flex items-center gap-2.5">
                  <Mail className="w-3.5 h-3.5 text-amber-300 flex-shrink-0" />
                  <a href="mailto:concierge@realestatehub.pk" className="hover:text-amber-300 transition-colors">
                    concierge@realestatehub.pk
                  </a>
                </div>
                <div className="flex items-center gap-2.5 text-slate-400">
                  <Clock className="w-3.5 h-3.5 text-slate-500 flex-shrink-0" />
                  <span>Mon – Sat: 9:00 AM – 8:00 PM PST</span>
                </div>
              </div>
            </div>

            {/* VIP Newsletter Dispatch */}
            <div className="p-4 rounded-2xl bg-[#0a1122]/90 border border-white/10 space-y-2.5">
              <div className="text-xs font-medium text-white flex items-center gap-1.5">
                <Sparkles className="w-3.5 h-3.5 text-amber-300" />
                <span>Private Client Dispatch</span>
              </div>
              <p className="text-[11px] text-slate-400 font-light leading-relaxed">
                Receive confidential off-market villa drops and market yields directly to your inbox.
              </p>

              {subscribed ? (
                <div className="py-2 px-3 rounded-xl bg-emerald-500/15 border border-emerald-500/30 text-emerald-300 text-xs flex items-center gap-2">
                  <Check className="w-3.5 h-3.5 flex-shrink-0" />
                  <span>Subscribed to VIP Dispatch!</span>
                </div>
              ) : (
                <form onSubmit={handleSubscribe} className="flex items-center gap-2">
                  <input
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="Your email address..."
                    required
                    className="flex-1 px-3 py-2 rounded-xl bg-white/[0.06] border border-white/15 text-white placeholder:text-slate-500 text-xs focus:outline-none focus:border-amber-400/50"
                  />
                  <button
                    type="submit"
                    className="p-2 rounded-xl bg-gradient-to-r from-amber-400 to-amber-500 hover:from-amber-300 hover:to-amber-400 text-slate-950 font-bold cursor-pointer transition-all shadow-[0_0_15px_rgba(245,180,100,0.3)]"
                    title="Subscribe"
                  >
                    <Send className="w-3.5 h-3.5" />
                  </button>
                </form>
              )}
            </div>
          </div>
        </div>

        {/* 4. Bottom Copyright & Legal Line */}
        <div className="pt-8 flex flex-col sm:flex-row items-center justify-between gap-4 text-xs text-slate-400">
          <div className="flex items-center gap-2">
            <span>© {new Date().getFullYear()} Sahi RealEstate Hub (Pvt.) Ltd.</span>
            <span className="text-slate-600">•</span>
            <span>All rights reserved.</span>
          </div>

          <div className="flex flex-wrap items-center justify-center gap-4 text-[11px] text-slate-400">
            <span className="text-amber-300/80 font-mono">LangGraph StateGraph</span>
            <span className="text-slate-600">•</span>
            <span className="text-amber-300/80 font-mono">Deepgram Nova-3 Urdu</span>
            <span className="text-slate-600">•</span>
            <span className="text-amber-300/80 font-mono">Vapi Voice Stream</span>
          </div>

          <div className="flex items-center gap-4 text-[11px] text-slate-500">
            <span className="hover:text-slate-300 transition-colors cursor-pointer">Privacy Policy</span>
            <span>•</span>
            <span className="hover:text-slate-300 transition-colors cursor-pointer">Terms of Service</span>
            <span>•</span>
            <span className="hover:text-slate-300 transition-colors cursor-pointer">CDA/RDA Compliance</span>
          </div>
        </div>
      </div>
    </footer>
  );
}
