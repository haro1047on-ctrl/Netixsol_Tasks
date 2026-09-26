import React, { useState, useEffect, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  X,
  Calendar as CalendarIcon,
  Clock,
  User,
  Phone,
  Mail,
  CheckCircle2,
  Building2,
  Sparkles,
  ArrowRight,
  ExternalLink,
  ChevronLeft,
  ChevronRight,
  ChevronDown,
} from "lucide-react";
import confetti from "canvas-confetti";

export default function BookingModal({ property, currentUser, isOpen, onClose, onSuccess }) {
  const [clientName, setClientName] = useState("");
  const [clientPhone, setClientPhone] = useState("");
  const [clientEmail, setClientEmail] = useState("");
  
  // Date Picker State
  const getToday = () => {
    const d = new Date();
    d.setHours(0, 0, 0, 0);
    return d;
  };

  const [selectedDate, setSelectedDate] = useState(() => {
    const d = getToday();
    d.setDate(d.getDate() + 1);
    return d;
  });

  const [viewDate, setViewDate] = useState(() => {
    const d = getToday();
    d.setDate(d.getDate() + 1);
    return new Date(d.getFullYear(), d.getMonth(), 1);
  });

  const [showCalendar, setShowCalendar] = useState(false);
  const calendarRef = useRef(null);

  const [timeStr, setTimeStr] = useState("3:00 PM");
  const [notes, setNotes] = useState("");
  const [loading, setLoading] = useState(false);
  const [bookingResult, setBookingResult] = useState(null);
  const [errorMsg, setErrorMsg] = useState("");

  // Close calendar popover on outside click
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (calendarRef.current && !calendarRef.current.contains(event.target)) {
        setShowCalendar(false);
      }
    };
    if (showCalendar) {
      document.addEventListener("mousedown", handleClickOutside);
    }
    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
    };
  }, [showCalendar]);

  // Populate from logged-in user or reset on open
  useEffect(() => {
    if (isOpen) {
      setClientName(currentUser?.name || "");
      setClientPhone(currentUser?.phone || "");
      setClientEmail(currentUser?.email || "");
      const tomorrow = getToday();
      tomorrow.setDate(tomorrow.getDate() + 1);
      setSelectedDate(tomorrow);
      setViewDate(new Date(tomorrow.getFullYear(), tomorrow.getMonth(), 1));
      setTimeStr("3:00 PM");
      setNotes("");
      setShowCalendar(false);
      setBookingResult(null);
      setErrorMsg("");
    }
  }, [isOpen, currentUser]);

  if (!isOpen || !property) return null;

  const propertyTitle =
    property.property_title ||
    `${property.area_marla || property.area || ""} Marla in ${property.locality || "Prime Locality"}, ${property.city || "Pakistan"}`;

  // Calendar Helpers
  const monthNames = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December"
  ];
  const dayNames = ["Su", "Mo", "Tu", "We", "Th", "Fr", "Sa"];

  const isSameDay = (d1, d2) => {
    if (!d1 || !d2) return false;
    return (
      d1.getFullYear() === d2.getFullYear() &&
      d1.getMonth() === d2.getMonth() &&
      d1.getDate() === d2.getDate()
    );
  };

  const isPastDay = (d) => {
    const today = getToday();
    return d.getTime() < today.getTime();
  };

  const getDaysArray = () => {
    const year = viewDate.getFullYear();
    const month = viewDate.getMonth();
    const firstDayIndex = new Date(year, month, 1).getDay();
    const numDays = new Date(year, month + 1, 0).getDate();
    const prevMonthDays = new Date(year, month, 0).getDate();

    const days = [];

    // Leading days from previous month
    for (let i = firstDayIndex - 1; i >= 0; i--) {
      days.push({
        date: new Date(year, month - 1, prevMonthDays - i),
        isCurrentMonth: false,
      });
    }

    // Days in current month
    for (let i = 1; i <= numDays; i++) {
      days.push({
        date: new Date(year, month, i),
        isCurrentMonth: true,
      });
    }

    // Trailing days to fill 7-col grid
    const remainder = 7 - (days.length % 7);
    if (remainder < 7) {
      for (let i = 1; i <= remainder; i++) {
        days.push({
          date: new Date(year, month + 1, i),
          isCurrentMonth: false,
        });
      }
    }

    return days;
  };

  const handlePrevMonth = (e) => {
    e.preventDefault();
    e.stopPropagation();
    const today = getToday();
    if (viewDate.getFullYear() === today.getFullYear() && viewDate.getMonth() <= today.getMonth()) {
      return;
    }
    setViewDate(new Date(viewDate.getFullYear(), viewDate.getMonth() - 1, 1));
  };

  const handleNextMonth = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setViewDate(new Date(viewDate.getFullYear(), viewDate.getMonth() + 1, 1));
  };

  const handleSelectDate = (d, e) => {
    if (e) {
      e.preventDefault();
      e.stopPropagation();
    }
    if (isPastDay(d)) return;
    setSelectedDate(d);
    setShowCalendar(false);
  };

  const selectPreset = (type, e) => {
    if (e) {
      e.preventDefault();
      e.stopPropagation();
    }
    const today = getToday();
    let target = new Date(today);
    if (type === "today") {
      target = today;
    } else if (type === "tomorrow") {
      target.setDate(today.getDate() + 1);
    } else if (type === "saturday") {
      const day = today.getDay();
      const diff = (6 - day + 7) % 7 || 7;
      target.setDate(today.getDate() + diff);
    } else if (type === "sunday") {
      const day = today.getDay();
      const diff = (7 - day + 7) % 7 || 7;
      target.setDate(today.getDate() + diff);
    }
    setSelectedDate(target);
    setViewDate(new Date(target.getFullYear(), target.getMonth(), 1));
    setShowCalendar(false);
  };

  const formatDisplayDate = (d) => {
    if (!d) return "Select Date";
    const today = getToday();
    const diffDays = Math.round((d.getTime() - today.getTime()) / (1000 * 60 * 60 * 24));
    const options = { weekday: "short", month: "short", day: "numeric" };
    const str = d.toLocaleDateString("en-US", options);
    if (diffDays === 0) return `Today (${str})`;
    if (diffDays === 1) return `Tomorrow (${str})`;
    return str;
  };

  const formatApiDate = (d) => {
    if (!d) return "Tomorrow";
    const options = { weekday: "short", month: "short", day: "numeric", year: "numeric" };
    return d.toLocaleDateString("en-US", options);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setErrorMsg("");
    setLoading(true);

    const formattedDate = formatApiDate(selectedDate);

    try {
      const res = await fetch("/api/crm/appointments", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          client_name: clientName || "Valued Client",
          client_phone: clientPhone || "Not Provided",
          client_email: clientEmail || "",
          property_id: property.property_id || property.id || "PROP-General",
          property_title: propertyTitle,
          agent_name: property.agent || "Ahmed Raza",
          date_str: formattedDate,
          time_str: timeStr,
          notes: notes || "Site visit booked from luxury catalog",
        }),
      });

      const data = await res.json();
      if (!res.ok || !data.ok) {
        throw new Error(data.error || "Booking request failed. Please try again.");
      }

      setBookingResult(data);

      // Signature golden champagne celebration burst
      confetti({
        particleCount: 75,
        spread: 70,
        origin: { y: 0.6 },
        colors: ["#fbbf24", "#f59e0b", "#fef3c7", "#ffffff", "#d97706"],
      });

      if (onSuccess) onSuccess();
    } catch (err) {
      setErrorMsg(err.message || "Failed to schedule appointment. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  const handleClose = () => {
    setBookingResult(null);
    setShowCalendar(false);
    onClose();
  };

  return (
    <AnimatePresence>
      <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
        {/* Backdrop with Twilight Obsidian Blur */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          onClick={handleClose}
          className="fixed inset-0 bg-[#060910]/80 backdrop-blur-xl transition-opacity"
        />

        {/* Ambient Villa Warm Golden Glow Leaks */}
        <div className="absolute w-[450px] h-[450px] rounded-full bg-[radial-gradient(circle,_rgba(245,180,100,0.14)_0%,_transparent_70%)] blur-3xl pointer-events-none -translate-y-10" />
        <div className="absolute w-[380px] h-[380px] rounded-full bg-[radial-gradient(circle,_rgba(56,189,248,0.05)_0%,_transparent_70%)] blur-3xl pointer-events-none translate-y-20 translate-x-20" />

        {/* Main Modal Card (Frosted Liquid Glass with Specular Gold Accents) */}
        <motion.div
          initial={{ opacity: 0, scale: 0.94, y: 15 }}
          animate={{ opacity: 1, scale: 1, y: 0 }}
          exit={{ opacity: 0, scale: 0.94, y: 15 }}
          transition={{ duration: 0.35, ease: [0.16, 1, 0.3, 1] }}
          onClick={(e) => e.stopPropagation()}
          className="relative z-10 w-full max-w-[460px] p-6 sm:p-8 rounded-3xl bg-[#0e1422]/95 backdrop-blur-3xl border border-white/15 shadow-[0_30px_90px_rgba(0,0,0,0.9),inset_0_1px_1px_rgba(255,255,255,0.15)] overflow-visible text-left"
        >
          {/* Specular Gold Top Rim Highlight */}
          <div className="absolute top-0 inset-x-8 h-[1.5px] bg-gradient-to-r from-transparent via-amber-400/50 to-transparent pointer-events-none" />

          {/* Close Button */}
          <button
            onClick={handleClose}
            className="absolute top-5 right-5 w-8 h-8 rounded-full bg-white/[0.06] hover:bg-white/[0.14] border border-white/15 hover:border-white/30 flex items-center justify-center text-slate-300 hover:text-white transition-all cursor-pointer shadow-sm z-20"
          >
            <X className="w-4 h-4" />
          </button>

          {bookingResult ? (
            /* =========================================================
               SUCCESS CONFIRMATION SCREEN
               ========================================================= */
            <motion.div
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              className="py-4 text-center space-y-4"
            >
              <div className="relative w-16 h-16 mx-auto flex items-center justify-center">
                <div className="absolute inset-0 rounded-full bg-amber-400/20 blur-xl animate-pulse" />
                <div className="relative w-16 h-16 rounded-2xl bg-white/[0.08] backdrop-blur-xl border border-amber-400/40 flex items-center justify-center shadow-[0_0_25px_rgba(245,180,100,0.2)]">
                  <CheckCircle2 className="w-8 h-8 text-amber-300" />
                </div>
              </div>

              <div>
                <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-emerald-500/10 border border-emerald-500/30 text-emerald-300 text-[10px] font-semibold tracking-wider uppercase mb-2">
                  <Sparkles className="w-3 h-3 text-emerald-300" />
                  <span>Reservation Confirmed</span>
                </span>
                <h3 className="text-2xl sm:text-3xl font-display-serif text-white tracking-tight">
                  Visit Scheduled
                </h3>
              </div>

              {/* Unique Memorable Appointment Badge */}
              {bookingResult.appointment_id && (
                <div className="p-3.5 rounded-2xl bg-amber-400/[0.08] border border-amber-400/25 max-w-xs mx-auto shadow-inner">
                  <div className="text-[10px] uppercase font-mono tracking-widest text-amber-300/80">
                    Your Appointment ID
                  </div>
                  <div className="text-xl sm:text-2xl font-bold font-mono text-amber-300 tracking-wider my-0.5">
                    {bookingResult.appointment_id}
                  </div>
                  <div className="text-[10px] text-slate-400 font-light">
                    Reference this ID to reschedule or cancel anytime
                  </div>
                </div>
              )}

              <p className="text-xs text-slate-300 max-w-sm mx-auto font-light leading-relaxed">
                Your private tour of{" "}
                <span className="text-white font-medium">{propertyTitle}</span> has been
                reserved for{" "}
                <span className="text-amber-300 font-medium">{formatDisplayDate(selectedDate)}</span> at{" "}
                <span className="text-amber-300 font-medium">{timeStr}</span>.
              </p>

              {/* Email Notification Alert */}
              {clientEmail && (
                <div className="p-3 rounded-xl bg-white/[0.04] border border-white/10 text-left flex items-start gap-2.5 max-w-sm mx-auto text-xs text-slate-300">
                  <Mail className="w-4 h-4 text-amber-300 mt-0.5 flex-shrink-0" />
                  <div>
                    <span className="text-white font-medium">Confirmation Dispatched</span>
                    <p className="text-[11px] text-slate-400 mt-0.5">
                      CRM notification and schedule details have been sent to{" "}
                      <span className="text-amber-300 font-mono">{clientEmail}</span>.
                    </p>
                  </div>
                </div>
              )}

              <div className="pt-2 flex flex-col sm:flex-row gap-2 max-w-sm mx-auto">
                {bookingResult.calendar_link && (
                  <a
                    href={bookingResult.calendar_link}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex-1 py-2.5 px-4 rounded-full bg-white/[0.06] hover:bg-white/[0.12] border border-white/15 text-slate-200 hover:text-white text-xs font-medium flex items-center justify-center gap-1.5 transition-all shadow-sm cursor-pointer"
                  >
                    <span>Google Calendar</span>
                    <ExternalLink className="w-3.5 h-3.5 text-slate-400" />
                  </a>
                )}
                <button
                  onClick={handleClose}
                  className="flex-1 py-2.5 px-4 rounded-full bg-gradient-to-r from-amber-400 via-amber-300 to-amber-500 hover:from-amber-300 hover:to-amber-400 text-slate-950 font-bold text-xs flex items-center justify-center gap-1.5 transition-all cursor-pointer shadow-[0_2px_12px_rgba(245,180,100,0.3)]"
                >
                  <span>Done</span>
                </button>
              </div>
            </motion.div>
          ) : (
            /* =========================================================
               BOOKING FORM
               ========================================================= */
            <div>
              {/* Header */}
              <div className="mb-5 text-left">
                <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-amber-400/10 border border-amber-400/25 text-amber-300 text-[10px] font-semibold tracking-wider uppercase mb-2 shadow-[0_0_15px_rgba(245,180,100,0.1)]">
                  <Sparkles className="w-3 h-3 text-amber-300" />
                  <span>Private Consultation Booking</span>
                </div>
                <h2 className="font-display-serif text-2xl sm:text-3xl font-normal text-white tracking-tight">
                  Schedule Private Tour
                </h2>
                <p className="text-xs text-slate-400 mt-1 font-light leading-relaxed flex items-center gap-1.5 truncate">
                  <Building2 className="w-3.5 h-3.5 text-amber-400/70 flex-shrink-0" />
                  <span className="truncate">{propertyTitle}</span>
                </p>
              </div>

              {/* Error banner */}
              {errorMsg && (
                <div className="mb-4 p-3 rounded-xl bg-red-500/10 border border-red-500/25 text-red-200 text-xs flex items-center gap-2 shadow-sm">
                  <span className="w-1.5 h-1.5 rounded-full bg-red-400 flex-shrink-0" />
                  <span>{errorMsg}</span>
                </div>
              )}

              <form onSubmit={handleSubmit} className="space-y-3.5 text-left">
                {/* Full Name */}
                <div>
                  <label className="block text-[10px] font-semibold tracking-widest text-slate-300 uppercase mb-1">
                    Your Full Name <span className="text-amber-400">*</span>
                  </label>
                  <div className="relative">
                    <User className="w-4 h-4 text-amber-300/70 absolute left-3.5 top-1/2 -translate-y-1/2" />
                    <input
                      type="text"
                      required
                      value={clientName}
                      onChange={(e) => setClientName(e.target.value)}
                      placeholder="Enter your full name"
                      className="w-full pl-10 pr-3.5 py-2.5 rounded-xl bg-white/[0.04] border border-white/12 text-white placeholder-slate-500 text-xs focus:outline-none focus:border-amber-400/60 focus:bg-white/[0.07] focus:ring-1 focus:ring-amber-400/30 transition-all"
                    />
                  </div>
                </div>

                {/* Phone & Email side by side or stacked */}
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  {/* Phone */}
                  <div>
                    <label className="block text-[10px] font-semibold tracking-widest text-slate-300 uppercase mb-1">
                      Phone Number <span className="text-amber-400">*</span>
                    </label>
                    <div className="relative">
                      <Phone className="w-4 h-4 text-amber-300/70 absolute left-3.5 top-1/2 -translate-y-1/2" />
                      <input
                        type="tel"
                        required
                        value={clientPhone}
                        onChange={(e) => setClientPhone(e.target.value)}
                        placeholder="+92 300 1234567"
                        className="w-full pl-10 pr-3.5 py-2.5 rounded-xl bg-white/[0.04] border border-white/12 text-white placeholder-slate-500 text-xs focus:outline-none focus:border-amber-400/60 focus:bg-white/[0.07] focus:ring-1 focus:ring-amber-400/30 transition-all"
                      />
                    </div>
                  </div>

                  {/* Email Address */}
                  <div>
                    <label className="block text-[10px] font-semibold tracking-widest text-slate-300 uppercase mb-1">
                      Email Address <span className="text-amber-400">*</span>
                    </label>
                    <div className="relative">
                      <Mail className="w-4 h-4 text-amber-300/70 absolute left-3.5 top-1/2 -translate-y-1/2" />
                      <input
                        type="email"
                        required
                        value={clientEmail}
                        onChange={(e) => setClientEmail(e.target.value)}
                        placeholder="client@example.com"
                        className="w-full pl-10 pr-3.5 py-2.5 rounded-xl bg-white/[0.04] border border-white/12 text-white placeholder-slate-500 text-xs focus:outline-none focus:border-amber-400/60 focus:bg-white/[0.07] focus:ring-1 focus:ring-amber-400/30 transition-all"
                      />
                    </div>
                  </div>
                </div>

                {/* Preferred Date & Time Slot */}
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  {/* Interactive Calendar Date Picker */}
                  <div className="relative" ref={calendarRef}>
                    <label className="block text-[10px] font-semibold tracking-widest text-slate-300 uppercase mb-1">
                      Preferred Date <span className="text-amber-400">*</span>
                    </label>

                    {/* Trigger Input Button */}
                    <button
                      type="button"
                      onClick={() => setShowCalendar((prev) => !prev)}
                      className={`w-full pl-10 pr-7 py-2.5 rounded-xl bg-white/[0.04] border text-white text-xs transition-all flex items-center justify-between text-left cursor-pointer group ${
                        showCalendar
                          ? "border-amber-400/60 bg-white/[0.07] ring-1 ring-amber-400/30"
                          : "border-white/12 hover:border-amber-400/40"
                      }`}
                    >
                      <CalendarIcon className="w-4 h-4 text-amber-300/80 absolute left-3.5 top-1/2 -translate-y-1/2 pointer-events-none" />
                      <span className="truncate">{formatDisplayDate(selectedDate)}</span>
                      <ChevronDown
                        className={`w-3.5 h-3.5 text-slate-400 group-hover:text-amber-300 transition-transform ${
                          showCalendar ? "rotate-180 text-amber-300" : ""
                        }`}
                      />
                    </button>

                    {/* Floating Luxury Calendar Popover */}
                    <AnimatePresence>
                      {showCalendar && (
                        <motion.div
                          initial={{ opacity: 0, y: -6, scale: 0.96 }}
                          animate={{ opacity: 1, y: 0, scale: 1 }}
                          exit={{ opacity: 0, y: -6, scale: 0.96 }}
                          transition={{ duration: 0.18, ease: "easeOut" }}
                          className="absolute left-0 sm:left-auto sm:right-0 top-full mt-2 z-50 w-[290px] sm:w-[310px] p-3.5 rounded-2xl bg-[#0b101c]/98 backdrop-blur-3xl border border-white/20 shadow-[0_20px_50px_rgba(0,0,0,0.9),0_0_25px_rgba(245,180,100,0.12)] text-left"
                        >
                          {/* Quick selection chips */}
                          <div className="flex items-center gap-1.5 pb-2.5 mb-2.5 border-b border-white/10 overflow-x-auto no-scrollbar">
                            <button
                              type="button"
                              onClick={(e) => selectPreset("today", e)}
                              className="px-2 py-1 rounded-lg text-[10px] font-medium bg-white/[0.05] hover:bg-amber-400/20 hover:text-amber-300 text-slate-300 border border-white/10 transition-all cursor-pointer whitespace-nowrap"
                            >
                              Today
                            </button>
                            <button
                              type="button"
                              onClick={(e) => selectPreset("tomorrow", e)}
                              className="px-2 py-1 rounded-lg text-[10px] font-medium bg-white/[0.05] hover:bg-amber-400/20 hover:text-amber-300 text-slate-300 border border-white/10 transition-all cursor-pointer whitespace-nowrap"
                            >
                              Tomorrow
                            </button>
                            <button
                              type="button"
                              onClick={(e) => selectPreset("saturday", e)}
                              className="px-2 py-1 rounded-lg text-[10px] font-medium bg-white/[0.05] hover:bg-amber-400/20 hover:text-amber-300 text-slate-300 border border-white/10 transition-all cursor-pointer whitespace-nowrap"
                            >
                              This Sat
                            </button>
                            <button
                              type="button"
                              onClick={(e) => selectPreset("sunday", e)}
                              className="px-2 py-1 rounded-lg text-[10px] font-medium bg-white/[0.05] hover:bg-amber-400/20 hover:text-amber-300 text-slate-300 border border-white/10 transition-all cursor-pointer whitespace-nowrap"
                            >
                              This Sun
                            </button>
                          </div>

                          {/* Month Navigation */}
                          <div className="flex items-center justify-between mb-2 px-1">
                            <button
                              type="button"
                              onClick={handlePrevMonth}
                              disabled={
                                viewDate.getFullYear() === getToday().getFullYear() &&
                                viewDate.getMonth() <= getToday().getMonth()
                              }
                              className="w-6 h-6 rounded-lg bg-white/[0.06] hover:bg-white/[0.14] disabled:opacity-20 disabled:hover:bg-white/[0.06] border border-white/15 flex items-center justify-center text-slate-300 hover:text-white transition-all cursor-pointer disabled:cursor-not-allowed"
                            >
                              <ChevronLeft className="w-3.5 h-3.5" />
                            </button>
                            <div className="font-display-serif text-xs font-semibold text-white tracking-wide">
                              {monthNames[viewDate.getMonth()]} {viewDate.getFullYear()}
                            </div>
                            <button
                              type="button"
                              onClick={handleNextMonth}
                              className="w-6 h-6 rounded-lg bg-white/[0.06] hover:bg-white/[0.14] border border-white/15 flex items-center justify-center text-slate-300 hover:text-white transition-all cursor-pointer"
                            >
                              <ChevronRight className="w-3.5 h-3.5" />
                            </button>
                          </div>

                          {/* Day Names Header */}
                          <div className="grid grid-cols-7 gap-1 text-center mb-1">
                            {dayNames.map((day) => (
                              <div
                                key={day}
                                className="text-[10px] font-mono text-slate-500 font-medium py-1"
                              >
                                {day}
                              </div>
                            ))}
                          </div>

                          {/* Day Grid */}
                          <div className="grid grid-cols-7 gap-1 text-center">
                            {getDaysArray().map((item, idx) => {
                              const isPast = isPastDay(item.date);
                              const isSelected = isSameDay(item.date, selectedDate);
                              const isCurrentToday = isSameDay(item.date, getToday());

                              return (
                                <button
                                  key={idx}
                                  type="button"
                                  disabled={isPast}
                                  onClick={(e) => handleSelectDate(item.date, e)}
                                  className={`h-7 w-7 mx-auto rounded-lg text-xs font-medium flex items-center justify-center transition-all ${
                                    isSelected
                                      ? "bg-gradient-to-r from-amber-400 via-amber-300 to-amber-500 text-slate-950 font-bold shadow-[0_0_12px_rgba(245,180,100,0.5)] scale-105"
                                      : isPast
                                      ? "text-slate-600 opacity-25 cursor-not-allowed"
                                      : !item.isCurrentMonth
                                      ? "text-slate-500 hover:bg-white/[0.04] cursor-pointer"
                                      : isCurrentToday
                                      ? "border border-amber-400/50 text-amber-300 hover:bg-amber-400/15 cursor-pointer"
                                      : "text-slate-200 hover:bg-white/[0.08] hover:text-amber-200 cursor-pointer"
                                  }`}
                                >
                                  {item.date.getDate()}
                                </button>
                              );
                            })}
                          </div>
                        </motion.div>
                      )}
                    </AnimatePresence>
                  </div>

                  {/* Time Slot */}
                  <div>
                    <label className="block text-[10px] font-semibold tracking-widest text-slate-300 uppercase mb-1">
                      Time Slot
                    </label>
                    <div className="relative">
                      <Clock className="w-4 h-4 text-amber-300/70 absolute left-3.5 top-1/2 -translate-y-1/2" />
                      <select
                        value={timeStr}
                        onChange={(e) => setTimeStr(e.target.value)}
                        className="w-full pl-10 pr-2 py-2.5 rounded-xl bg-white/[0.04] border border-white/12 text-white text-xs focus:outline-none focus:border-amber-400/60 focus:bg-white/[0.07] focus:ring-1 focus:ring-amber-400/30 transition-all cursor-pointer"
                      >
                        <option value="11:00 AM" className="bg-[#0e1422] text-white">11:00 AM</option>
                        <option value="2:00 PM" className="bg-[#0e1422] text-white">2:00 PM</option>
                        <option value="3:00 PM" className="bg-[#0e1422] text-white">3:00 PM</option>
                        <option value="4:00 PM" className="bg-[#0e1422] text-white">4:00 PM</option>
                        <option value="5:00 PM" className="bg-[#0e1422] text-white">5:00 PM</option>
                        <option value="6:00 PM" className="bg-[#0e1422] text-white">6:00 PM</option>
                      </select>
                    </div>
                  </div>
                </div>

                {/* Special Notes */}
                <div>
                  <label className="block text-[10px] font-semibold tracking-widest text-slate-300 uppercase mb-1">
                    Special Notes (Optional)
                  </label>
                  <textarea
                    rows={2}
                    value={notes}
                    onChange={(e) => setNotes(e.target.value)}
                    placeholder="Any specific architectural details or family preferences..."
                    className="w-full px-3.5 py-2 rounded-xl bg-white/[0.04] border border-white/12 text-white placeholder-slate-500 text-xs focus:outline-none focus:border-amber-400/60 focus:bg-white/[0.07] focus:ring-1 focus:ring-amber-400/30 transition-all resize-none"
                  />
                </div>

                {/* Gold Shimmering Submission Button */}
                <motion.button
                  whileHover={{ scale: 1.015, y: -1 }}
                  whileTap={{ scale: 0.985 }}
                  type="submit"
                  disabled={loading}
                  className="relative w-full py-3 px-4 rounded-full bg-gradient-to-r from-amber-400 via-amber-300 to-amber-500 hover:from-amber-300 hover:to-amber-400 text-slate-950 font-bold text-xs sm:text-sm flex items-center justify-center gap-2 group/btn cursor-pointer shadow-[0_4px_20px_rgba(245,180,100,0.35)] hover:shadow-[0_6px_28px_rgba(245,180,100,0.6)] transition-all overflow-hidden mt-3"
                >
                  <div className="absolute inset-0 -translate-x-full group-hover/btn:translate-x-full transition-transform duration-700 bg-gradient-to-r from-transparent via-white/50 to-transparent pointer-events-none" />
                  {loading ? (
                    <span className="inline-block w-4 h-4 border-2 border-slate-950/30 border-t-slate-950 rounded-full animate-spin" />
                  ) : (
                    <>
                      <CalendarIcon className="w-4 h-4 text-slate-950/80" />
                      <span>Confirm Reservation</span>
                      <ArrowRight className="w-4 h-4 text-slate-950/80 group-hover/btn:translate-x-1 transition-transform" />
                    </>
                  )}
                </motion.button>
              </form>
            </div>
          )}
        </motion.div>
      </div>
    </AnimatePresence>
  );
}
