import React, { useState, useEffect, useCallback } from "react";
import { motion } from "framer-motion";
import Navbar from "./components/Navbar";
import HeroSection from "./components/HeroSection";
import PropertyExplorer from "./components/PropertyExplorer";
import AdminPortal from "./components/AdminPortal";
import AuthModal from "./components/AuthModal";
import BookingModal from "./components/BookingModal";
import AiAssistantWidget from "./components/AiAssistantWidget";
import AiFloatingAgent from "./components/AiFloatingAgent";
import ContactSection from "./components/ContactSection";
import Footer from "./components/Footer";
import {
  Sparkles,
  Calendar,
  ShieldCheck,
  PhoneCall,
  Building2,
  Cpu,
  Radio,
  Clock,
  ArrowUpRight,
  CheckCircle2,
} from "lucide-react";

export default function App() {
  const [currentUser, setCurrentUser] = useState(() => {
    try {
      const saved = localStorage.getItem("realestate_user");
      return saved ? JSON.parse(saved) : null;
    } catch {
      return null;
    }
  });

  const [activeTab, setActiveTab] = useState("properties"); // "properties" | "crm" | "admin"
  const [backendConnected, setBackendConnected] = useState(false);

  const [totalPropertiesCount, setTotalPropertiesCount] = useState(750);

  // Modals state
  const [authModalOpen, setAuthModalOpen] = useState(false);
  const [bookingProperty, setBookingProperty] = useState(null);
  const [aiWidgetOpen, setAiWidgetOpen] = useState(false);
  const [aiInitialQuery, setAiInitialQuery] = useState("");

  // Check backend health
  const checkHealth = useCallback(async () => {
    try {
      const res = await fetch("/api/health");
      const data = await res.json();
      setBackendConnected(Boolean(data.ok));
    } catch {
      setBackendConnected(false);
    }
  }, []);

  useEffect(() => {
    checkHealth();
    const interval = setInterval(checkHealth, 10000);
    return () => clearInterval(interval);
  }, [checkHealth]);

  const handleAuthSuccess = (user, token) => {
    setCurrentUser(user);
    try {
      localStorage.setItem("realestate_user", JSON.stringify(user));
      localStorage.setItem("realestate_token", token);
    } catch { }
    if (user.role === "admin") {
      setActiveTab("admin");
    }
  };

  const handleLogout = () => {
    setCurrentUser(null);
    try {
      localStorage.removeItem("realestate_user");
      localStorage.removeItem("realestate_token");
    } catch { }
    if (activeTab === "admin") {
      setActiveTab("properties");
    }
  };

  const handleAskAi = (prop) => {
    setAiInitialQuery(
      `Mujhe is property ke bare mein bataye: ${prop.area_marla} Marla ${prop.property_type} in ${prop.locality}, budget ${prop.price} PKR.`
    );
    setAiWidgetOpen(true);
  };

  const handleOpenAdminDemo = () => {
    if (currentUser?.role === "admin") {
      setActiveTab("admin");
    } else {
      setAuthModalOpen(true);
    }
  };

  const handleTotalLoaded = useCallback((total) => {
    setTotalPropertiesCount(total);
  }, []);

  const handleSelectFeaturedProperty = (featuredProp) => {
    setBookingProperty({
      property_id: `FEAT-${featuredProp.id}`,
      property_title: `${featuredProp.title} (${featuredProp.locality}, ${featuredProp.city})`,
      area_marla: featuredProp.area,
      locality: featuredProp.locality,
      city: featuredProp.city,
      price: featuredProp.price,
      agent: "Ahmed Raza",
    });
  };

  return (
    <div className="min-h-screen flex flex-col bg-[#090d16] text-[#FAF8F5] selection:bg-amber-400/30 selection:text-amber-200">
      {/* Liquid Glass Navigation */}
      <Navbar
        currentUser={currentUser}
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        onOpenAuth={() => setAuthModalOpen(true)}
        onLogout={handleLogout}
        onOpenAiWidget={() => setAiWidgetOpen(true)}
        backendConnected={backendConnected}
      />

      {/* Main Content Sections */}
      <main className="flex-1">
        {activeTab === "properties" && (
          <>
            {/* Hero Section (Matching Reference Photo with Real DB Metrics & Framer Motion) */}
            <HeroSection
              totalProperties={totalPropertiesCount}
              onExplore={() => {
                const el = document.getElementById("properties-section");
                if (el) el.scrollIntoView({ behavior: "smooth" });
              }}
              onOpenVoice={() => setAiWidgetOpen(true)}
              onOpenAdminDemo={handleOpenAdminDemo}
              onSelectFeaturedProperty={handleSelectFeaturedProperty}
            />

            {/* Curated Properties Portfolio (Seamless Hero Continuation without background image) */}
            <PropertyExplorer
              isAdmin={currentUser?.role === "admin"}
              onBookVisit={(prop) => setBookingProperty(prop)}
              onAskAi={handleAskAi}
              onEditProperty={() => setActiveTab("admin")}
              onDeleteProperty={() => setActiveTab("admin")}
              onTotalLoaded={handleTotalLoaded}
            />

            {/* Features & Architectural Ecosystem Showcase with Framer Motion */}
            <section id="features-section" className="py-24 px-4 sm:px-8 max-w-7xl mx-auto text-left relative">
              <div className="text-center max-w-2xl mx-auto mb-16">
                <motion.div
                  initial={{ opacity: 0, y: 15 }}
                  whileInView={{ opacity: 1, y: 0 }}
                  viewport={{ once: true }}
                  transition={{ duration: 0.6 }}
                  className="inline-flex items-center gap-2 px-3.5 py-1 rounded-full bg-white/[0.06] backdrop-blur-md border border-white/12 text-amber-200 text-xs font-medium mb-3 shadow-sm"
                >
                  <Cpu className="w-3.5 h-3.5 text-amber-300" />
                  <span>Autonomous Intelligent Architecture</span>
                </motion.div>

                <motion.h2
                  initial={{ opacity: 0, y: 20 }}
                  whileInView={{ opacity: 1, y: 0 }}
                  viewport={{ once: true }}
                  transition={{ duration: 0.75, delay: 0.1, ease: [0.16, 1, 0.3, 1] }}
                  className="font-display-serif text-3xl sm:text-4xl lg:text-5xl font-normal text-white tracking-tight"
                >
                  Engineered For Distinction
                </motion.h2>

                <motion.p
                  initial={{ opacity: 0, y: 15 }}
                  whileInView={{ opacity: 1, y: 0 }}
                  viewport={{ once: true }}
                  transition={{ duration: 0.75, delay: 0.2 }}
                  className="text-slate-400 text-xs sm:text-sm mt-3 font-light leading-relaxed"
                >
                  A unified platform marrying state-of-the-art AI voice agents, deterministic LangGraph workflows, and verified real estate intelligence.
                </motion.p>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
                {/* Feature 1 */}
                <motion.div
                  initial={{ opacity: 0, y: 30 }}
                  whileInView={{ opacity: 1, y: 0 }}
                  viewport={{ once: true }}
                  transition={{ duration: 0.6, delay: 0.1 }}
                  whileHover={{ y: -6, transition: { duration: 0.25 } }}
                  className="p-6 rounded-2xl bg-[#0e1422]/80 backdrop-blur-xl border border-white/10 hover:border-white/25 transition-all shadow-lg hover:shadow-[0_20px_40px_rgba(0,0,0,0.7),0_0_20px_rgba(245,180,100,0.06)]"
                >
                  <div className="w-12 h-12 rounded-2xl bg-white/[0.06] border border-white/12 text-sky-400 flex items-center justify-center mb-5 shadow-inner">
                    <Radio className="w-6 h-6" />
                  </div>
                  <h3 className="font-heading text-lg font-semibold text-white mb-2">
                    Deepgram Nova-3 Urdu STT
                  </h3>
                  <p className="text-xs text-slate-400 leading-relaxed font-light">
                    Fluid natural Urdu voice recognition with sub-second latency, dialect comprehension, and live acoustic audio streaming.
                  </p>
                </motion.div>

                {/* Feature 2 */}
                <motion.div
                  initial={{ opacity: 0, y: 30 }}
                  whileInView={{ opacity: 1, y: 0 }}
                  viewport={{ once: true }}
                  transition={{ duration: 0.6, delay: 0.2 }}
                  whileHover={{ y: -6, transition: { duration: 0.25 } }}
                  className="p-6 rounded-2xl bg-[#0e1422]/80 backdrop-blur-xl border border-white/10 hover:border-white/25 transition-all shadow-lg hover:shadow-[0_20px_40px_rgba(0,0,0,0.7),0_0_20px_rgba(245,180,100,0.06)]"
                >
                  <div className="w-12 h-12 rounded-2xl bg-white/[0.06] border border-white/12 text-amber-300 flex items-center justify-center mb-5 shadow-inner">
                    <Cpu className="w-6 h-6" />
                  </div>
                  <h3 className="font-heading text-lg font-semibold text-white mb-2">
                    LangGraph StateGraph Agent
                  </h3>
                  <p className="text-xs text-slate-400 leading-relaxed font-light">
                    Deterministic multi-node state orchestration with intent detection, property retrieval, and intelligent lead classification.
                  </p>
                </motion.div>

                {/* Feature 3 */}
                <motion.div
                  initial={{ opacity: 0, y: 30 }}
                  whileInView={{ opacity: 1, y: 0 }}
                  viewport={{ once: true }}
                  transition={{ duration: 0.6, delay: 0.3 }}
                  whileHover={{ y: -6, transition: { duration: 0.25 } }}
                  className="p-6 rounded-2xl bg-[#0e1422]/80 backdrop-blur-xl border border-white/10 hover:border-white/25 transition-all shadow-lg hover:shadow-[0_20px_40px_rgba(0,0,0,0.7),0_0_20px_rgba(245,180,100,0.06)]"
                >
                  <div className="w-12 h-12 rounded-2xl bg-white/[0.06] border border-white/12 text-amber-400 flex items-center justify-center mb-5 shadow-inner">
                    <Clock className="w-6 h-6" />
                  </div>
                  <h3 className="font-heading text-lg font-semibold text-white mb-2">
                    Automated CRM Scheduling
                  </h3>
                  <p className="text-xs text-slate-400 leading-relaxed font-light">
                    Direct on-demand site visit reservations, email dispatch to property agents, and instant calendar synchronizations.
                  </p>
                </motion.div>

                {/* Feature 4 */}
                <motion.div
                  initial={{ opacity: 0, y: 30 }}
                  whileInView={{ opacity: 1, y: 0 }}
                  viewport={{ once: true }}
                  transition={{ duration: 0.6, delay: 0.4 }}
                  whileHover={{ y: -6, transition: { duration: 0.25 } }}
                  className="p-6 rounded-2xl bg-[#0e1422]/80 backdrop-blur-xl border border-white/10 hover:border-white/25 transition-all shadow-lg hover:shadow-[0_20px_40px_rgba(0,0,0,0.7),0_0_20px_rgba(245,180,100,0.06)]"
                >
                  <div className="w-12 h-12 rounded-2xl bg-white/[0.06] border border-white/12 text-emerald-400 flex items-center justify-center mb-5 shadow-inner">
                    <ShieldCheck className="w-6 h-6" />
                  </div>
                  <h3 className="font-heading text-lg font-semibold text-white mb-2">
                    100% Verified DB Listings
                  </h3>
                  <p className="text-xs text-slate-400 leading-relaxed font-light">
                    750+ authenticated residences, villas, and commercial properties across Lahore, Islamabad, and Rawalpindi.
                  </p>
                </motion.div>
              </div>
            </section>
          </>
        )}

        {/* CRM Appointments Tab */}
        {activeTab === "crm" && (
          <div className="pt-28 pb-16">
            <div className="max-w-7xl mx-auto px-4 sm:px-8 mb-6 text-left">
              <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-white/[0.06] backdrop-blur-md border border-white/12 text-amber-200 text-xs font-semibold mb-2">
                <Calendar className="w-3.5 h-3.5 text-amber-300" />
                <span>Automated CRM Appointment Schedule</span>
              </div>
              <h1 className="font-display-serif text-3xl sm:text-4xl font-normal text-white">
                Client Visit Schedules
              </h1>
              <p className="text-slate-400 text-xs mt-1">
                Real-time appointment calendar integrated with LangGraph agent and email notifications.
              </p>
            </div>
            <AdminPortal onRefreshStats={checkHealth} />
          </div>
        )}

        {/* Admin Portal Tab */}
        {activeTab === "admin" && (
          <div className="pt-28 pb-16">
            {currentUser?.role === "admin" ? (
              <AdminPortal onRefreshStats={checkHealth} />
            ) : (
              <div className="py-20 text-center px-4 max-w-md mx-auto">
                <div className="w-16 h-16 rounded-2xl bg-white/[0.06] border border-white/12 text-amber-300 flex items-center justify-center mx-auto mb-4 shadow-xl">
                  <ShieldCheck className="w-8 h-8" />
                </div>
                <h2 className="font-display-serif text-3xl font-normal text-white mb-2">
                  Admin Portal Access
                </h2>
                <p className="text-xs text-slate-400 mb-6 font-light">
                  Please log in as an administrator to add, edit, or delete property records and manage CRM schedules.
                </p>
                <button
                  onClick={() => setAuthModalOpen(true)}
                  className="w-full py-3 rounded-full text-xs font-semibold text-slate-950 bg-gradient-to-r from-amber-400 to-amber-500 hover:from-amber-300 hover:to-amber-400 cursor-pointer shadow-lg transition-all"
                >
                  Sign In as Administrator
                </button>
              </div>
            )}
          </div>
        )}
      </main>

      {/* Floating Animated Lottie AI Agent (Hover popup + Voice & Chat widget trigger) */}
      {!aiWidgetOpen && (
        <AiFloatingAgent onClick={() => setAiWidgetOpen(true)} />
      )}

      {/* Modern Luxury Contact Us Section with Direct Dispatch to umersahi5p@gmail.com */}
      {activeTab === "properties" && (
        <ContactSection
          onOpenAi={() => setAiWidgetOpen(true)}
          onOpenBooking={() =>
            setBookingProperty({
              property_id: "VIP-CONSULTATION",
              property_title: "Private VIP Estate Consultation",
              locality: "Islamabad & Lahore Estates",
              agent: "Senior Partner Advisory",
            })
          }
        />
      )}

      {/* Luxury Architectural Dusk Footer with Rich About Us & Full Services */}
      <Footer
        onOpenAi={() => setAiWidgetOpen(true)}
        onOpenBooking={() =>
          setBookingProperty({
            property_id: "VIP-CONSULTATION",
            property_title: "Private VIP Estate Consultation",
            locality: "Islamabad & Lahore Estates",
            agent: "Senior Partner Advisory",
          })
        }
      />

      {/* Modals */}
      <AuthModal
        isOpen={authModalOpen}
        onClose={() => setAuthModalOpen(false)}
        onAuthSuccess={handleAuthSuccess}
      />

      <BookingModal
        property={bookingProperty}
        currentUser={currentUser}
        isOpen={Boolean(bookingProperty)}
        onClose={() => setBookingProperty(null)}
        onSuccess={() => checkHealth()}
      />

      <AiAssistantWidget
        isOpen={aiWidgetOpen}
        onClose={() => {
          setAiWidgetOpen(false);
          setAiInitialQuery("");
        }}
        initialQuery={aiInitialQuery}
        onBookVisit={(prop) => {
          setBookingProperty(prop);
          setAiWidgetOpen(false);
        }}
      />
    </div>
  );
}
