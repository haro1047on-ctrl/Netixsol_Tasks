import React, { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { DotLottieReact } from "@lottiefiles/dotlottie-react";
import { Sparkles, PhoneCall, MessageSquare, Bot, ArrowRight } from "lucide-react";

export default function AiFloatingAgent({ onClick }) {
  const [isHovered, setIsHovered] = useState(false);

  return (
    <div
      className="fixed bottom-5 right-5 sm:bottom-6 sm:right-6 z-40 flex flex-col-reverse sm:flex-row items-end sm:items-center gap-3"
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
    >
      {/* Pop-up Card appearing on Hover */}
      <AnimatePresence>
        {isHovered && (
          <motion.div
            initial={{ opacity: 0, y: 10, sm: { y: 0, x: 20 }, scale: 0.92 }}
            animate={{ opacity: 1, y: 0, x: 0, scale: 1 }}
            exit={{ opacity: 0, y: 10, scale: 0.92 }}
            transition={{ type: "spring", stiffness: 420, damping: 30 }}
            onClick={onClick}
            className="cursor-pointer select-none relative bg-[#090e1a]/95 backdrop-blur-2xl border border-amber-400/40 rounded-2xl p-4 shadow-[0_20px_50px_rgba(0,0,0,0.9),0_0_35px_rgba(245,180,100,0.2)] text-left max-w-[calc(100vw-40px)] sm:min-w-[270px] group/popup"
          >
            {/* Header row */}
            <div className="flex items-center justify-between gap-2 mb-1.5">
              <div className="flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-emerald-400 shadow-[0_0_10px_rgba(52,211,153,0.9)] animate-pulse" />
                <span className="text-[10px] tracking-widest uppercase font-semibold text-amber-300">
                  Online 24/7
                </span>
              </div>
              <div className="flex items-center gap-1 text-[10px] text-slate-400 bg-white/5 px-2 py-0.5 rounded-full border border-white/10">
                <Sparkles className="w-3 h-3 text-amber-400" />
                <span>Multilingual</span>
              </div>
            </div>

            {/* Main Title required by user */}
            <h4 className="text-sm font-semibold text-white tracking-tight flex items-center justify-between group-hover/popup:text-amber-200 transition-colors">
              AI Voice & Chat Agent
              <ArrowRight className="w-3.5 h-3.5 text-amber-400 transform group-hover/popup:translate-x-1 transition-transform" />
            </h4>

            {/* Micro description */}
            <p className="text-[11px] text-slate-400 mt-1 leading-snug font-light">
              Speak or chat in Urdu/English for luxury property tours, instant valuations & bookings.
            </p>

            {/* Feature badges */}
            <div className="flex items-center gap-2 mt-3 pt-2.5 border-t border-white/10 text-[10px]">
              <span className="flex items-center gap-1 text-emerald-300/90 bg-emerald-500/10 px-2 py-0.5 rounded-md border border-emerald-500/20">
                <PhoneCall className="w-2.5 h-2.5" /> Voice Call
              </span>
              <span className="flex items-center gap-1 text-amber-300/90 bg-amber-500/10 px-2 py-0.5 rounded-md border border-amber-500/20">
                <MessageSquare className="w-2.5 h-2.5" /> AI Chat
              </span>
            </div>

            {/* Pointer arrow to the avatar */}
            <div className="hidden sm:block absolute top-1/2 -right-2 -translate-y-1/2 w-0 h-0 border-t-[7px] border-t-transparent border-b-[7px] border-b-transparent border-l-[8px] border-l-[#090e1a]/95" />
          </motion.div>
        )}
      </AnimatePresence>

      {/* Floating Animated Lottie Agent Avatar */}
      <motion.button
        initial={{ opacity: 0, scale: 0.8 }}
        animate={{
          opacity: 1,
          scale: 1,
          y: [0, -5, 0],
        }}
        transition={{
          y: { duration: 3.5, repeat: Infinity, ease: "easeInOut" },
          opacity: { duration: 0.4 },
          scale: { duration: 0.4 },
        }}
        whileHover={{ scale: 1.08 }}
        whileTap={{ scale: 0.94 }}
        onClick={onClick}
        aria-label="Open AI Voice & Chat Agent"
        className="relative w-24 h-24 sm:w-[108px] sm:h-[108px] rounded-full bg-gradient-to-b from-[#111827] to-[#080d18] border-[2.5px] border-amber-400/60 hover:border-amber-400 p-2 flex items-center justify-center cursor-pointer shadow-[0_20px_50px_rgba(0,0,0,0.85),0_0_35px_rgba(245,180,100,0.3)] hover:shadow-[0_25px_65px_rgba(0,0,0,0.95),0_0_50px_rgba(245,180,100,0.55)] transition-all group focus:outline-none"
      >
        {/* Ambient Ring Glow */}
        <div className="absolute inset-0 rounded-full bg-gradient-to-tr from-amber-500/25 via-transparent to-amber-300/25 blur-md pointer-events-none group-hover:opacity-100 opacity-70 transition-opacity" />

        {/* Lottie Animation */}
        <div className="w-full h-full rounded-full overflow-hidden flex items-center justify-center pointer-events-none relative z-10">
          <DotLottieReact
            src="/agent-ai.lottie"
            loop
            autoplay
            className="w-full h-full scale-110"
          />
        </div>

        {/* Live Active Status Indicator Dot */}
        <span className="absolute top-1.5 right-1.5 z-20 w-4.5 h-4.5 sm:w-5 sm:h-5 bg-emerald-400 rounded-full ring-2 sm:ring-[3px] ring-[#080d18] shadow-[0_0_15px_rgba(52,211,153,0.95)] animate-pulse" />
      </motion.button>
    </div>
  );
}
