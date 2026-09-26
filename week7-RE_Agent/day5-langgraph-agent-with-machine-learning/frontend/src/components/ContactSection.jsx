import React, { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Mail,
  Phone,
  MapPin,
  Sparkles,
  Send,
  CheckCircle2,
  Clock,
  ShieldCheck,
  Building2,
  MessageSquare,
  ArrowRight,
  Headphones,
  User,
  Tag,
  AlertCircle,
  ExternalLink,
} from "lucide-react";
import confetti from "canvas-confetti";

export default function ContactSection({ onOpenAi, onOpenBooking }) {
  const [formData, setFormData] = useState({
    name: "",
    email: "",
    phone: "",
    inquiry_type: "Buy Luxury Villa",
    city: "Islamabad",
    budget: "5 - 10 Crore",
    message: "",
  });

  const [loading, setLoading] = useState(false);
  const [submitted, setSubmitted] = useState(false);
  const [errorMsg, setErrorMsg] = useState("");

  const inquiryOptions = [
    "Buy Luxury Villa",
    "Sell an Estate",
    "Private Site Visit",
    "Investment Advisory",
    "Overseas Client Desk",
  ];

  const cityOptions = ["Islamabad", "Lahore", "Rawalpindi"];

  const budgetOptions = [
    "Under 2 Crore",
    "2 - 5 Crore",
    "5 - 10 Crore",
    "10 - 25 Crore",
    "25+ Crore",
  ];

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!formData.name.trim() || !formData.email.trim() || !formData.message.trim()) {
      setErrorMsg("Please fill in your name, email, and message.");
      return;
    }

    setLoading(true);
    setErrorMsg("");

    try {
      const res = await fetch("/api/contact", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(formData),
      });

      const data = await res.json();
      if (!res.ok || !data.ok) {
        throw new Error(data.error || "Failed to dispatch inquiry. Please try again.");
      }

      setSubmitted(true);
      try {
        confetti({
          particleCount: 80,
          spread: 80,
          origin: { y: 0.65 },
          colors: ["#f5b464", "#f59e0b", "#38bdf8", "#ffffff"],
        });
      } catch {
        // Confetti optional
      }
    } catch (err) {
      setErrorMsg(err.message || "Network error. You can also email us directly at umersahi5p@gmail.com.");
    } finally {
      setLoading(false);
    }
  };

  const handleReset = () => {
    setSubmitted(false);
    setFormData({
      name: "",
      email: "",
      phone: "",
      inquiry_type: "Buy Luxury Villa",
      city: "Islamabad",
      budget: "5 - 10 Crore",
      message: "",
    });
  };

  return (
    <section id="contact" className="py-24 px-4 sm:px-6 lg:px-8 relative overflow-hidden bg-gradient-to-b from-[#090d16] via-[#070b14] to-[#060912]">
      {/* Ambient Atmospheric Glows */}
      <div className="absolute top-1/4 left-1/4 w-[600px] h-[600px] bg-[radial-gradient(circle,_rgba(245,180,100,0.035)_0%,_transparent_65%)] blur-3xl pointer-events-none" />
      <div className="absolute bottom-10 right-10 w-[550px] h-[550px] bg-[radial-gradient(circle,_rgba(56,189,248,0.03)_0%,_transparent_65%)] blur-3xl pointer-events-none" />

      <div className="relative z-10 max-w-7xl mx-auto">
        {/* Section Header */}
        <motion.div
          initial={{ opacity: 0, y: 24 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: "-50px" }}
          transition={{ duration: 0.8, ease: [0.16, 1, 0.3, 1] }}
          className="text-center max-w-3xl mx-auto mb-16"
        >
          <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-amber-400/10 border border-amber-400/25 text-amber-300 text-xs font-mono tracking-widest uppercase mb-4 shadow-sm">
            <Sparkles className="w-3.5 h-3.5 text-amber-400" />
            <span>Executive Client Concierge</span>
          </div>

          <h2 className="font-display-serif text-3xl sm:text-4xl lg:text-5xl font-normal text-white tracking-tight mb-4">
            Connect with Our Senior Partners
          </h2>

          <p className="text-slate-400 text-xs sm:text-sm font-light leading-relaxed">
            Direct, confidential access to Pakistan’s premier luxury real estate advisory. All inquiries are delivered
            directly to our Principal Office at <strong className="text-amber-300 font-medium">umersahi5p@gmail.com</strong>.
          </p>
        </motion.div>

        {/* 2-Column Luxury Layout */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 lg:gap-10 items-start">
          {/* LEFT COLUMN: Executive Advisory & Direct Hotline Channels (5 cols) */}
          <motion.div
            initial={{ opacity: 0, x: -24 }}
            whileInView={{ opacity: 1, x: 0 }}
            viewport={{ once: true, margin: "-50px" }}
            transition={{ duration: 0.8, delay: 0.1, ease: [0.16, 1, 0.3, 1] }}
            className="lg:col-span-5 space-y-6 text-left"
          >
            {/* Primary Direct Inbox Card */}
            <div className="p-6 sm:p-7 rounded-3xl bg-[#0c1322] border border-amber-400/35 shadow-[0_20px_50px_rgba(0,0,0,0.8),0_0_30px_rgba(245,180,100,0.12)] relative overflow-hidden">
              <div className="absolute top-0 right-0 w-36 h-36 bg-gradient-to-bl from-amber-400/15 to-transparent rounded-bl-full pointer-events-none" />

              <div className="flex items-center gap-2.5 mb-3">
                <span className="px-2.5 py-1 rounded-full text-[10px] font-mono uppercase tracking-wider bg-amber-400/20 text-amber-300 border border-amber-400/40">
                  Priority Executive Inbox
                </span>
                <span className="inline-block w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
              </div>

              <h3 className="text-xl font-heading font-semibold text-white mb-2">Direct Principal Recipient</h3>
              <p className="text-xs text-slate-400 font-light mb-4 leading-relaxed">
                Your message is routed directly to our Managing Principal for expedited review.
              </p>

              <div className="flex items-center gap-3 p-3.5 rounded-2xl bg-[#080e1b] border border-white/10 mb-4">
                <div className="w-10 h-10 rounded-xl bg-amber-400/15 border border-amber-400/30 flex items-center justify-center text-amber-300 flex-shrink-0">
                  <Mail className="w-5 h-5" />
                </div>
                <div className="min-w-0">
                  <span className="block text-[10px] font-mono text-slate-400 uppercase tracking-wider">Direct Email</span>
                  <a
                    href="mailto:umersahi5p@gmail.com"
                    className="text-amber-300 font-semibold text-sm hover:underline truncate block"
                  >
                    umersahi5p@gmail.com
                  </a>
                </div>
              </div>

              {/* Instant WhatsApp Channel */}
              <a
                href="https://wa.me/923001234567?text=Assalam-o-Alaikum,%20I%20am%20interested%20in%20a%20luxury%20estate%20via%20RealEstate%20Hub"
                target="_blank"
                rel="noopener noreferrer"
                className="w-full py-3 px-4 rounded-2xl bg-emerald-500/15 hover:bg-emerald-500/25 border border-emerald-500/40 text-emerald-300 text-xs font-semibold flex items-center justify-center gap-2 transition-all cursor-pointer shadow-sm hover:shadow-[0_0_20px_rgba(16,185,129,0.25)]"
              >
                <MessageSquare className="w-4 h-4 text-emerald-400" />
                <span>Chat Instantly via WhatsApp Hotline</span>
                <ExternalLink className="w-3.5 h-3.5 text-emerald-400 ml-1" />
              </a>
            </div>

            {/* Headquarters & Contact Details */}
            <div className="p-6 rounded-3xl bg-[#0c1322] border border-white/12 shadow-[0_16px_40px_rgba(0,0,0,0.6)] space-y-4">
              <h4 className="text-xs font-semibold uppercase tracking-widest text-slate-300 font-mono flex items-center gap-2">
                <Building2 className="w-4 h-4 text-amber-300" />
                <span>Executive Headquarters</span>
              </h4>

              <div className="space-y-3 text-xs text-slate-300">
                <div className="flex items-start gap-3">
                  <MapPin className="w-4 h-4 text-amber-300 flex-shrink-0 mt-0.5" />
                  <span className="font-light">
                    Executive Tower, Jinnah Avenue, Sector F-7/G-7 Blue Area, Islamabad, Pakistan
                  </span>
                </div>

                <div className="flex items-center gap-3">
                  <Phone className="w-4 h-4 text-amber-300 flex-shrink-0" />
                  <a href="tel:+92518849000" className="hover:text-amber-300 transition-colors font-mono">
                    +92 (051) 884-9000 • +92 (300) 123-4567
                  </a>
                </div>

                <div className="flex items-center gap-3">
                  <Clock className="w-4 h-4 text-slate-400 flex-shrink-0" />
                  <span className="text-slate-400 font-light">Monday – Saturday: 9:00 AM – 8:00 PM PST</span>
                </div>
              </div>
            </div>

            {/* Service Commitments Grid */}
            <div className="grid grid-cols-2 gap-3">
              <div className="p-3.5 rounded-2xl bg-white/[0.03] border border-white/10">
                <div className="flex items-center gap-2 text-white text-xs font-medium mb-1">
                  <Clock className="w-3.5 h-3.5 text-amber-300" />
                  <span>&lt; 2-Hour Response</span>
                </div>
                <p className="text-[11px] text-slate-400 font-light">Expedited reply guaranteed for all client inquiries.</p>
              </div>

              <div className="p-3.5 rounded-2xl bg-white/[0.03] border border-white/10">
                <div className="flex items-center gap-2 text-white text-xs font-medium mb-1">
                  <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
                  <span>100% Confidential</span>
                </div>
                <p className="text-[11px] text-slate-400 font-light">Protected under Non-Disclosure Agreements.</p>
              </div>
            </div>
          </motion.div>

          {/* RIGHT COLUMN: Modern Luxury Interactive Contact Form (7 cols) */}
          <motion.div
            initial={{ opacity: 0, x: 24 }}
            whileInView={{ opacity: 1, x: 0 }}
            viewport={{ once: true, margin: "-50px" }}
            transition={{ duration: 0.8, delay: 0.15, ease: [0.16, 1, 0.3, 1] }}
            className="lg:col-span-7"
          >
            <div className="rounded-3xl p-6 sm:p-8 bg-[#0c1322] border border-white/15 shadow-[0_25px_60px_-10px_rgba(0,0,0,0.85)] relative overflow-hidden text-left">
              <div className="absolute top-0 inset-x-0 h-[1px] bg-gradient-to-r from-transparent via-amber-400/50 to-transparent pointer-events-none" />

              {submitted ? (
                <div className="py-12 px-4 text-center space-y-5">
                  <div className="w-16 h-16 mx-auto rounded-full bg-emerald-500/15 border border-emerald-500/40 text-emerald-400 flex items-center justify-center shadow-[0_0_30px_rgba(16,185,129,0.3)]">
                    <CheckCircle2 className="w-8 h-8" />
                  </div>
                  <h3 className="font-display-serif text-2xl sm:text-3xl text-white">Inquiry Dispatched Successfully!</h3>
                  <p className="text-xs sm:text-sm text-slate-300 max-w-md mx-auto font-light leading-relaxed">
                    Thank you, <strong className="text-white font-semibold">{formData.name}</strong>. Your inquiry has been
                    sent directly to our Executive Principal at <strong className="text-amber-300 font-mono">umersahi5p@gmail.com</strong>.
                  </p>

                  <div className="p-4 rounded-2xl bg-[#080e1a] border border-white/10 max-w-md mx-auto text-left space-y-1.5 text-xs">
                    <div className="text-slate-400"><strong>Inquiry:</strong> {formData.inquiry_type} ({formData.city})</div>
                    <div className="text-slate-400"><strong>Budget:</strong> {formData.budget}</div>
                    <div className="text-slate-400"><strong>Contact:</strong> {formData.email} • {formData.phone}</div>
                  </div>

                  <div className="pt-4 flex flex-col sm:flex-row items-center justify-center gap-3">
                    <button
                      onClick={handleReset}
                      className="px-6 py-2.5 rounded-full text-xs font-medium text-white bg-white/10 hover:bg-white/20 border border-white/20 transition-all cursor-pointer"
                    >
                      Send Another Inquiry
                    </button>
                    <button
                      onClick={onOpenAi}
                      className="px-6 py-2.5 rounded-full text-xs font-semibold text-slate-950 bg-gradient-to-r from-amber-400 to-amber-500 hover:from-amber-300 hover:to-amber-400 transition-all flex items-center gap-2 cursor-pointer shadow-md"
                    >
                      <Headphones className="w-3.5 h-3.5" />
                      <span>Talk with Urdu AI Agent</span>
                    </button>
                  </div>
                </div>
              ) : (
                <form onSubmit={handleSubmit} className="space-y-5">
                  <div className="border-b border-white/10 pb-4 mb-5">
                    <h3 className="text-lg font-heading font-semibold text-white">Luxury Estate Inquiry Form</h3>
                    <p className="text-xs text-slate-400 font-light mt-1">
                      Direct transmission to <span className="text-amber-300 font-mono">umersahi5p@gmail.com</span>
                    </p>
                  </div>

                  {errorMsg && (
                    <div className="p-3 rounded-2xl bg-red-500/15 border border-red-500/30 text-red-300 text-xs flex items-center gap-2.5">
                      <AlertCircle className="w-4 h-4 flex-shrink-0 text-red-400" />
                      <span>{errorMsg}</span>
                    </div>
                  )}

                  {/* 1. Inquiry Type Selector Pills */}
                  <div>
                    <label className="block text-[11px] font-semibold text-slate-400 uppercase tracking-wider mb-2 font-mono">
                      Inquiry Category
                    </label>
                    <div className="flex flex-wrap gap-2">
                      {inquiryOptions.map((type) => {
                        const isSelected = formData.inquiry_type === type;
                        return (
                          <button
                            key={type}
                            type="button"
                            onClick={() => setFormData({ ...formData, inquiry_type: type })}
                            className={`px-3 py-1.5 rounded-full text-xs font-medium transition-all cursor-pointer ${
                              isSelected
                                ? "bg-amber-400 text-slate-950 font-bold shadow-[0_0_15px_rgba(245,180,100,0.35)]"
                                : "bg-[#090f1e] text-slate-300 hover:text-white border border-white/10 hover:border-white/20"
                            }`}
                          >
                            {type}
                          </button>
                        );
                      })}
                    </div>
                  </div>

                  {/* 2. Name & Email Row */}
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                    <div>
                      <label className="block text-[11px] font-semibold text-slate-400 uppercase tracking-wider mb-1.5 font-mono">
                        Full Name *
                      </label>
                      <div className="relative">
                        <User className="w-4 h-4 text-slate-400 absolute left-3.5 top-1/2 -translate-y-1/2" />
                        <input
                          type="text"
                          required
                          value={formData.name}
                          onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                          placeholder="e.g. Mian Tariq"
                          className="w-full pl-10 pr-4 py-2.5 rounded-2xl bg-[#090f1e] border border-white/15 text-white placeholder:text-slate-500 text-xs focus:outline-none focus:border-amber-400/60 focus:bg-[#0d1629] transition-all"
                        />
                      </div>
                    </div>

                    <div>
                      <label className="block text-[11px] font-semibold text-slate-400 uppercase tracking-wider mb-1.5 font-mono">
                        Email Address *
                      </label>
                      <div className="relative">
                        <Mail className="w-4 h-4 text-slate-400 absolute left-3.5 top-1/2 -translate-y-1/2" />
                        <input
                          type="email"
                          required
                          value={formData.email}
                          onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                          placeholder="tariq@example.com"
                          className="w-full pl-10 pr-4 py-2.5 rounded-2xl bg-[#090f1e] border border-white/15 text-white placeholder:text-slate-500 text-xs focus:outline-none focus:border-amber-400/60 focus:bg-[#0d1629] transition-all"
                        />
                      </div>
                    </div>
                  </div>

                  {/* 3. Phone Number & City Preference Row */}
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                    <div>
                      <label className="block text-[11px] font-semibold text-slate-400 uppercase tracking-wider mb-1.5 font-mono">
                        Phone / WhatsApp
                      </label>
                      <div className="relative">
                        <Phone className="w-4 h-4 text-slate-400 absolute left-3.5 top-1/2 -translate-y-1/2" />
                        <input
                          type="tel"
                          value={formData.phone}
                          onChange={(e) => setFormData({ ...formData, phone: e.target.value })}
                          placeholder="+92 300 1234567"
                          className="w-full pl-10 pr-4 py-2.5 rounded-2xl bg-[#090f1e] border border-white/15 text-white placeholder:text-slate-500 text-xs focus:outline-none focus:border-amber-400/60 focus:bg-[#0d1629] transition-all"
                        />
                      </div>
                    </div>

                    <div>
                      <label className="block text-[11px] font-semibold text-slate-400 uppercase tracking-wider mb-1.5 font-mono">
                        Preferred City
                      </label>
                      <select
                        value={formData.city}
                        onChange={(e) => setFormData({ ...formData, city: e.target.value })}
                        className="w-full px-3.5 py-2.5 rounded-2xl bg-[#090f1e] border border-white/15 text-white text-xs focus:outline-none focus:border-amber-400/60 focus:bg-[#0d1629] transition-all cursor-pointer"
                      >
                        {cityOptions.map((c) => (
                          <option key={c} value={c} className="bg-[#0c1322] text-white">
                            {c}
                          </option>
                        ))}
                      </select>
                    </div>
                  </div>

                  {/* 4. Budget Range Selector */}
                  <div>
                    <label className="block text-[11px] font-semibold text-slate-400 uppercase tracking-wider mb-1.5 font-mono">
                      Estimated Budget Range
                    </label>
                    <select
                      value={formData.budget}
                      onChange={(e) => setFormData({ ...formData, budget: e.target.value })}
                      className="w-full px-3.5 py-2.5 rounded-2xl bg-[#090f1e] border border-white/15 text-white text-xs focus:outline-none focus:border-amber-400/60 focus:bg-[#0d1629] transition-all cursor-pointer"
                    >
                      {budgetOptions.map((b) => (
                        <option key={b} value={b} className="bg-[#0c1322] text-white">
                          {b}
                        </option>
                      ))}
                    </select>
                  </div>

                  {/* 5. Detailed Requirements / Message */}
                  <div>
                    <label className="block text-[11px] font-semibold text-slate-400 uppercase tracking-wider mb-1.5 font-mono">
                      Detailed Message / Property Specifications *
                    </label>
                    <textarea
                      required
                      rows={4}
                      value={formData.message}
                      onChange={(e) => setFormData({ ...formData, message: e.target.value })}
                      placeholder="Tell us about the property specifications, preferred locality (e.g. DHA Phase 6, Sector F-7, Bahria Town), Marla/Kanal size, or schedule a consultation..."
                      className="w-full p-3.5 rounded-2xl bg-[#090f1e] border border-white/15 text-white placeholder:text-slate-500 text-xs focus:outline-none focus:border-amber-400/60 focus:bg-[#0d1629] transition-all resize-none"
                    />
                  </div>

                  {/* Submit Button */}
                  <div className="pt-2">
                    <button
                      type="submit"
                      disabled={loading}
                      className="w-full py-3.5 px-6 rounded-full bg-gradient-to-r from-amber-400 via-amber-500 to-amber-600 hover:from-amber-300 hover:to-amber-500 text-slate-950 font-bold text-xs sm:text-sm flex items-center justify-center gap-2 cursor-pointer shadow-[0_0_25px_rgba(245,180,100,0.35)] hover:shadow-[0_0_35px_rgba(245,180,100,0.5)] transition-all disabled:opacity-60 disabled:cursor-not-allowed"
                    >
                      {loading ? (
                        <>
                          <div className="w-4 h-4 border-2 border-slate-950 border-t-transparent rounded-full animate-spin" />
                          <span>Dispatching to umersahi5p@gmail.com...</span>
                        </>
                      ) : (
                        <>
                          <Send className="w-4 h-4 text-slate-950" />
                          <span>Submit VIP Inquiry Directly to Principal</span>
                          <ArrowRight className="w-4 h-4 text-slate-950" />
                        </>
                      )}
                    </button>
                  </div>

                  <div className="flex items-center justify-between text-[11px] text-slate-400 pt-1">
                    <span className="flex items-center gap-1.5">
                      <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
                      <span>Transmitted directly to umersahi5p@gmail.com</span>
                    </span>
                    <span>Guaranteed Response within 2 hours</span>
                  </div>
                </form>
              )}
            </div>
          </motion.div>
        </div>
      </div>
    </section>
  );
}
